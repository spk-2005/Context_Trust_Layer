import pytest
from app.ingestion.grounding_verifier import GroundingVerifier
from app.llm.schemas import ExtractedClaim


def test_grounding_verifier_prefilter():
    # Assertive text should pass pre-filter
    assert GroundingVerifier.needs_claim_extraction("All accounts must use multi-factor authentication.")
    assert GroundingVerifier.needs_claim_extraction("Refund exception window is 60 days.")
    assert GroundingVerifier.needs_claim_extraction("Contractors may access VPN with approval.")
    
    # Noise text should be skipped
    assert not GroundingVerifier.needs_claim_extraction("Page 1 of 10")
    assert not GroundingVerifier.needs_claim_extraction("Table of Contents")


def test_grounding_verifier_valid_exact_evidence():
    source_text = "All privileged accounts must use multi-factor authentication. Passwords must be at least 14 characters long."
    claim = ExtractedClaim(
        claim_text="All privileged accounts must use multi-factor authentication.",
        subject="Privileged accounts",
        predicate="must use",
        object="multi-factor authentication",
        modality="MUST",
        claim_type="security",
        evidence_text_span="All privileged accounts must use multi-factor authentication.",
    )
    res = GroundingVerifier.verify_and_ground_claim(claim, source_text)
    assert res.is_valid
    assert res.start_offset == 0
    assert res.end_offset == 61
    assert len(res.evidence_hash) == 64
    assert res.verified_modality == "MUST"
    assert res.numeric_grounded


def test_grounding_verifier_numeric_grounding():
    source_text = "Standard enterprise customer refunds strictly adhere to the 30-day baseline."
    
    # Case 1: Grounded number (30 days exists in text)
    grounded_claim = ExtractedClaim(
        claim_text="Standard refunds adhere to 30 days.",
        subject="Standard refunds",
        predicate="adhere to",
        object="30 days",
        modality="MUST",
        numeric_value=30.0,
        numeric_unit="days",
        evidence_text_span="refunds strictly adhere to the 30-day baseline",
    )
    res1 = GroundingVerifier.verify_and_ground_claim(grounded_claim, source_text)
    assert res1.is_valid
    assert res1.numeric_grounded
    assert grounded_claim.numeric_value == 30.0

    # Case 2: Hallucinated number (90 days does NOT exist in text)
    hallucinated_claim = ExtractedClaim(
        claim_text="Standard refunds adhere to 90 days.",
        subject="Standard refunds",
        predicate="adhere to",
        object="90 days",
        modality="MUST",
        numeric_value=90.0,
        numeric_unit="days",
        evidence_text_span="refunds strictly adhere to the 30-day baseline",
    )
    res2 = GroundingVerifier.verify_and_ground_claim(hallucinated_claim, source_text)
    assert res2.is_valid
    assert not res2.numeric_grounded
    # Number should be sanitized/cleared
    assert hallucinated_claim.numeric_value is None


def test_grounding_verifier_rejects_hallucinated_evidence():
    source_text = "Employees are allowed 2 remote work days per week."
    hallucinated_claim = ExtractedClaim(
        claim_text="All employees receive unlimited annual bonuses.",
        subject="Employees",
        predicate="receive",
        object="unlimited bonuses",
        modality="CAN",
        evidence_text_span="Employees receive $100,000 yearly bonus unconditionally.",
    )
    res = GroundingVerifier.verify_and_ground_claim(hallucinated_claim, source_text)
    assert not res.is_valid
    assert "was not found in source section" in res.rejection_reason


def test_grounding_verifier_modality_correction():
    source_text = "Plaintext HTTP port 80 ingress is strictly barred in Production."
    claim = ExtractedClaim(
        claim_text="Plaintext HTTP is allowed in Production.",
        subject="Plaintext HTTP",
        predicate="is allowed in",
        object="Production",
        modality="CAN",
        evidence_text_span="Plaintext HTTP port 80 ingress is strictly barred in Production.",
    )
    res = GroundingVerifier.verify_and_ground_claim(claim, source_text)
    assert res.is_valid
    # Python deterministic check catches "barred" and corrects modality to CANNOT
    assert res.verified_modality == "CANNOT"
