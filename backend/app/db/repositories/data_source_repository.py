import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.data_source import DataSource
from app.db.repositories.base import BaseRepository


class DataSourceRepository(BaseRepository[DataSource]):
    def __init__(self, session: AsyncSession):
        super().__init__(DataSource, session)

    async def get_by_external_id(
        self,
        organization_id: uuid.UUID,
        source_type: str,
        external_id: str,
    ) -> DataSource | None:
        stmt = select(DataSource).where(
            DataSource.organization_id == organization_id,
            DataSource.source_type == source_type,
            DataSource.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        organization_id: uuid.UUID,
        name: str,
        source_type: str,
        external_id: str | None = None,
        authority_level: int = 50,
        connection_config: dict | None = None,
        owner_id: uuid.UUID | None = None,
        source_family: Any = None,
        source_intent: Any = None,
        scope_config: dict | None = None,
        capabilities: dict | None = None,
    ) -> DataSource:
        ext_id = external_id or f"{source_type}-{uuid.uuid4().hex[:8]}"
        existing = await self.get_by_external_id(
            organization_id=organization_id,
            source_type=source_type,
            external_id=ext_id,
        )
        if existing:
            if connection_config:
                existing.connection_config = connection_config
            if scope_config:
                existing.scope_config = scope_config
            if capabilities:
                existing.capabilities = capabilities
            if source_family:
                existing.source_family = source_family
            if source_intent:
                existing.source_intent = source_intent
            if owner_id:
                existing.owner_id = owner_id
            await self.session.flush()
            return existing

        source = DataSource(
            organization_id=organization_id,
            name=name,
            source_type=source_type,
            external_id=ext_id,
            authority_level=authority_level,
            connection_config=connection_config or {},
            scope_config=scope_config or {},
            capabilities=capabilities or {},
            owner_id=owner_id,
        )
        if source_family:
            source.source_family = source_family
        if source_intent:
            source.source_intent = source_intent

        return await self.create(source)

    async def list_by_organization(
        self,
        organization_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[DataSource]:
        stmt = (
            select(DataSource)
            .where(DataSource.organization_id == organization_id)
            .offset(offset)
            .limit(limit)
            .order_by(DataSource.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()
