import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.db.enums import OrganizationStatus
from app.schemas.auth import UserResponse


class OrganizationBase(BaseModel):
    name: str
    slug: str


class OrganizationCreate(OrganizationBase):
    domain_whitelist: List[str] = Field(default_factory=list)
    allowed_auth_methods: List[str] = Field(
        default_factory=lambda: ["password", "google", "microsoft", "okta"]
    )


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    status: OrganizationStatus
    domain_whitelist: List[str] = Field(default_factory=list)
    allowed_auth_methods: List[str] = Field(
        default_factory=lambda: ["password", "google", "microsoft", "okta"]
    )
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationSettingsUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    domain_whitelist: Optional[List[str]] = None
    allowed_auth_methods: Optional[List[str]] = None


class OrganizationMemberResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    role: str
    status: str
    title: Optional[str] = None
    department: Optional[str] = None
    avatar_url: Optional[str] = None
    is_verified: bool = True
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationMemberRoleUpdate(BaseModel):
    role: str = Field(..., description="Target role: admin, data_owner, reviewer, operator, developer")


class InviteCreateRequest(BaseModel):
    email: EmailStr
    role: str = Field(default="developer", description="Assigned role upon joining")


class InviteResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: str
    email: str
    role: str
    token: str
    invite_url: str
    status: str
    expires_at: datetime
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class InviteInspectResponse(BaseModel):
    token: str
    organization_id: uuid.UUID
    organization_name: str
    organization_slug: str
    email: str
    role: str
    expires_at: datetime
    is_expired: bool


class InviteAcceptRequest(BaseModel):
    token: str
    full_name: Optional[str] = None
    password: Optional[str] = None


class TenantSwitchResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400
    user: UserResponse
    active_organization: OrganizationResponse
