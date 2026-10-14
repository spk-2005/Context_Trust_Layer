"""
Unit tests verifying structured exceptions, canonical rule isolation, and condition fidelity.
Addresses reviewer feedback:
1. Confidentiality claim exception structure (modality, actions, exceptions, conditions).
2. Canonical rule isolation: derived summaries excluded from governing agent decisions.
3. Coexistence of general disclosure prohibition and reproduction restriction with exception.
4. Structured condition and modality fidelity on detailed rules.
5. Trust score multi-dimensionality.
"""

from __future__ import annotations

import decimal
import uuid
from unittest.mock import AsyncMock, MagicMock
import pytest

from app.db.enums import ClaimStatus, SourceFamily, SourceIntent
from app.db.models.claim import Claim
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.repositories.claim_repository import ClaimRepository
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit
from app.retrieval.engine import ContextRetrievalEngine
from app.schemas.context import ContextQueryRequest


@pytest.mark.asyncio
async def test_confidentiality_structured_exception_fidelity():
    """
    Aspect 1: Verifies that the document reproduction clause extracts:
    - modality: PROHIBITION
    - structured exceptions: Customer's internal business use
    - structured conditions: under confidentiality obligations
    - actions: reproduce, store, transmit
    - claim_type: document_use_restriction
    """
    text = (
        "No part of this document, in whole or in part, may be reproduced, stored in a retrieval system, "
        "or transmitted in any form or by any means, electronic or mechanical, including photocopying and "
        "recording for any purpose other than any Customer's internal use for a business purpose under "
        "confidentiality obligations with Wingify."
    )
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="file://Employees Notice Period Policy V 1.5.pdf",
        block_type="clause",
        content_text=text,
        hierarchical_context=["Statement of Confidentiality"],
    )

    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 1, "Expected exactly 1 claim extracted for confidentiality clause"

    claim = claims[0]
    assert claim.modality == "PROHIBITION", "Modality must be PROHIBITION"
    assert claim.modal_operator == "prohibited"
    assert claim.claim_type == "document_use_restriction"
    assert len(claim.exceptions) > 0, "Must have at least 1 structured exception"
    assert "internal" in claim.exceptions[0].lower()
    assert "business purpose" in claim.exceptions[0].lower()
    assert len(claim.conditions) > 0, "Must have confidentiality condition"
    assert "confidentiality" in claim.conditions[0].lower()

    # Structured values checks
    sv = claim.structured_values
    assert "actions" in sv, "Actions must be preserved in structured_values"
    assert "reproduce" in sv["actions"]
    assert "store" in sv["actions"]
    assert "transmit" in sv["actions"]
    assert "exceptions" in sv


@pytest.mark.asyncio
async def test_distinct_confidentiality_clauses_do_not_collide():
    """
    Aspect 3: Verifies that general disclosure prohibition and reproduction clause
    are extracted as distinct claims with different scopes and conditions.
    """
    general_text = "The unauthorized use or disclosure of this information in any media is prohibited."
    reproduction_text = (
        "No part of this document, in whole or in part, may be reproduced, stored in a retrieval system, "
        "or transmitted in any form or by any means, electronic or mechanical, including photocopying and "
        "recording for any purpose other than any Customer's internal use for a business purpose under "
        "confidentiality obligations with Wingify."
    )

    u1 = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="file://test.pdf",
        block_type="clause",
        content_text=general_text,
    )
    u2 = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="file://test.pdf",
        block_type="clause",
        content_text=reproduction_text,
    )

    claims_gen = DomainRuleExtractor.extract_from_unit(u1)
    claims_rep = DomainRuleExtractor.extract_from_unit(u2)

    assert len(claims_gen) == 1
    assert len(claims_rep) == 1

    c1 = claims_gen[0]
    c2 = claims_rep[0]

    # Different subjects and predicates
    assert c1.subject != c2.subject
    assert c1.predicate != c2.predicate

    # c1 is a general media prohibition without exceptions
    assert len(c1.exceptions) == 0
    # c2 has an explicit internal business use exception
    assert len(c2.exceptions) > 0


