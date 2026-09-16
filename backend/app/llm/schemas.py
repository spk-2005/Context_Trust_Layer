from datetime import datetime
from pydantic import BaseModel, Field


class ExtractedClaim(BaseModel):
    claim_text: str = Field(..., description="The complete atomic fact statement")
    subject: str = Field(..., description="Entity or topic the claim is about")
    predicate: str = Field(..., description="Action, property, relation, or condition")
    object: str = Field(..., description="Value, quantity, state, or target entity")
    claim_type: str = Field(default="policy", description="Type of claim (e.g. policy, technical, financial, metric)")
    modality: str = Field(
        default="normative",
        description="Modality of claim: 'normative' (governing enterprise rule/obligation), 'illustrative' (example/hypothetical/scenario sample), or 'descriptive' (factual/contextual background)"
    )
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Extraction confidence score")
    evidence_text_span: str = Field(..., description="Exact substring quote from the source text backing this claim")
    valid_from: datetime | None = Field(default=None, description="Effective start date if mentioned")
    valid_until: datetime | None = Field(default=None, description="Expiration date if mentioned")


class ClaimExtractionResult(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list)
    extraction_model: str = "mock"
    extraction_method: str = "llm_structured_extraction"


class ContradictionResult(BaseModel):
    is_contradiction: bool
    conflict_type: str = "direct_contradiction"  # direct_contradiction, temporal_outdated, numerical_discrepancy, complementary
    severity: str = "high"  # high, medium, low
    confidence: float = Field(default=0.90, ge=0.0, le=1.0)
    reasoning: str = ""
