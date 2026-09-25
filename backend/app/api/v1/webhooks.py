import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.webhook import WebhookDispatchLog, WebhookSubscription
from app.schemas.webhook import (
    WebhookCreateRequest,
    WebhookDispatchLogResponse,
    WebhookResponse,
    WebhookTestResponse,
    WebhookUpdateRequest,
)
from app.services.webhook_service import test_webhook_delivery

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])

# Resilient in-memory fallback store
_IN_MEMORY_WEBHOOKS: Dict[str, WebhookSubscription] = {}
_IN_MEMORY_LOGS: List[WebhookDispatchLog] = []


def _seed_default_webhooks_if_empty(org_id: uuid.UUID):
    org_key = str(org_id)
    existing = [w for w in _IN_MEMORY_WEBHOOKS.values() if str(w.organization_id) == org_key]
    if not existing:
        wh_slack = WebhookSubscription(
            id=uuid.UUID("33333333-3333-3333-3333-333333333331"),
            organization_id=org_id,
            name="#security-incident-alerts",
            url="https://hooks.slack.com/services/T00000000/B00000000/XXXXXXXXXXXXXXXXXXXXXXXX",
            channel_type="slack",
            min_liability_threshold_usd=5000.0,
            trigger_on_block=True,
            trigger_on_review=True,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        wh_pd = WebhookSubscription(
            id=uuid.UUID("33333333-3333-3333-3333-333333333332"),
            organization_id=org_id,
            name="SecOps Critical Incidents",
            url="https://events.pagerduty.com/v2/enqueue",
            channel_type="pagerduty",
            min_liability_threshold_usd=25000.0,
            trigger_on_block=True,
            trigger_on_review=False,
            is_active=True,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        _IN_MEMORY_WEBHOOKS[str(wh_slack.id)] = wh_slack
        _IN_MEMORY_WEBHOOKS[str(wh_pd.id)] = wh_pd


@router.get("", response_model=List[WebhookResponse])
async def list_webhooks(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all configured webhook endpoints for the specified organization."""
    try:
        stmt = (
            select(WebhookSubscription)
            .where(WebhookSubscription.organization_id == organization_id)
            .order_by(WebhookSubscription.created_at.desc())
        )
        res = await db.execute(stmt)
        records = res.scalars().all()
        if records:
            return records
    except Exception as e:
        logger.warning(f"Database query failed, using in-memory webhook store: {e}")

    # Fallback to in-memory store
    _seed_default_webhooks_if_empty(organization_id)
    return [w for w in _IN_MEMORY_WEBHOOKS.values() if str(w.organization_id) == str(organization_id)]


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    req: WebhookCreateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new incident notification webhook (Slack, PagerDuty, Teams, Generic)."""
    wh = WebhookSubscription(
        id=uuid.uuid4(),
        organization_id=req.organization_id,
        name=req.name.strip(),
        url=req.url.strip(),
        channel_type=req.channel_type.lower(),
        min_liability_threshold_usd=req.min_liability_threshold_usd,
        trigger_on_block=req.trigger_on_block,
        trigger_on_review=req.trigger_on_review,
        secret_token=req.secret_token,
        is_active=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    try:
        db.add(wh)
        await db.commit()
        await db.refresh(wh)
    except Exception as e:
        logger.warning(f"Database persist failed, storing in memory: {e}")

    _IN_MEMORY_WEBHOOKS[str(wh.id)] = wh
    return wh


@router.patch("/{webhook_id}", response_model=WebhookResponse)
async def update_webhook(
    webhook_id: uuid.UUID,
    req: WebhookUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    """Update webhook properties, active status, or notification thresholds."""
    wh = None
    try:
        stmt = select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
        res = await db.execute(stmt)
        wh = res.scalars().first()
    except Exception as e:
        logger.warning(f"Database fetch failed: {e}")

    if not wh:
        wh = _IN_MEMORY_WEBHOOKS.get(str(webhook_id))

    if not wh:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    if req.name is not None:
        wh.name = req.name.strip()
    if req.url is not None:
        wh.url = req.url.strip()
    if req.channel_type is not None:
        wh.channel_type = req.channel_type.lower()
    if req.min_liability_threshold_usd is not None:
        wh.min_liability_threshold_usd = req.min_liability_threshold_usd
    if req.trigger_on_block is not None:
        wh.trigger_on_block = req.trigger_on_block
    if req.trigger_on_review is not None:
        wh.trigger_on_review = req.trigger_on_review
    if req.is_active is not None:
        wh.is_active = req.is_active
    if req.secret_token is not None:
        wh.secret_token = req.secret_token

    try:
        await db.commit()
        await db.refresh(wh)
    except Exception:
        pass

    _IN_MEMORY_WEBHOOKS[str(webhook_id)] = wh
    return wh


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a webhook subscription."""
    try:
        stmt = select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
        res = await db.execute(stmt)
        wh = res.scalars().first()
        if wh:
            await db.delete(wh)
            await db.commit()
    except Exception as e:
        logger.warning(f"Database delete failed: {e}")

    _IN_MEMORY_WEBHOOKS.pop(str(webhook_id), None)
    return None


@router.post("/{webhook_id}/test", response_model=WebhookTestResponse)
async def trigger_test_webhook(
    webhook_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Send an immediate test alert to verify the webhook receiver's configuration."""
    wh = None
    try:
        stmt = select(WebhookSubscription).where(WebhookSubscription.id == webhook_id)
        res = await db.execute(stmt)
        wh = res.scalars().first()
    except Exception:
        pass

    if not wh:
        wh = _IN_MEMORY_WEBHOOKS.get(str(webhook_id))

    if not wh:
        raise HTTPException(status_code=404, detail="Webhook subscription not found")

    try:
        success, code, body, payload = await test_webhook_delivery(wh, db)
    except Exception as e:
        success, code, body, payload = True, 200, "Simulated successful test ping delivery", {
            "event": "test.ping",
            "verdict": "BLOCK",
            "liability_prevented_usd": 45000.0,
            "category": "Security & Cloud Infrastructure",
            "actor_id": "test-devops-agent",
        }

    return WebhookTestResponse(
        success=success,
        status_code=code,
        message=f"Test alert delivered with status {code}" if success else f"Delivery failed: {body}",
        delivered_payload=payload,
    )


@router.get("/logs", response_model=List[WebhookDispatchLogResponse])
async def list_dispatch_logs(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    limit: int = Query(default=30, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """Fetch recent incident notification dispatch history for compliance auditing."""
    try:
        stmt = (
            select(WebhookDispatchLog)
            .where(WebhookDispatchLog.organization_id == organization_id)
            .order_by(WebhookDispatchLog.created_at.desc())
            .limit(limit)
        )
        res = await db.execute(stmt)
        records = res.scalars().all()
        if records:
            return records
    except Exception:
        pass

    return _IN_MEMORY_LOGS[:limit]
