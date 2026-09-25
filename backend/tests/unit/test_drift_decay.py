import uuid
import pytest

from app.schemas.drift import ClaimRemediateRequest
from app.services.drift_decay_service import (
    _calculate_decay,
    analyze_context_drift,
    remediate_claim_decay,
)


def test_calculate_decay_tiers():
    trust_30, dec_30, cat_30, _ = _calculate_decay(10, 0.90)
    assert cat_30 == "ACTIVE_FRESH"
    assert dec_30 == 0.0
    assert trust_30 == 0.90

    trust_60, dec_60, cat_60, _ = _calculate_decay(60, 0.90)
    assert cat_60 == "AGING_WARNING"
    assert dec_60 > 0.0

    trust_120, dec_120, cat_120, _ = _calculate_decay(120, 0.90)
    assert cat_120 == "STALE_TEMPORAL"
    assert dec_120 == 25.0

    trust_200, dec_200, cat_200, _ = _calculate_decay(200, 0.90)
    assert cat_200 == "SEVERELY_DECAYED"
    assert dec_200 == 50.0


@pytest.mark.asyncio
async def test_analyze_context_drift():
    org_id = uuid.uuid4()
    resp = await analyze_context_drift(org_id, session=None)
    assert resp.total_claims > 0
    assert resp.average_age_days >= 0
    assert 0.0 <= resp.freshness_index_pct <= 100.0
    assert len(resp.decay_radar) == 4
    assert len(resp.decayed_claims) > 0


@pytest.mark.asyncio
async def test_remediate_claim_re_attest_and_retire():
    org_id = uuid.uuid4()
    # Initial analysis to ensure seeded claims
    analysis = await analyze_context_drift(org_id, session=None)
    target_claim = analysis.decayed_claims[0]

    # 1. Test Re-Attest
    req_attest = ClaimRemediateRequest(
        claim_id=target_claim.claim_id,
        action="RE_ATTEST",
        notes="Verified against newly signed corporate handbook",
    )
    res_attest = await remediate_claim_decay(req_attest, session=None)
    assert res_attest.action_taken == "RE_ATTEST"
    assert res_attest.new_status == "ACTIVE"
    assert res_attest.new_trust_score >= 0.90

    # 2. Test Retire
    req_retire = ClaimRemediateRequest(
        claim_id=target_claim.claim_id,
        action="RETIRE",
        notes="Obsolete policy rule deprecated",
    )
    res_retire = await remediate_claim_decay(req_retire, session=None)
    assert res_retire.action_taken == "RETIRE"
    assert res_retire.new_status == "SUPERSEDED"
    assert res_retire.new_trust_score == 0.0
