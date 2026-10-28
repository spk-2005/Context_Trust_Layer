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
    governance_config: Optional[dict] = Field(default_factory=dict)
    setup_completed: bool = False


class OrganizationResponse(OrganizationBase):
    id: uuid.UUID
    status: OrganizationStatus
    domain_whitelist: List[str] = Field(default_factory=list)
    allowed_auth_methods: List[str] = Field(
        default_factory=lambda: ["password", "google", "microsoft", "okta"]
    )
    governance_config: Optional[dict] = Field(default_factory=dict)
    setup_completed: bool = False
    member_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OrganizationSettingsUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    domain_whitelist: Optional[List[str]] = None
    allowed_auth_methods: Optional[List[str]] = None
    governance_config: Optional[dict] = None
    setup_completed: Optional[bool] = None


class WorkspaceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    domain: Optional[str] = Field("governance", max_length=50)
    icon: Optional[str] = Field("📁", max_length=20)
    description: Optional[str] = Field(None, max_length=500)


class WorkspaceUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    domain: Optional[str] = Field(None, max_length=50)
    icon: Optional[str] = Field(None, max_length=20)
    description: Optional[str] = Field(None, max_length=500)


class WorkspaceResponse(BaseModel):
    id: str
    name: str
    domain: str = "governance"
    icon: str = "📁"
    description: Optional[str] = ""
    created_at: Optional[str] = None


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


class OrganizationSetupMemberInvite(BaseModel):
    name: Optional[str] = None
    email: EmailStr
    role: str = "reviewer"
    department: Optional[str] = None


class OrganizationSetupWizardRequest(BaseModel):
    name: str
    slug: Optional[str] = None
    domain_whitelist: List[str] = Field(default_factory=list)
    allowed_auth_methods: List[str] = Field(default_factory=lambda: ["password", "google", "microsoft", "okta"])
    initial_members: List[OrganizationSetupMemberInvite] = Field(default_factory=list)
    industry: Optional[str] = "Financial Services & Capital Markets"
    trust_threshold: float = Field(default=0.70, ge=0.5, le=0.99)
    conflict_policy: str = Field(default="human_in_the_loop")
    regulatory_frameworks: List[str] = Field(default_factory=lambda: ["NIST AI 600-1", "EU AI Act"])
    liability_cap_usd: float = Field(default=50000.0)
    seed_baseline_policies: bool = True
    organization_id: Optional[uuid.UUID] = None
    initial_workspace: Optional[dict] = None


class SetupStepDetail(BaseModel):
    id: str
    title: str
    description: str
    completed: bool
    data: Optional[dict] = None


class OrganizationSetupStatusResponse(BaseModel):
    organization_id: uuid.UUID
    organization_name: str
    setup_completed: bool
    completion_percentage: int
    completed_steps_count: int
    total_steps_count: int
    steps: List[SetupStepDetail]
    next_recommended_step: str


class OrganizationSetupWizardResponse(BaseModel):
    organization: OrganizationResponse
    status: OrganizationSetupStatusResponse
    access_token: Optional[str] = None
    mcp_api_key: Optional[str] = None
    message: str

