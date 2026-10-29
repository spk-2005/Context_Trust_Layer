import decimal
import logging
import uuid
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user import User
from app.decision_engine.evaluator import DecisionEvaluator
from app.llm.factory import get_llm_provider
from app.retrieval.engine import ContextRetrievalEngine
from app.schemas.context import ContextQueryRequest
from app.services.answer_verifier import AnswerVerifier
from app.services.context_resolver import ConversationContextResolver

logger = logging.getLogger(__name__)


class CopilotCitation(BaseModel):
    source_index: int
    claim_id: uuid.UUID | str
    document_id: Optional[uuid.UUID | str] = None
    document_name: str
    section: Optional[str] = None
    page: Optional[int] = None
    folder_name: str = "Enterprise Policies"
    trust_score: float
    claim_text: str
    evidence_snippet: Optional[Any] = None
    evidence_url: str


class CopilotQueryRequest(BaseModel):
    organization_id: uuid.UUID
    user_id: uuid.UUID
    user_name: str = "User"
    user_role: str = "developer"
    question: str
    workspace_id: Optional[str] = "all"
    domain: Optional[str] = "global"
    allowed_evidence_lanes: List[str] = Field(default_factory=lambda: ["canonical", "verified"])
    assistance_mode: Literal["read_only_qa"] = "read_only_qa"
    trace_id: str


class CopilotQueryResponse(BaseModel):
    trace_id: str
    answer_status: Literal["ANSWERED", "PARTIAL", "CLARIFICATION_NEEDED", "REVIEW_RECOMMENDED", "DISPUTED"]
    decision_verdict: Literal["ALLOW", "REVIEW", "CLARIFY"]
    synthesized_answer: str
    citations: List[CopilotCitation] = Field(default_factory=list)
    conditions: List[str] = Field(default_factory=list)
    missing_facts: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    has_conflicts: bool = False
    trust_score: float = 0.50
    confidence: float = 0.50
    review_options: List[str] = Field(default_factory=lambda: ["report_issue", "request_human_review"])


