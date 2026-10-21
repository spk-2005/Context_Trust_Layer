"""
Unit tests for Release Certification Ledger & Merkle Audit Trail Engine (Sprint AF-13).
Validates:
1. Merkle ledger construction across candidate claims.
2. Cryptographic root hash and compliance seal generation.
3. Inclusion proof validation against root hash.
4. Correct partitioning into Human-Adjudicated vs Automated-Verified vs Provisional.
"""

import pytest
from app.evaluation.release_certification_ledger import (
    ReleaseCertificationEngine,
    CertificationLedger,
    ClaimCertificationRecord,
)
from app.services.merkle_service import verify_merkle_proof, MerkleProofStep


def test_build_certification_ledger_and_merkle_proof():
    mock_claims = [
        {
            "claim_id": "CLM-DOC057-001",
            "document_id": "DOC-057",
            "status": "CANONICAL",
            "subject": {"canonical_entity": "Customer"},
            "predicate": {"normalized_action": "may_transfer_perpetual_license"},
            "object": {"normalized_object": "perpetual licenses to Affiliate"},
            "modality": "MAY",
            "evidence": {
                "char_start": 100,
                "char_end": 180,
                "verbatim_quote": "Customer may transfer perpetual licenses to an Affiliate.",
            },
            "gates": {
                "span_exists": True,
                "clause_entails_claim": True,
                "subject_valid": True,
                "counterparty_resolved": True,
                "predicate_valid": True,
                "is_atomic": True,
                "is_not_duplicate": True,
                "claim_type_allowed": True,
                "human_approved_if_required": True,
            },
        },
        {
            "claim_id": "CLM-DOC057-002",
            "document_id": "DOC-057",
            "status": "CANONICAL",
            "subject": {"canonical_entity": "Microsoft"},
            "predicate": {"normalized_action": "grants_product_license"},
            "object": {"normalized_object": "limited license"},
            "modality": "MAY",
            "evidence": {
                "char_start": 200,
                "char_end": 280,
                "verbatim_quote": "Microsoft grants Customer a limited license.",
            },
            "gates": {
                "span_exists": True,
                "clause_entails_claim": True,
                "subject_valid": True,
                "counterparty_resolved": True,
                "predicate_valid": True,
                "is_atomic": True,
                "is_not_duplicate": True,
                "claim_type_allowed": True,
                "human_approved_if_required": True,
            },
        },
        {
            "claim_id": "CLM-DOC057-003",
            "document_id": "DOC-057",
            "status": "REJECTED",
            "subject": {"canonical_entity": "the following"},  # Bad fragment
            "predicate": {"normalized_action": "invalid_fragment"},
            "object": {"normalized_object": "non rule"},
            "modality": "MUST",
            "evidence": {"char_start": 0, "char_end": 50, "verbatim_quote": "The following items..."},
            "gates": {
                "span_exists": False,
                "clause_entails_claim": False,
                "subject_valid": False,
            },
        },
    ]

    adjudicated = {"CLM-DOC057-001"}
    sha_map = {"DOC-057": "a" * 64}

    ledger = ReleaseCertificationEngine.build_certification_ledger(
        mock_claims,
        adjudicated_claim_ids=adjudicated,
        doc_sha_map=sha_map,
    )

    assert ledger.release_version == "v3.0-certified-conditional"
    assert ledger.total_claims_evaluated == 3
    assert ledger.canonical_claims_count == 2
    assert ledger.human_certified_count == 1
    assert ledger.automated_certified_count == 1
    assert ledger.rejected_count == 1
    assert len(ledger.merkle_root_hash) == 64
    assert len(ledger.compliance_seal) == 64

    # Verify first claim record
    rec1 = ledger.certified_records[0]
    assert rec1.claim_id == "CLM-DOC057-001"
    assert rec1.certification_tier == "HUMAN_CERTIFIED"
    assert len(rec1.merkle_proof_path) > 0

    # Verify second claim record
    rec2 = ledger.certified_records[1]
    assert rec2.claim_id == "CLM-DOC057-002"
    assert rec2.certification_tier == "AUTOMATED_CERTIFIED"

    # Verify third claim record (rejected)
    rec3 = ledger.certified_records[2]
    assert rec3.claim_id == "CLM-DOC057-003"
    assert rec3.certification_tier == "REJECTED"

    # Verify cryptographic Merkle proof for rec1
    token1 = ReleaseCertificationEngine.compute_claim_token(
        claim_id=rec1.claim_id,
        document_id=rec1.document_id,
        doc_sha256=sha_map["DOC-057"],
        char_start=rec1.char_start,
        char_end=rec1.char_end,
        entailment_verified=rec1.clause_entails_claim_verified,
        span_verified=rec1.span_exists_verified,
    )
    proof_steps = [MerkleProofStep(**s) for s in rec1.merkle_proof_path]
    is_valid, computed_root = verify_merkle_proof(token1, ledger.merkle_root_hash, proof_steps)
    assert is_valid is True
    assert computed_root == ledger.merkle_root_hash
