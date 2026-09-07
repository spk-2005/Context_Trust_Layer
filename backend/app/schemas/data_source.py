import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import RecordStatus


class DataSourceCreate(BaseModel):
    organization_id: uuid.UUID = Field(default=uuid.UUID("11111111-1111-1111-1111-111111111111"))
    name: str
    source_type: str = Field(..., description="confluence, jira, github, portal, file")
    external_id: str | None = None
    authority_level: int = Field(default=80, ge=0, le=100)


class DataSourceResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    source_type: str
    external_id: str | None = None
    authority_level: int
    status: RecordStatus
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
