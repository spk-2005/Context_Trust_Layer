import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.merkle import (
    MerkleCertificateResponse,
    MerkleLedgerStatusResponse,
    MerkleProofResponse,
    MerkleVerificationRequest,
    MerkleVerificationResponse,
)
from app.services.merkle_service import (
    generate_compliance_certificate,
    generate_merkle_proof,
    get_ledger_tokens,
    get_merkle_status,
    verify_merkle_proof,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/merkle", tags=["Cryptographic Merkle Audit Ledger"])


@router.get("/status", response_model=MerkleLedgerStatusResponse)
async def get_ledger_status(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve current Merkle Root, batch height, and cryptographic ledger status."""
    return await get_merkle_status(organization_id, session=db)


@router.get("/proof/{audit_token}", response_model=MerkleProofResponse)
async def get_proof_for_token(
    audit_token: str,
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a cryptographic Merkle inclusion proof proving that an audit record is permanently sealed."""
    tokens = await get_ledger_tokens(organization_id, session=db)
    proof = generate_merkle_proof(audit_token, tokens)
    if not proof:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit token '{audit_token}' could not be proven in ledger.",
        )
    return proof


@router.post("/verify", response_model=MerkleVerificationResponse)
async def verify_proof_independently(payload: MerkleVerificationRequest):
    """Verifies a Merkle inclusion proof independently using pure SHA-256 math."""
    is_valid, computed_root = verify_merkle_proof(
        payload.audit_token, payload.root_hash, payload.proof_path
    )
    message = (
        "Cryptographic proof verified successfully: Audit record is sealed in the Merkle ledger."
        if is_valid
        else "Verification failed: Computed root hash does not match expected ledger anchor."
    )
    return MerkleVerificationResponse(
        is_valid=is_valid,
        computed_root_hash=computed_root,
        expected_root_hash=payload.root_hash,
        audit_token=payload.audit_token,
        message=message,
    )


@router.get("/certificate/{audit_token}", response_model=MerkleCertificateResponse)
async def get_compliance_certificate(
    audit_token: str,
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    db: AsyncSession = Depends(get_db),
):
    """Generates an exportable EU AI Act Article 12 compliance certificate for an audited decision."""
    return await generate_compliance_certificate(audit_token, organization_id, session=db)
