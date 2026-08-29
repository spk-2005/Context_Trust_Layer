import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.db.enums import OrganizationStatus


class OrganizationBase(BaseModel):
    name: str
    slug: str


class OrganizationCreate(OrganizationBase):
    pass


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    status: OrganizationStatus
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
