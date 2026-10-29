import asyncio
from datetime import datetime, timedelta, timezone
import logging
from typing import Any, Dict, Optional
import uuid

import httpx
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.config import settings
from app.core.slack_security import (
    decrypt_slack_bot_token,
    generate_slack_link_token,
    resolve_slack_backend_url,
)
from app.db.database import engine
from app.db.enums import RecordStatus
from app.db.models.slack import (
    SlackDeliveryLedger,
    SlackInboundRequest,
    SlackInstallation,
    SlackJob,
    SlackUserIdentity,
)
from app.db.models.user import User
from app.services.copilot_query_service import CopilotQueryRequest, CopilotQueryService
from app.services.slack_block_kit import SlackBlockKitRenderer

logger = logging.getLogger(__name__)


class SlackJobWorker:
    """
    Durable transactional background worker for processing Slack requests.
    Uses PostgreSQL SKIP LOCKED row locks to coordinate safely across concurrent workers.
    Enforces response_url expiry, rate limiting, and exact delivery ledger tracking.
    """

    def __init__(self, session_factory=None):
        self._session_factory = session_factory or async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        self._running = False
        self._task: Optional[asyncio.Task] = None

    def start(self, poll_interval_seconds: float = 0.5):
        """Starts the background worker polling loop."""
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._run_loop(poll_interval_seconds))
            logger.info("SlackJobWorker loop started.")

    def stop(self):
        """Stops the worker loop gracefully."""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
        logger.info("SlackJobWorker loop stopped.")

    async def _run_loop(self, poll_interval_seconds: float):
        while self._running:
            try:
                job_processed = await self.process_next_job()
                if not job_processed:
                    await asyncio.sleep(poll_interval_seconds)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error in SlackJobWorker loop: {e}", exc_info=True)
                await asyncio.sleep(poll_interval_seconds)

    async def process_next_job(self) -> bool:
        """
        Polls and executes the next pending job atomically using SKIP LOCKED.
        Returns True if a job was found and processed, False otherwise.
        """
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            # Atomic lock lease on the next available job
            stmt = (
                select(SlackJob)
                .where(SlackJob.status == "QUEUED", SlackJob.next_run_at <= now)
                .order_by(SlackJob.created_at.asc())
                .limit(1)
                .with_for_update(skip_locked=True)
            )
            res = await session.execute(stmt)
            job = res.scalar_one_or_none()
            if not job:
                return False

            job.status = "RUNNING"
            job.locked_at = now
            job.locked_by = f"worker_{uuid.uuid4().hex[:6]}"
            job.attempts += 1
            job.updated_at = now
            await session.commit()

            # Execute the leased job
            await self._execute_job(job.id)
            return True

    async def _execute_job(self, job_id: uuid.UUID):
        now = datetime.now(timezone.utc)
        async with self._session_factory() as session:
            job_stmt = select(SlackJob).where(SlackJob.id == job_id)
            job = (await session.execute(job_stmt)).scalar_one_or_none()
            if not job:
                return

            req_stmt = select(SlackInboundRequest).where(SlackInboundRequest.id == job.inbound_request_id)
            req = (await session.execute(req_stmt)).scalar_one_or_none()
            if not req:
                job.status = "FAILED"
                job.error_message = "Associated inbound request not found."
                await session.commit()
                return

            try:
                # 1. Check installation status
                inst_stmt = select(SlackInstallation).where(
                    SlackInstallation.slack_team_id == req.slack_team_id,
                    SlackInstallation.is_active == True,
                )
                installation = (await session.execute(inst_stmt)).scalar_one_or_none()
                if not installation:
                    job.status = "FAILED"
                    job.error_message = "Slack workspace installation not found or disabled."
                    req.status = "FAILED"
                    await session.commit()
                    return

                # 2. Check response_url expiry (Slack limits to 30 mins; we check with safety margin)
                if now > req.response_url_expires_at:
                    job.status = "FAILED"
                    job.error_message = "Delivery expired: Slack response_url validity elapsed."
                    req.status = "EXPIRED"
                    ledger = SlackDeliveryLedger(
                        inbound_request_id=req.id,
                        delivery_target="response_url",
                        delivery_status="EXPIRED",
                        trace_id=req.trace_id,
                        delivered_at=now,
                    )
                    session.add(ledger)
                    await session.commit()
                    return

                # 3. Check User Identity Mapping
                ident_stmt = select(SlackUserIdentity).where(
                    SlackUserIdentity.slack_team_id == req.slack_team_id,
                    SlackUserIdentity.slack_user_id == req.slack_user_id,
                    SlackUserIdentity.is_active == True,
                )
                identity = (await session.execute(ident_stmt)).scalar_one_or_none()

                # If unlinked: dispatch secure linking card
                if not identity:
                    link_token = generate_slack_link_token(
                        slack_team_id=req.slack_team_id,
                        slack_user_id=req.slack_user_id,
                        organization_id=str(installation.organization_id),
                    )
                    base_url = resolve_slack_backend_url()
                    link_url = f"{base_url}/v1/slack/link-ui?token={link_token}"
                    payload = SlackBlockKitRenderer.render_account_linking_card(link_url)

                    await self._dispatch_to_response_url(session, req, payload)
                    job.status = "COMPLETED"
                    req.status = "UNLINKED"
                    await session.commit()
                    return

                # 4. Check active Trulin user status
                user_stmt = select(User).where(User.id == identity.trulin_user_id)
                user = (await session.execute(user_stmt)).scalar_one_or_none()
                if not user or user.status != RecordStatus.ACTIVE:
                    error_card = SlackBlockKitRenderer.render_error_card(
                        message="Your linked Trulin user account is inactive or revoked. Please contact your organization administrator.",
                        trace_id=req.trace_id,
                    )
                    await self._dispatch_to_response_url(session, req, error_card)
                    job.status = "COMPLETED"
                    req.status = "FAILED"
                    await session.commit()
                    return

                # Update identity last used timestamp
                identity.last_used_at = now

                # 5. Execute shared Copilot query
                copilot_service = CopilotQueryService(session)
                user_role_str = user.role.value if hasattr(user.role, "value") else str(user.role)
                query_req = CopilotQueryRequest(
                    organization_id=user.organization_id,
                    user_id=user.id,
                    user_name=user.name,
                    user_role=user_role_str,
                    question=req.raw_text,
                    trace_id=req.trace_id,
                )
                public_web_url = getattr(settings, "trulin_public_url", "https://app.trulin.ai")
                copilot_res = await copilot_service.query_policy(query_req, public_web_url=public_web_url)

                # 6. Render Block Kit & Dispatch to response_url
                block_kit_payload = SlackBlockKitRenderer.render_policy_answer(copilot_res, req.raw_text)
                delivery_ok = await self._dispatch_to_response_url(session, req, block_kit_payload)

                if delivery_ok:
                    job.status = "COMPLETED"
                    req.status = "COMPLETED"
                else:
                    # Retry handling is coordinated inside dispatch
                    pass

                await session.commit()

            except Exception as e:
                logger.error(f"Error executing Slack job {job_id}: {e}", exc_info=True)
                if job.attempts < job.max_attempts:
                    job.status = "QUEUED"
                    job.next_run_at = now + timedelta(seconds=2 ** job.attempts)
                else:
                    job.status = "FAILED"
                    job.error_message = str(e)
                    req.status = "FAILED"
                    # Attempt to post error notice
                    try:
                        err_card = SlackBlockKitRenderer.render_error_card(
                            message="An unexpected system error occurred while generating your policy answer.",
                            trace_id=req.trace_id,
                        )
                        await self._dispatch_to_response_url(session, req, err_card)
                    except Exception:
                        pass
                await session.commit()

    async def _dispatch_to_response_url(
        self,
        session: AsyncSession,
        req: SlackInboundRequest,
        payload: Dict[str, Any],
    ) -> bool:
        """Dispatches an ephemeral Block Kit payload to Slack's response_url."""
        now = datetime.now(timezone.utc)
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(req.response_url, json=payload)

                # Handle HTTP 429 Rate Limit
                if res.status_code == 429:
                    retry_after = int(res.headers.get("Retry-After", "2"))
                    logger.warning(f"Slack 429 Rate Limit hit. Retry-After: {retry_after}s for req {req.id}")
                    ledger = SlackDeliveryLedger(
                        inbound_request_id=req.id,
                        delivery_target="response_url",
                        delivery_status="RETRIED",
                        http_status=429,
                        trace_id=req.trace_id,
                        delivered_at=now,
                    )
                    session.add(ledger)
                    return False

                res.raise_for_status()
                ledger = SlackDeliveryLedger(
                    inbound_request_id=req.id,
                    delivery_target="response_url",
                    delivery_status="SUCCESS",
                    http_status=res.status_code,
                    trace_id=req.trace_id,
                    delivered_at=now,
                )
                session.add(ledger)
                return True

        except Exception as e:
            logger.warning(f"Failed to post to Slack response_url for req {req.id}: {e}")
            ledger = SlackDeliveryLedger(
                inbound_request_id=req.id,
                delivery_target="response_url",
                delivery_status="FAILED",
                http_status=getattr(getattr(e, "response", None), "status_code", 500),
                trace_id=req.trace_id,
                delivered_at=now,
            )
            session.add(ledger)
            return False


# Singleton worker instance
slack_worker = SlackJobWorker()
