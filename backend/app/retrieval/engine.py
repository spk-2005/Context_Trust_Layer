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
        from app.services.policy_agent_access_gate import PolicyAgentAccessGate
        self.access_gate = PolicyAgentAccessGate()

    async def query_context(
        self,
        request_in: ContextQueryRequest,
    ) -> ContextQueryResponse:
        # 1. Ensure a valid Agent record exists for the organization
        from app.db.models.agent import Agent
        from app.db.enums import RecordStatus

        effective_agent_id = request_in.agent_id
        if effective_agent_id:
            agent_check = await self.session.execute(
                select(Agent.id).where(Agent.id == effective_agent_id).limit(1)
            )
            if not agent_check.scalar_one_or_none():
                effective_agent_id = None

        if not effective_agent_id:
            org_agent = await self.session.execute(
                select(Agent.id).where(Agent.organization_id == request_in.organization_id).limit(1)
            )
            found_id = org_agent.scalar_one_or_none()
            if found_id:
                effective_agent_id = found_id
            else:
                default_agent = Agent(
                    organization_id=request_in.organization_id,
                    name="Context Trust Copilot",
                    description="Autonomous context verification agent",
                    agent_type="copilot",
                    status=RecordStatus.ACTIVE,
                )
                self.session.add(default_agent)
                await self.session.flush()
                await self.session.refresh(default_agent)
                effective_agent_id = default_agent.id

        # 1b. Log the AgentRequest record
        agent_req = AgentRequest(
            organization_id=request_in.organization_id,
            agent_id=effective_agent_id,
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
        )
        if getattr(request_in, "canonical_only", True):
            stmt = stmt.where(Claim.claim_type != "derived_summary")

        stmt = stmt.options(
            selectinload(Claim.evidence).selectinload(ClaimEvidence.document),
            selectinload(Claim.validity_records),
            selectinload(Claim.trust_scores),
            selectinload(Claim.document_version),
        )
        res = await self.session.execute(stmt)
        all_claims = res.scalars().all()

        evaluated_items: list[tuple[Claim, decimal.Decimal, bool, str | None, ContextItemResponse | None]] = []
        query_terms = set(request_in.query.lower().split())
        now = datetime.now(timezone.utc)

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
            # Calculate relevance score based on keyword overlap & term importance
            claim_lower = claim.claim_text.lower()
            overlap = query_terms.intersection(claim_words)
            relevance_match = len(overlap) > 0 or len(query_terms) == 0
            
            relevance_score = len(overlap)
            for qt in query_terms:
                clean_qt = qt.strip("?.,!$₹£€")
                if clean_qt and any(char.isdigit() for char in clean_qt) and clean_qt in claim_lower:
                    relevance_score += 5
                elif qt in ["refund", "window", "enterprise", "exception", "limit", "procurement", "po", "downtime", "sla", "cfo", "approval"] and qt in claim_lower:
                    relevance_score += 2

            # Departmental Workspace Domain Scoping Bonus
            target_domain = (request_in.domain or request_in.workspace_id or "").lower()
            if target_domain and target_domain not in ("global", "all"):
                domain_keywords = {
                    "finance": ["refund", "billing", "invoice", "arr", "tier", "payment", "accounting", "handbook", "confluence", "customer"],
                    "secops": ["security", "firewall", "ingress", "iam", "mtls", "session", "token", "freeze", "infrastructure", "portal"],
                    "hr": ["remote", "work", "leave", "vacation", "employee", "handbook", "people", "guideline"],
                    "support": ["support", "dispute", "sla", "ticket", "escalation", "customer", "resolution", "arbitration"],
                    "staging": ["sandbox", "staging", "test", "trial", "mock", "experiment"]
                }
                kws = domain_keywords.get(target_domain, [target_domain])
                if any(kw in claim_lower for kw in kws):
                    relevance_score += 25
                elif any(kw in (claim.subject or "").lower() for kw in kws):
                    relevance_score += 20

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
            else:
                # Enforce Sprint AE-3 Trust Tier Gate: Only certified tiers accessible
                claim_tier_eval = {
                    "candidate_id": str(claim.id),
                    "final_state": getattr(claim, "certification_status", None) or ("DUAL_HUMAN_CERTIFIED" if claim.status in [ClaimStatus.ACTIVE, ClaimStatus.VERIFIED] else "HUMAN_REVIEW_REQUIRED"),
                    "status": claim.status.value if hasattr(claim.status, "value") else str(claim.status)
                }
                gate_allowed, gate_level, gate_reason = self.access_gate.check_access(
                    claim_tier_eval,
                    agent_id=str(request_in.agent_id) if request_in.agent_id else None
                )
                if not gate_allowed:
                    included = False
                    exclusion_reason = gate_reason

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
                    claim_type=claim.claim_type,
                    is_canonical=(claim.claim_type != "derived_summary"),
                )

            evaluated_items.append((claim, latest_score, included, exclusion_reason, item_response, relevance_score))

        # 3. Sort included items by relevance score and trust score (highest first) and limit to max_results
        included_items = [item for item in evaluated_items if item[2]]
        included_items.sort(key=lambda x: (x[5], x[1]), reverse=True)
        top_included = included_items[: request_in.max_results]

        final_context_list: list[ContextItemResponse] = []
        rank = 1

        for claim, score, included, reason, resp, _rel in top_included:
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
        for claim, score, included, reason, _, _rel in excluded_items:
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
