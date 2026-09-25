import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MerkleProofStep(BaseModel):
    hash: str
    direction: str = Field(..., description="'left' (sibling is on left) or 'right' (sibling is on right)")


class MerkleProofResponse(BaseModel):
    audit_token: str
    leaf_hash: str
    root_hash: str
    is_valid: bool
    batch_size: int
    tree_depth: int
    proof_path: List[MerkleProofStep]
    timestamp: datetime


class MerkleLedgerStatusResponse(BaseModel):
    root_hash: str
    total_sealed_records: int
    tree_depth: int
    batch_height: int
    last_anchored_at: datetime
    compliance_standard: str = "EU AI Act Art. 12 & NIST AI GOVERN 1.2"


class MerkleVerificationRequest(BaseModel):
    audit_token: str
    root_hash: str
    proof_path: List[MerkleProofStep]


class MerkleVerificationResponse(BaseModel):
    is_valid: bool
    computed_root_hash: str
    expected_root_hash: str
    audit_token: str
    message: str


class MerkleCertificateResponse(BaseModel):
    certificate_id: str
    audit_token: str
    decision_id: Optional[str] = None
    actor_id: Optional[str] = None
    actor_role: Optional[str] = None
    verdict: Optional[str] = None
    leaf_hash: str
    root_hash: str
    timestamp: datetime
    compliance_seal: str
    proof_path: List[MerkleProofStep]
    tamper_evident: bool = True