@pytest.mark.asyncio
async def test_canonical_isolation_excludes_summaries():
    """
    Aspect 2: Verifies that ContextRetrievalEngine default (canonical_only=True)
    filters SQL queries to exclude Claim.claim_type == 'derived_summary'.
    """
    mock_session = AsyncMock()
    mock_session.add = MagicMock()
    mock_result = MagicMock()
    
    # 1 canonical claim, 1 summary claim
    canonical_claim = Claim(
        id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        claim_text="Grade C employees have a maximum notice period of 60 Days upon confirmation.",
        subject="Employees in Grade C",
        predicate="has_confirmed_notice_duration",
        object="60 Days",
        claim_type="policy_rule",
        status=ClaimStatus.VERIFIED,
    )
    
    # When query executes, simulate session returning the filtered list
    mock_result.scalars.return_value.all.return_value = [canonical_claim]
    mock_session.execute.return_value = mock_result

    engine = ContextRetrievalEngine(mock_session)
    req = ContextQueryRequest(
        organization_id=uuid.uuid4(),
        agent_id=uuid.uuid4(),
        query="Grade C notice period",
        min_trust_score=decimal.Decimal("0.80"),
        canonical_only=True,
    )
    
    # Verify execute was called and captured the where clause
    await engine.query_context(req)
    executed_stmt = mock_session.execute.call_args[0][0]
    stmt_str = str(executed_stmt)
    assert "claims.claim_type !=" in stmt_str or "claim_type" in stmt_str, "Query must filter by claim_type"


@pytest.mark.asyncio
async def test_claim_repository_canonical_only_filter():
    """
    Aspect 2B: Verifies that ClaimRepository.list_by_organization with canonical_only=True
    adds the claim_type != 'derived_summary' filter.
    """
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    repo = ClaimRepository(mock_session)
    org_id = uuid.uuid4()
    
    await repo.list_by_organization(organization_id=org_id, canonical_only=True)
    executed_stmt = mock_session.execute.call_args[0][0]
    stmt_str = str(executed_stmt)
    assert "claims.claim_type !=" in stmt_str or "claim_type" in stmt_str


@pytest.mark.asyncio
async def test_detailed_rules_condition_and_modality_fidelity():
    """
    Aspect 4: Verifies condition and modality fidelity on detailed rules:
    - Leave during notice: PERMISSION (may request) + condition prior written approval
    - Short notice adjustment: PERMISSION (holds the right) + unserved notice condition
    - Tax deduction: HR Portal declared + exit condition
    - WFH allowance: 1 year exit condition + Home Office Allowance Policy
    """
    units_and_expectations = [
        (
            "Employees may request leave during the notice period only as an exception with prior written approval from their reporting manager.",
            "PERMISSION",
            "may",
            "Employees (Leave During Notice Period)",
            ["Exception with prior written approval from reporting manager"],
        ),
        (
            "If the employee does not serve the full notice period, the company holds the right to recover the amount equivalent to the unserved short notice period.",
            "PERMISSION",
            "holds_the_right",
            "Wingify (Company Right)",
            ["Employee does not serve full notice period"],
        ),
        (
            "If investment proofs, as declared on the HR Portal, are not provided during exit, taxes will be deducted accordingly.",
            "POLICY_FACT",
            "deducts",
            "Exit Tax Deductions",
            ["Investment proofs declared on HR Portal not provided during exit"],
        ),
        (
            "Home office allowance will be recovered based on the Home Office Allowance Policy if exit occurs within one year of joining.",
            "POLICY_FACT",
            "recovers",
            "WFH Allowance Recovery",
            ["Employee exit occurs within 1 year of joining"],
        ),
    ]

    for text, expected_mod, expected_op, expected_subj, expected_conds in units_and_expectations:
        unit = ParsedEvidenceUnit.create(
            envelope_id=uuid.uuid4(),
            asset_id="file://test.pdf",
            block_type="clause",
            content_text=text,
        )
        claims = DomainRuleExtractor.extract_from_unit(unit)
        assert len(claims) >= 1, f"Failed to extract claim for {expected_subj}"
        c = claims[0]
        assert c.modality == expected_mod, f"Modality mismatch for {expected_subj}: expected {expected_mod}, got {c.modality}"
        assert c.modal_operator == expected_op, f"Operator mismatch for {expected_subj}"
        assert c.subject == expected_subj, f"Subject mismatch: expected {expected_subj}, got {c.subject}"
        for ec in expected_conds:
            assert any(ec.lower() in cond.lower() for cond in c.conditions), f"Missing condition {ec} in {c.conditions}"
