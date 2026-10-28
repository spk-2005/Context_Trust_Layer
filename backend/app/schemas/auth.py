import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.db.enums import UserRole, RecordStatus


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=4)
    device_id: Optional[str] = None


class PersonaLoginRequest(BaseModel):
    user_id: Optional[uuid.UUID] = None
    email: Optional[str] = None
    role: Optional[str] = None
    device_id: Optional[str] = None


class UserRegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=6)
    name: str = Field(..., min_length=2, max_length=255)
    organization_name: Optional[str] = Field(None, max_length=255)
    role: Optional[UserRole] = Field(default=UserRole.DEVELOPER)
    department: Optional[str] = Field(None, max_length=100)
    title: Optional[str] = Field(None, max_length=100)
    device_id: Optional[str] = None


class TokenRefreshRequest(BaseModel):
    refresh_token: str
    device_id: Optional[str] = None


class OrganizationSummary(BaseModel):
    id: uuid.UUID
    name: str
    slug: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    organization_name: Optional[str] = None
    name: str
    email: str
    role: str
    status: str
    avatar_url: Optional[str] = None
    title: Optional[str] = None
    department: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    timezone: Optional[str] = None
    user_preferences: Optional[dict] = None
    active_device_id: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 86400  # 24 hours in seconds
    user: UserResponse
    is_new_user: bool = False
    pending_invitations: list[dict] = Field(default_factory=list)
    organizations: list[dict] = Field(default_factory=list)
