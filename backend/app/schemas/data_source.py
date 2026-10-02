import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import RecordStatus


class DataSourceCreate(BaseModel):
    organization_id: uuid.UUID = Field(default=uuid.UUID("11111111-1111-1111-1111-111111111111"))
    name: str
    source_type: str = Field(..., description="confluence, jira, github, postgresql, kafka, salesforce, mongodb, portal, file, snowflake, s3, etc.")
    external_id: str | None = None
    authority_level: int = Field(default=80, ge=0, le=100)
    connection_config: dict[str, Any] | None = Field(default_factory=dict)
    owner_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class DataSourceResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    source_type: str
    external_id: str | None = None
    authority_level: int
    connection_config: dict[str, Any] | None = None
    owner_id: uuid.UUID | None = None
    status: RecordStatus
    last_synced_at: datetime | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConnectionTestRequest(BaseModel):
    source_type: str = Field(..., description="postgresql, kafka, salesforce, mongodb, github, confluence, jira")
    connection_config: dict[str, Any] = Field(default_factory=dict)


class ConnectionTestResult(BaseModel):
    success: bool
    status: str = "ok"  # ok, error, warning
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    tested_at: datetime

