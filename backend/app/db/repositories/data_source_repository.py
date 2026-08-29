import uuid

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
    ) -> DataSource:
        if external_id:
            existing = await self.get_by_external_id(
                organization_id=organization_id,
                source_type=source_type,
                external_id=external_id,
            )
            if existing:
                return existing

        source = DataSource(
            organization_id=organization_id,
            name=name,
            source_type=source_type,
            external_id=external_id,
            authority_level=authority_level,
        )
        return await self.create(source)
