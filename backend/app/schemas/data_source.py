import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import RecordStatus


class DataSourceCreate(BaseModel):
    organization_id: uuid.UUID = Field(default=uuid.UUID("11111111-1111-1111-1111-111111111111"))
    name: str
    source_type: str = Field(..., description="github, mongodb, jira, confluence, postgresql, etc.")
    external_id: str | None = None
    authority_level: int = Field(default=80, ge=0, le=100)
    connection_config: dict[str, Any] | None = Field(default_factory=dict)
    owner_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None


class DataSourceUpdate(BaseModel):
    name: str | None = None
    authority_level: int | None = Field(default=None, ge=0, le=100)
    connection_config: dict[str, Any] | None = None


class ScheduleUpdateRequest(BaseModel):
    schedule: str = Field(..., description="'off', '1m', '10m'")


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
    source_type: str = Field(..., description="github, mongodb, mongodb_atlas, jira, confluence, postgresql")
    connection_config: dict[str, Any] = Field(default_factory=dict)


class ConnectionTestResult(BaseModel):
    success: bool
    status: str = "ok"  # ok, error, warning
    message: str
    details: dict[str, Any] = Field(default_factory=dict)
    tested_at: datetime


class ResourceDiscoveryRequest(BaseModel):
    source_type: str = Field(..., description="github, mongodb, jira, confluence, postgresql")
    connection_config: dict[str, Any] = Field(default_factory=dict)
    target_resource: str = "default"  # repos, databases, collections, projects, spaces, schemas, tables
    parent_resource: str | None = None  # e.g. database name or schema name


class ResourceDiscoveryResponse(BaseModel):
    source_type: str
    target_resource: str
    items: list[Any] = Field(default_factory=list)
    total_count: int = 0
