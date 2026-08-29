import decimal
import uuid
from pydantic import BaseModel, Field


class ContextQueryRequest(BaseModel):
    organization_id: uuid.UUID
    agent_id: uuid.UUID
    query: str
    min_trust_score: decimal.Decimal = Field(
        default=decimal.Decimal("0.8000"),
        ge=0,
        le=1,
    )
    max_results: int = Field(default=10, gt=0)


class ContextSourceInfo(BaseModel):
    document: str
    section: str | None = None
    page: int | None = None


class ContextValidityInfo(BaseModel):
    status: str
    valid_from: str | None = None
    valid_until: str | None = None


class ContextItemResponse(BaseModel):
    claim: str
    trust_score: decimal.Decimal
    validity: ContextValidityInfo
    source: ContextSourceInfo
    evidence: list[str] = []


class ContextQueryResponse(BaseModel):
    context: list[ContextItemResponse] = []
    conflicts: list[dict] = []
    confidence: decimal.Decimal = decimal.Decimal("1.0000")
