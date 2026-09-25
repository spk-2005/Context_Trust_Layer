import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClaimDecayItem(BaseModel):
    claim_id: uuid.UUID
    claim_text: str
    document_title: str
    created_at: datetime
    age_days: int
    initial_trust: float
    current_decayed_trust: float
    decay_pct: float
    drift_category: str  # "ACTIVE_FRESH", "AGING_WARNING", "STALE_TEMPORAL", "SEVERELY_DECAYED"
    recommended_action: str


class DriftAnalysisResponse(BaseModel):
    organization_id: uuid.UUID
    analyzed_at: datetime
    total_claims: int
    fresh_claims_count: int
    decayed_claims_count: int
    stale_documents_count: int
    average_age_days: int
    freshness_index_pct: float  # 0.0 - 100.0%
    decay_radar: Dict[str, int]  # e.g. {"<30d": 12, "30-90d": 8, "90-180d": 4, ">180d": 2}
    decayed_claims: List[ClaimDecayItem]


class ClaimRemediateRequest(BaseModel):
    claim_id: uuid.UUID
    action: str = Field(..., description="'RE_ATTEST' (refresh timestamp to today) or 'RETIRE' (deprecate)")
    notes: Optional[str] = None


class ClaimRemediateResponse(BaseModel):
    claim_id: uuid.UUID
    action_taken: str
    new_status: str
    new_trust_score: float
    message: str
    timestamp: datetime
