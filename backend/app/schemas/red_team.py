import uuid
from datetime import datetime
from typing import Any, List, Optional
from pydantic import BaseModel, Field


class RedTeamAttackCase(BaseModel):
    id: str
    name: str
    category: str  # "PROMPT_INJECTION", "DATA_EXFILTRATION", "PRIVILEGE_ESCALATION", "JAILBREAK", "BENIGN_CONTROL"
    severity: str  # "CRITICAL", "HIGH", "MEDIUM", "LOW"
    actor_id: str
    actor_role: str
    prompt: str
    description: str
    expected_verdicts: List[str] = Field(default_factory=lambda: ["BLOCK", "REVIEW"])
    is_benign: bool = False


class RedTeamCaseResult(BaseModel):
    case_id: str
    name: str
    category: str
    severity: str
    actor_role: str
    prompt: str
    verdict: str
    risk_level: str
    passed: bool  # True if attack was intercepted (or benign allowed), False if breached/false positive
    outcome_status: str  # "INTERCEPTED", "BREACHED", "BENIGN_PASSED", "FALSE_POSITIVE"
    reasons: List[str] = Field(default_factory=list)
    suggested_action: Optional[str] = None
    execution_ms: int = 0
    liability_prevented_usd: float = 0.0


class RedTeamRunRequest(BaseModel):
    organization_id: Optional[uuid.UUID] = None
    categories: Optional[List[str]] = None
    custom_attacks: Optional[List[RedTeamAttackCase]] = None


class RedTeamRunResponse(BaseModel):
    run_id: str
    timestamp: datetime
    total_tests: int
    passed_tests: int
    failed_tests: int
    robustness_score: float  # 0.0 - 100.0%
    interception_rate: float  # % of malicious attacks caught
    false_positive_rate: float  # % of benign prompts blocked
    total_liability_guarded_usd: float
    category_summary: dict[str, Any]
    results: List[RedTeamCaseResult]


class CustomInjectRequest(BaseModel):
    prompt: str = Field(..., description="Adversarial or benign prompt to test")
    actor_role: str = Field(default="support", description="Simulated agent role")
    actor_id: str = Field(default="red-team-agent", description="Simulated agent ID")
    category: Optional[str] = "CUSTOM_INJECTION"
    organization_id: Optional[uuid.UUID] = None


class CustomInjectResponse(BaseModel):
    verdict: str
    risk_level: str
    intercepted: bool
    reasons: List[str]
    suggested_action: Optional[str]
    liability_prevented_usd: float
    execution_ms: int
