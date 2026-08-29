import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.agent_context_item import AgentContextItem
from app.db.models.agent_request import AgentRequest
from app.db.repositories.base import BaseRepository


class ContextRepository(BaseRepository[AgentRequest]):
    def __init__(self, session: AsyncSession):
        super().__init__(AgentRequest, session)

    async def get_request_with_items(
        self,
        request_id: uuid.UUID,
    ) -> AgentRequest | None:
        stmt = (
            select(AgentRequest)
            .where(AgentRequest.id == request_id)
            .options(
                selectinload(AgentRequest.context_items).selectinload(
                    AgentContextItem.claim
                )
            )
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_requests_by_agent(
        self,
        agent_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[AgentRequest]:
        stmt = (
            select(AgentRequest)
            .where(AgentRequest.agent_id == agent_id)
            .offset(offset)
            .limit(limit)
            .options(selectinload(AgentRequest.context_items))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
