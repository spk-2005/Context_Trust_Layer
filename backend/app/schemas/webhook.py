import uuid
from datetime import datetime
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, HttpUrl


class WebhookCreateRequest(BaseModel):
    organization_id: uuid.UUID
    name: str = Field(..., min_length=2, max_length=255, description="Human-friendly label e.g. 'Security Ops Slack'")
    url: str = Field(..., description="Target destination HTTP(S) endpoint")
    channel_type: Literal["slack", "pagerduty", "teams", "generic"] = "slack"
    min_liability_threshold_usd: float = Field(default=5000.0, ge=0.0, description="Minimum liability prevented required to trigger notification")
    trigger_on_block: bool = Field(default=True, description="Trigger on BLOCK verdicts")
    trigger_on_review: bool = Field(default=True, description="Trigger on REVIEW / REQUIRE_REVIEW verdicts")
    secret_token: Optional[str] = Field(default=None, description="Optional HMAC signing secret or Bearer token")


class WebhookUpdateRequest(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    channel_type: Optional[Literal["slack", "pagerduty", "teams", "generic"]] = None
    min_liability_threshold_usd: Optional[float] = None
    trigger_on_block: Optional[bool] = None
    trigger_on_review: Optional[bool] = None
    is_active: Optional[bool] = None
    secret_token: Optional[str] = None


class WebhookResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    name: str
    url: str
    channel_type: str
    min_liability_threshold_usd: float
    trigger_on_block: bool
    trigger_on_review: bool
    is_active: bool
    last_triggered_at: Optional[datetime] = None
    last_status_code: Optional[int] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class WebhookTestResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    message: str
    delivered_payload: Dict[str, Any]


class WebhookDispatchLogResponse(BaseModel):
    id: uuid.UUID
    webhook_id: uuid.UUID
    organization_id: uuid.UUID
    event_type: str
    liability_prevented_usd: float
    actor_id: str
    verdict: str
    response_status: Optional[int] = None
    response_body: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
