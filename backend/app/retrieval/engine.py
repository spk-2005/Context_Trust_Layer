import decimal
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.enums import ClaimStatus, ConflictStatus
from app.db.models.agent_context_item import AgentContextItem
from app.db.models.agent_request import AgentRequest
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.schemas.context import (
    ContextItemResponse,
    ContextQueryRequest,
    ContextQueryResponse,
    ContextSourceInfo,
    ContextValidityInfo,
)


class ContextRetrievalEngine:
    """Retrieves high-trust, verified, non-conflicting context for AI agents with full provenance."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.session = session
        self.llm = llm_provider or get_llm_provider()

    async def query_context(
        self,
        request_in: ContextQueryRequest,
    ) -> ContextQueryResponse:
        now = datetime.now(timezone.utc)

        # 1. Log the AgentRequest record
        agent_req = AgentRequest(
            organization_id=request_in.organization_id,
            agent_id=request_in.agent_id,
            query=request_in.query,
            trust_threshold=request_in.min_trust_score,
            max_results=request_in.max_results,
            status="processing",
        )
        self.session.add(agent_req)
        await self.session.flush()
        await self.session.refresh(agent_req)

        # 2. Fetch candidate claims for this organization
        stmt = (
            select(Claim)
            .where(
                Claim.organization_id == request_in.organization_id,
                Claim.status.in_([ClaimStatus.ACTIVE, ClaimStatus.VERIFIED, ClaimStatus.CONFLICTED]),
            )
            .options(
                selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
                selectinload(Claim.validity_records),
                selectinload(Claim.trust_scores),
                selectinload(Claim.document_version),
            )
        )
        res = await self.session.execute(stmt)
        all_claims = res.scalars().all()

        evaluated_items: list[tuple[Claim, decimal.Decimal, bool, str | None, ContextItemResponse | None]] = []
        query_terms = set(request_in.query.lower().split())

        for claim in all_claims:
            # Determine latest trust score
            latest_score = decimal.Decimal("0.5000")
            if claim.trust_scores:
                latest_score = max(ts.overall_score for ts in claim.trust_scores)

            # Check validity window
            is_valid = True
            validity_info = ContextValidityInfo(status="active")
            for val in claim.validity_records:
                if val.valid_until and val.valid_until < now:
                    is_valid = False
                    validity_info.status = "expired"
                    validity_info.valid_until = str(val.valid_until)
                if val.valid_from:
                    validity_info.valid_from = str(val.valid_from)

            # Check if claim content matches query keywords/intent
            claim_words = set(claim.claim_text.lower().split())
            overlap = query_terms.intersection(claim_words)
            relevance_match = len(overlap) > 0 or len(query_terms) == 0

            # Filter decisions
            included = True
            exclusion_reason = None

            if not is_valid:
                included = False
                exclusion_reason = "Claim validity window has expired."
            elif latest_score < request_in.min_trust_score:
                included = False
                exclusion_reason = f"Trust score ({latest_score}) below required threshold ({request_in.min_trust_score})."
            elif not relevance_match:
                included = False
                exclusion_reason = "Claim not relevant to query."
            elif claim.status == ClaimStatus.CONFLICTED:
                included = False
                exclusion_reason = "Claim has unresolved conflict pending human review."

            item_response = None
            if included:
                # Build provenance / evidence metadata
                doc_title = "Unknown Document"
                section_title = None
                page_num = 1
                evidence_quotes: list[str] = []

                for ev in claim.evidence:
                    if ev.document:
                        doc_title = ev.document.title
                    section_title = ev.section
                    page_num = ev.page_number or 1
                    evidence_quotes.append(ev.text_span)

                item_response = ContextItemResponse(
                    claim=claim.claim_text,
                    trust_score=latest_score,
                    validity=validity_info,
                    source=ContextSourceInfo(
                        document=doc_title,
                        section=section_title,
                        page=page_num,
                    ),
                    evidence=evidence_quotes,
                )

            evaluated_items.append((claim, latest_score, included, exclusion_reason, item_response))

        # 3. Sort included items by trust score (highest first) and limit to max_results
        included_items = [item for item in evaluated_items if item[2]]
        included_items.sort(key=lambda x: x[1], reverse=True)
        top_included = included_items[: request_in.max_results]

        final_context_list: list[ContextItemResponse] = []
        rank = 1

        for claim, score, included, reason, resp in top_included:
            if resp:
                final_context_list.append(resp)
            # Record in DB
            context_log = AgentContextItem(
                request_id=agent_req.id,
                claim_id=claim.id,
                rank=rank,
                trust_score=score,
                included=True,
                exclusion_reason=None,
            )
            self.session.add(context_log)
            rank += 1

        # Record excluded items in DB for auditing
        excluded_items = [item for item in evaluated_items if not item[2]]
        for claim, score, included, reason, _ in excluded_items:
            context_log = AgentContextItem(
                request_id=agent_req.id,
                claim_id=claim.id,
                rank=rank,
                trust_score=score,
                included=False,
                exclusion_reason=reason,
            )
            self.session.add(context_log)
            rank += 1

        # 4. Mark AgentRequest completed
        agent_req.status = "completed"
        agent_req.completed_at = datetime.now(timezone.utc)
        await self.session.flush()

        avg_confidence = (
            sum(item.trust_score for item in final_context_list) / len(final_context_list)
            if final_context_list
            else request_in.min_trust_score
        )

        return ContextQueryResponse(
            context=final_context_list,
            conflicts=[],
            confidence=decimal.Decimal(f"{avg_confidence:.4f}"),
        )
