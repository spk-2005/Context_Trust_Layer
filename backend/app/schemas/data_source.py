import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import RecordStatus


class DataSourceBase(BaseModel):
    name: str
    source_type: str
    external_id: str | None = None
    authority_level: int = Field(default=50, ge=0, le=100)


class DataSourceCreate(DataSourceBase):
    organization_id: uuid.UUID


class DataSourceResponse(DataSourceBase):
    id: uuid.UUID
    organization_id: uuid.UUID
    status: RecordStatus
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
