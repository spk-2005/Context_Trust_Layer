import decimal
import logging
import uuid
from typing import Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.chat_repository import ChatRepository
from app.llm.factory import get_llm_provider
from app.retrieval.engine import ContextRetrievalEngine
from app.schemas.context import ContextQueryRequest

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.repo = ChatRepository(session)
        self.llm = get_llm_provider()

    async def list_sessions(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        sessions = await self.repo.list_sessions(organization_id, user_id, limit)
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
    ) -> dict[str, Any]:
        s = await self.repo.create_session(
            organization_id=organization_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            title=title,
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
    ) -> dict[str, Any]:
        # 1. Store user message in DB
        user_msg = await self.repo.add_message(
            session_id=session_id,
            role="user",
            content=content,
            metadata_json={"author": user_name, "role": user_role},
        )

        # 2. Query Context Retrieval Engine for grounded evidence
        retrieval_engine = ContextRetrievalEngine(self.session, self.llm)
        # Use default seed agent or find agent for organization
        default_agent_id = uuid.UUID("88888888-8888-8888-8888-888888888888")
        context_req = ContextQueryRequest(
            organization_id=organization_id,
            agent_id=default_agent_id,
            query=content,
            min_trust_score=decimal.Decimal("0.50"),
            max_results=8,
        )
        context_res = await retrieval_engine.query_context(context_req)

        # 3. Analyze retrieved context, conflicts, and trust scores
        included_claims = context_res.context
        has_conflicts = len(context_res.conflicts) > 0
        
        avg_trust = (
            sum(float(item.trust_score) for item in included_claims) / len(included_claims)
            if included_claims else 0.50
        )

        # 4. Formulate citations & warnings
        citations = []
        for item in included_claims:
            citations.append({
                "claim_text": item.claim,
                "trust_score": float(item.trust_score),
                "source_title": item.source.document if item.source else "Knowledge Base",
                "section": item.source.section if item.source else None,
                "validity": item.validity.status if item.validity else "active",
                "evidence": item.evidence,
            })

        warnings = []
        if has_conflicts:
            for conf in context_res.conflicts:
                desc = conf.get("description") or "Contradictory evidence detected between active sources."
                warnings.append(f"Disputed evidence: {desc}")

        # 5. Determine verification verdict
        if not included_claims:
            decision = "CLARIFY"
            confidence = 0.50
        elif has_conflicts:
            decision = "REVIEW"
            confidence = round(max(0.60, avg_trust * 0.85), 2)
        elif avg_trust >= 0.70:
            decision = "ALLOW"
            confidence = round(min(0.99, avg_trust), 2)
        else:
            decision = "REVIEW"
            confidence = round(avg_trust, 2)

        # 6. Synthesize grounded answer via configured LLM provider (Ox Alpha / OpenRouter / OpenAI / Mock)
        synthesized_answer = await self.llm.generate_grounded_answer(
            query=content,
            citations=citations,
            has_conflicts=has_conflicts,
            warnings=warnings,
        )

        metadata_json = {
            "decision": decision,
            "confidence": confidence,
            "trust_score": round(avg_trust, 2),
            "citations": citations,
            "warnings": warnings,
            "has_conflicts": has_conflicts,
            "total_evaluated_claims": len(context_res.context),
        }

        # 6. Store assistant message in DB
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
