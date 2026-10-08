import uuid
from collections.abc import Sequence
from typing import Generic, TypeVar

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    def __init__(self, model: type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: uuid.UUID) -> ModelType | None:
        return await self.session.get(self.model, entity_id)

    async def get(self, entity_id: uuid.UUID) -> ModelType | None:
        return await self.get_by_id(entity_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> Sequence[ModelType]:
        stmt = select(self.model).offset(offset).limit(limit)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def create(self, entity: ModelType) -> ModelType:
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete_by_id(self, entity_id: uuid.UUID) -> bool:
        stmt = delete(self.model).where(self.model.id == entity_id)
        result = await self.session.execute(stmt)
        await self.session.flush()
        return result.rowcount > 0
