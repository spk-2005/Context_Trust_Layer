import decimal
import logging
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.chat_repository import ChatRepository
from app.decision_engine.evaluator import DecisionEvaluator
from app.llm.factory import get_llm_provider
from app.retrieval.engine import ContextRetrievalEngine
from app.schemas.context import ContextQueryRequest
from app.schemas.decision import DecisionActor, DecisionContextItem, DecisionEvaluateRequest
from app.services.answer_verifier import AnswerVerifier
from app.services.context_resolver import ConversationContextResolver

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ChatRepository(session)
        self.llm = get_llm_provider()
        self.resolver = ConversationContextResolver(self.llm)

    async def list_sessions(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        workspace_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        sessions = await self.repo.list_sessions(organization_id, user_id, workspace_id, limit)
        return [s.to_dict() for s in sessions]

    async def get_session(self, session_id: uuid.UUID) -> dict[str, Any] | None:
        s = await self.repo.get_session(session_id)
        if not s:
            return None
        res = s.to_dict()
        res["messages"] = [m.to_dict() for m in (s.messages or [])]
        return res

    async def create_session(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        user_name: str,
        user_role: str,
        title: str = "New Conversation",
        workspace_id: str | None = "all",
        domain: str | None = "global",
    ) -> dict[str, Any]:
        s = await self.repo.create_session(
            organization_id=organization_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            title=title,
            workspace_id=workspace_id or "all",
            domain=domain or "global",
        )
        await self.session.commit()
        return s.to_dict()

    async def delete_session(self, session_id: uuid.UUID) -> bool:
        success = await self.repo.delete_session(session_id)
        await self.session.commit()
        return success

    async def process_user_message(
        self,
        session_id: uuid.UUID,
        organization_id: uuid.UUID,
        content: str,
        user_id: uuid.UUID | None = None,
        user_name: str = "User",
        user_role: str = "developer",
        workspace_id: str | None = None,
        domain: str | None = None,
    ) -> dict[str, Any]:
        # 1. Fetch existing session & conversation history
        session_obj = await self.repo.get_session(session_id)
        recent_history: list[dict[str, str]] = []
        if session_obj and session_obj.messages:
            for m in session_obj.messages[-6:]:
                if m.role in ("user", "assistant") and m.content:
                    recent_history.append({"role": m.role, "content": m.content})

        # 2. Store new user message in DB
        user_msg = await self.repo.add_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata_json={"author": user_name, "role": user_role, "workspace_id": workspace_id, "domain": domain},
        )

        effective_domain = domain or (session_obj.domain if session_obj else None) or "global"
        effective_workspace = workspace_id or (session_obj.workspace_id if session_obj else None) or "all"

        # 3. Detect operational mode (Mode A: Document Q&A vs Mode B: Action Evaluation)
        q_lower = content.lower().strip()
        action_patterns = [
            "can i ", "can we ", "may i ", "may we ", "am i allowed to", "is the agent allowed to",
            "can this agent", "approve ", "issue refund", "grant access", "override", "open port",
            "bypass", "execute ", "authorize ", "permitted to "
        ]
        is_action_eval = any(p in q_lower for p in action_patterns) or (
            any(k in q_lower for k in ["refund", "credit", "firewall", "port 22", "bypass", "access"]) and
            any(v in q_lower for v in ["can", "may", "allowed", "approve", "authorize", "issue"])
        )
        mode = "action_evaluation" if is_action_eval else "document_qa"

        # 4. Resolve conversational query for multi-turn context and query Context Retrieval Engine
        resolved_query = await self.resolver.resolve_query(content, recent_history)

        retrieval_engine = ContextRetrievalEngine(self.session, self.llm)
        default_agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
        context_req = ContextQueryRequest(
            organization_id=organization_id,
            agent_id=default_agent_id,
            query=resolved_query,
            min_trust_score=decimal.Decimal("0.50"),
            max_results=8,
            domain=effective_domain,
            workspace_id=effective_workspace,
        )
        context_res = await retrieval_engine.query_context(context_req)

        # 5. Extract retrieved context, conflicts, and trust scores
        included_claims = context_res.context
        has_conflicts = len(context_res.conflicts) > 0

        avg_trust = (
            sum(float(item.trust_score) for item in included_claims) / len(included_claims)
            if included_claims else 0.50
        )

        # 6. Formulate citations with full provenance (deduplicating identical claim statements)
        citations = []
        seen_claims = set()
        for idx, item in enumerate(included_claims):
            norm_text = item.claim.strip().lower()
            if norm_text in seen_claims:
                continue
            seen_claims.add(norm_text)
            citations.append({
                "source_index": idx + 1,
                "claim_id": item.claim_id,
                "document_id": item.document_id,
                "folder_name": getattr(item.source, "folder_name", None) or (item.governed_package.folder_name if item.governed_package else None) or "Enterprise Policies",
                "folder_id": getattr(item.source, "folder_id", None) or (item.governed_package.folder_id if item.governed_package else None),
                "evidence_lane": getattr(item, "evidence_lane", "canonical"),
                "claim_text": item.claim,
                "trust_score": float(item.trust_score),
                "source_title": item.source.document if item.source else "Knowledge Base",
                "section": item.source.section if item.source else None,
                "page": item.source.page if item.source else None,
                "validity": item.validity.status if item.validity else "active",
                "evidence": item.evidence,
            })

        warnings = []
        if has_conflicts:
            for conf in context_res.conflicts:
                desc = conf.get("description") or "Contradictory evidence detected between active sources."
                warnings.append(f"Disputed evidence: {desc}")

        # 7. Execute according to Mode
        audit_id = None
        risk_level = None
        answer_status = None

        if mode == "action_evaluation":
            # Mode B: Evaluate Proposed Action via DecisionEvaluator
            decision_contexts = [
                DecisionContextItem(
                    claim=item.claim,
                    source=item.source.document if item.source else "Knowledge Base",
                    authority_level=int(float(item.trust_score) * 100),
                    scope=effective_domain,
                )
                for item in included_claims
            ]
            evaluator = DecisionEvaluator(llm_provider=self.llm, session=self.session)
            eval_req = DecisionEvaluateRequest(
                decision=content,
                actor=DecisionActor(id=str(user_id or "user-default"), role=user_role),
                context=decision_contexts,
                organization_id=organization_id,
            )
            eval_res = await evaluator.evaluate(eval_req, session=self.session)

            decision = eval_res.decision  # ALLOW, BLOCK, REVIEW, CLARIFY
            risk_level = eval_res.risk    # LOW, MEDIUM, HIGH
            audit_id = eval_res.audit_id
            confidence = round(max(0.70, avg_trust), 2)
            answer_status = "EVALUATED"

            # Format authoritative decision report
            bullet_reasons = "\n".join(f"- {r}" for r in eval_res.reasons) if eval_res.reasons else "- Evaluated against enterprise baseline policies."
            next_action_str = f"\n\n**Recommended Next Action:** {eval_res.suggested_action}" if eval_res.suggested_action else ""
            synthesized_answer = (
                f"### 🛡️ Decision Governance Verdict: **{decision}**\n\n"
                f"**Evaluated Action:** {content}\n\n"
                f"**Policy Findings & Entitlements:**\n{bullet_reasons}"
                f"{next_action_str}\n\n"
                f"🔒 **Governance Audit ID:** `{audit_id}` • **Risk Assessment:** {risk_level}"
            )
        else:
            # Mode A: Document Q&A Synthesis with multi-turn history
            synthesized_answer = await self.llm.generate_grounded_answer(
                query=content,
                citations=citations,
                has_conflicts=has_conflicts,
                warnings=warnings,
                history=recent_history,
            )

            ans_lower = synthesized_answer.lower()
            is_gap_or_escalation = any(k in ans_lower for k in [
                "does not specify", "do not specify", "missing specification",
                "does not contain", "do not contain", "not covered", "not addressed",
                "no explicit", "not explicitly", "neither permitted nor",
                "escalat", "unverified figure", "recommend consulting", "consult your",
                "consult the", "internal controls", "sox compliance", "segregation of duties",
                "segregation-of-duties", "no numeric window", "unverified"
            ])

            if not included_claims:
                answer_status = "CLARIFICATION_NEEDED"
                decision = "CLARIFY"
                confidence = 0.50
            elif has_conflicts:
                answer_status = "DISPUTED"
                decision = "REVIEW"
                confidence = round(max(0.65, avg_trust * 0.85), 2)
            elif is_gap_or_escalation:
                answer_status = "PARTIAL"
                decision = "REVIEW"
                confidence = round(max(0.65, avg_trust * 0.85), 2)
            elif avg_trust >= 0.70:
                answer_status = "ANSWERED"
                decision = "ALLOW"
                confidence = round(min(0.99, avg_trust), 2)
            else:
                answer_status = "REVIEW_RECOMMENDED"
                decision = "REVIEW"
                confidence = round(avg_trust, 2)

        # 7. Verify synthesized answer against retrieved citations and numerical assertions
        verification_result = AnswerVerifier.verify(
            synthesized_answer=synthesized_answer,
            citations=citations,
            has_conflicts=has_conflicts,
            mode=mode,
        )

        if not verification_result.is_verified:
            if verification_result.verification_status == "CITATION_MISMATCH":
                if mode == "document_qa":
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

        metadata_json = {
            "mode": mode,
            "resolved_query": resolved_query if resolved_query != content else None,
            "answer_status": answer_status,
            "decision": decision,
            "risk_level": risk_level,
            "audit_id": audit_id,
            "confidence": confidence,
            "trust_score": round(avg_trust, 2),
            "citations": citations,
            "warnings": warnings,
            "has_conflicts": has_conflicts,
            "conflicts": context_res.conflicts,
            "total_evaluated_claims": len(context_res.context),
            "verification": verification_result.to_dict(),
        }

        # 8. Store assistant message in DB
        assistant_msg = await self.repo.add_message(
            session_id=session_id,
            role="assistant",
            content=synthesized_answer,
            metadata_json=metadata_json,
        )

        await self.session.commit()

        return {
            "session_id": str(session_id),
            "user_message": user_msg.to_dict(),
            "assistant_message": assistant_msg.to_dict(),
        }
