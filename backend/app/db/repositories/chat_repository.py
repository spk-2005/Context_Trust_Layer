import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.chat import ChatSession, ChatMessage
from app.db.repositories.base import BaseRepository


class ChatRepository(BaseRepository[ChatSession]):
    def __init__(self, session: AsyncSession):
        super().__init__(ChatSession, session)

    async def list_sessions(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        limit: int = 50,
    ) -> Sequence[ChatSession]:
        stmt = (
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.organization_id == organization_id)
        )
        if user_id:
            stmt = stmt.where(ChatSession.user_id == user_id)
        
        stmt = stmt.order_by(ChatSession.updated_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_session(self, session_id: uuid.UUID) -> ChatSession | None:
        stmt = (
            select(ChatSession)
            .options(selectinload(ChatSession.messages))
            .where(ChatSession.id == session_id)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_session(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None,
        user_name: str,
        user_role: str,
        title: str = "New Conversation",
    ) -> ChatSession:
        session_obj = ChatSession(
            organization_id=organization_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            title=title,
        )
        self.session.add(session_obj)
        await self.session.flush()
        await self.session.refresh(session_obj)
        return session_obj

    async def add_message(
        self,
        session_id: uuid.UUID,
        role: str,
        content: str,
        metadata_json: dict | None = None,
    ) -> ChatMessage:
        message = ChatMessage(
            session_id=session_id,
            role=role,
            content=content,
            metadata_json=metadata_json or {},
        )
        self.session.add(message)

        # Update parent session's updated_at timestamp
        session_obj = await self.get_by_id(session_id)
        if session_obj:
            session_obj.updated_at = datetime.now(timezone.utc)
            # If title is default, generate from first user message
            if role == "user" and session_obj.title == "New Conversation":
                clean_title = content.strip().split("\n")[0][:60]
                if clean_title:
                    session_obj.title = clean_title

        await self.session.flush()
        await self.session.refresh(message)
        return message

    async def delete_session(self, session_id: uuid.UUID) -> bool:
        stmt = delete(ChatSession).where(ChatSession.id == session_id)
        result = await self.session.execute(stmt)
        return result.rowcount > 0