class CopilotQueryService:
    """
    Decoupled, channel-agnostic policy copilot query service.
    Enforces identical evidence retrieval, authorization, conflict detection, 
    and answer verification across Web and Slack surfaces.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.llm = get_llm_provider()
        self.resolver = ConversationContextResolver(self.llm)

    async def query_policy(self, req: CopilotQueryRequest, public_web_url: str = "https://app.trulin.ai") -> CopilotQueryResponse:
        """
        Executes a grounded, authorized policy evidence query for read-only assistance.
        """
        trace_id = req.trace_id or f"trc-{uuid.uuid4().hex[:8]}"
        q_clean = req.question.strip()

        # 1. Retrieve authorized evidence claims via ContextRetrievalEngine
        retrieval_engine = ContextRetrievalEngine(self.session, self.llm)
        agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
        
        context_req = ContextQueryRequest(
            organization_id=req.organization_id,
            agent_id=agent_id,
            query=q_clean,
            min_trust_score=decimal.Decimal("0.50"),
            max_results=8,
            domain=req.domain or "global",
            workspace_id=req.workspace_id or "all",
        )
        context_res = await retrieval_engine.query_context(context_req)
        included_claims = context_res.context
        has_conflicts = len(context_res.conflicts) > 0

        avg_trust = (
            sum(float(item.trust_score) for item in included_claims) / len(included_claims)
            if included_claims else 0.50
        )

        # 2. Assemble deduplicated citations with full provenance
        citations: List[CopilotCitation] = []
        seen_claims = set()
        for idx, item in enumerate(included_claims):
            norm_text = item.claim.strip().lower()
            if norm_text in seen_claims:
                continue
            seen_claims.add(norm_text)
            
            doc_title = item.source.document if item.source else "Knowledge Base"
            section_title = item.source.section if item.source else None
            page_num = item.source.page if item.source else None
            folder_title = (
                getattr(item.source, "folder_name", None) 
                or (item.governed_package.folder_name if getattr(item, "governed_package", None) else None) 
                or "Enterprise Policies"
            )
            
            # Secure evidence URL: Requires login to view details
            evidence_url = f"{public_web_url.rstrip('/')}/evidence/{item.claim_id}"

            citations.append(
                CopilotCitation(
                    source_index=len(citations) + 1,
                    claim_id=item.claim_id,
                    document_id=item.document_id,
                    document_name=doc_title,
                    section=section_title,
                    page=page_num,
                    folder_name=folder_title,
                    trust_score=round(float(item.trust_score), 2),
                    claim_text=item.claim,
                    evidence_snippet=item.evidence,
                    evidence_url=evidence_url,
                )
            )

        warnings: List[str] = []
        if has_conflicts:
            for conf in context_res.conflicts:
                desc = conf.get("description") or "Contradictory evidence detected between active sources."
                warnings.append(f"Disputed evidence: {desc}")

        # 3. Handle Empty or Insufficient Evidence honestly (No Mock Hallucination)
        if not included_claims:
            return CopilotQueryResponse(
                trace_id=trace_id,
                answer_status="CLARIFICATION_NEEDED",
                decision_verdict="CLARIFY",
                synthesized_answer="No permitted policy documents or clauses were found covering this specific question in your authorized Trulin collections.",
                citations=[],
                missing_facts=["No relevant governing agreement, policy clause, or rule was found."],
                warnings=["Insufficient evidence in authorized workspace collections."],
                has_conflicts=False,
                trust_score=0.50,
                confidence=0.50,
            )

        # 4. Synthesize Grounded Answer via LLM
        citation_dicts = [
            {
                "source_index": c.source_index,
                "claim_id": c.claim_id,
                "document_id": c.document_id,
                "source_title": c.document_name,
                "section": c.section,
                "page": c.page,
                "claim_text": c.claim_text,
                "trust_score": c.trust_score,
                "evidence": c.evidence_snippet,
            }
            for c in citations
        ]

        synthesized_answer = await self.llm.generate_grounded_answer(
            query=q_clean,
            citations=citation_dicts,
            has_conflicts=has_conflicts,
            warnings=warnings,
            history=[],
        )

        ans_lower = synthesized_answer.lower()
        is_gap_or_escalation = any(k in ans_lower for k in [
            "does not specify", "do not specify", "missing specification",
            "does not contain", "do not contain", "not covered", "not addressed",
            "no explicit", "not explicitly", "neither permitted nor",
            "escalat", "unverified figure", "recommend consulting", "consult your",
            "consult the", "internal controls", "sox compliance", "segregation of duties",
            "no numeric window", "unverified"
        ])

        # 5. Determine Answer Status and Governance Decision
        if has_conflicts:
            answer_status = "DISPUTED"
            decision_verdict = "REVIEW"
            confidence = round(max(0.65, avg_trust * 0.85), 2)
        elif is_gap_or_escalation:
            answer_status = "PARTIAL"
            decision_verdict = "REVIEW"
            confidence = round(max(0.65, avg_trust * 0.85), 2)
        elif avg_trust >= 0.70:
            answer_status = "ANSWERED"
            decision_verdict = "ALLOW"
            confidence = round(min(0.99, avg_trust), 2)
        else:
            answer_status = "REVIEW_RECOMMENDED"
            decision_verdict = "REVIEW"
            confidence = round(avg_trust, 2)

        # 6. Verify Synthesized Answer using AnswerVerifier
        verification_result = AnswerVerifier.verify(
            synthesized_answer=synthesized_answer,
            citations=citation_dicts,
            has_conflicts=has_conflicts,
            mode="document_qa",
        )

        if not verification_result.is_verified:
            if verification_result.verification_status == "CITATION_MISMATCH":
                answer_status = "PARTIAL"
                confidence = min(confidence, 0.60)
            elif verification_result.verification_status == "PARTIALLY_GROUNDED":
                if answer_status == "ANSWERED":
                    answer_status = "PARTIAL"
                    confidence = min(confidence, 0.70)

        if verification_result.hallucination_warnings:
            for hw in verification_result.hallucination_warnings:
                if hw not in warnings:
                    warnings.append(hw)

        # 7. Extract Conditions or Limitations
        conditions: List[str] = []
        for line in synthesized_answer.split("\n"):
            line_str = line.strip()
            if line_str.startswith(("-", "•", "*")) and any(kw in line_str.lower() for kw in ["condition", "exception", "unless", "provided that", "subject to", "require", "deadline"]):
                clean_bullet = line_str.lstrip("-•* ").strip()
                if clean_bullet and clean_bullet not in conditions:
                    conditions.append(clean_bullet)

        missing_facts: List[str] = []
        if is_gap_or_escalation or answer_status in ("PARTIAL", "CLARIFICATION_NEEDED"):
            missing_facts.append("Specific operational threshold or exception window requires contractual addendum.")

        return CopilotQueryResponse(
            trace_id=trace_id,
            answer_status=answer_status,
            decision_verdict=decision_verdict,
            synthesized_answer=synthesized_answer,
            citations=citations,
            conditions=conditions,
            missing_facts=missing_facts,
            warnings=warnings,
            has_conflicts=has_conflicts,
            trust_score=round(avg_trust, 2),
            confidence=confidence,
            review_options=["report_issue", "request_human_review"],
        )
