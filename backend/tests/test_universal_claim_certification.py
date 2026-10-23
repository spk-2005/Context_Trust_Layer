"""
Universal Property-Based Regression Test Suite for Document-Agnostic Claim Certification.

Validates all 14 Universal Invariants across 5 distinct document domains:
1. Commercial Master Services Agreement (MSA)
2. Corporate Information Security and Acceptable Use Policy
3. Vendor Hardware & Cloud Services Invoice Terms
4. Executive Employment & Proprietary Information Agreement
5. Mutual Non-Disclosure Agreement (NDA)
"""

import json
from pathlib import Path
import pytest

from app.schemas.evidence import ImmutableEvidenceSpan
from app.schemas.universal_claim import (
    ClaimLifecycleState,
    ClaimType,
    ModalityType,
    ObjectEntity,
    PredicateAction,
    SubjectEntity,
    UniversalClaim,
)
from app.services.compound_splitter import CompoundClaimSplitter
from app.services.declarative_repair_engine import DeclarativeRepairEngine
from app.services.deduplication_cascade import SemanticDeduplicationCascade
from app.services.dynamic_modality_extractor import DynamicModalityExtractor
from app.services.evidence_locator_service import EvidenceLocatorService
from app.services.risk_policy_service import AgentAccessDecision, RiskPolicyConfig, RiskPolicyEvaluator
from app.services.role_direction_validator import RoleDirectionValidator
from app.services.universal_gate_evaluator import UniversalGateEvaluator
from app.taxonomy.registry import PredicateRegistryService


FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures" / "synthetic_corpus"


class TestUniversalClaimCertificationProperties:
    """Property-based verification of the 14 Universal Pipeline Invariants."""

    # -------------------------------------------------------------------------
    # Invariant 1: No canonical claim has missing evidence
    # -------------------------------------------------------------------------
    def test_invariant_1_no_canonical_claim_has_missing_evidence(self):
        res = UniversalGateEvaluator.evaluate(
            claim_text="Customer must pay all undisputed invoices within thirty calendar days of invoice date.",
            subject="Customer",
            predicate="must_pay_within_30_days",
            claim_type="RULE",
            evidence=None,  # Missing evidence
        )
        assert res.gates["evidence_exists"] is False
        assert res.gates["evidence_located"] is False
        assert res.is_canonical is False
        assert res.certification_tier == "REJECTED"
        assert any("Missing ImmutableEvidenceSpan" in r for r in res.rejection_reasons)

    # -------------------------------------------------------------------------
    # Invariant 2: No canonical claim_text contains a predicate slug
    # -------------------------------------------------------------------------
    def test_invariant_2_no_canonical_claim_text_contains_predicate_slug(self):
        content = "Users must not reverse engineer proprietary software."
        ev = ImmutableEvidenceSpan.from_content(
            verbatim_quote=content,
            clause_text=content,
            content=content,
        )
        res = UniversalGateEvaluator.evaluate(
            claim_text="Users must_not_reverse_engineer proprietary software.",  # Slug injected
            subject="Users",
            predicate="must_not_reverse_engineer",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
        )
        assert res.gates["text_integrity"] is False
        assert res.is_canonical is False
        assert any("Injected predicate identifier" in r for r in res.rejection_reasons)

    # -------------------------------------------------------------------------
    # Invariant 3: No canonical RULE claim lacks an operative modal
    # -------------------------------------------------------------------------
    def test_invariant_3_no_canonical_rule_claim_lacks_operative_modal(self):
        content = "Users reverse engineer proprietary software."
        ev = ImmutableEvidenceSpan.from_content(
            verbatim_quote=content,
            clause_text=content,
            content=content,
        )
        res = UniversalGateEvaluator.evaluate(
            claim_text="Users reverse engineer proprietary software.",  # Headless/no modal
            subject="Users",
            predicate="must_not_reverse_engineer",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
        )
        assert res.gates["text_integrity"] is False
        assert res.is_canonical is False
        assert any("missing an operative modal" in r for r in res.rejection_reasons)

    # -------------------------------------------------------------------------
    # Invariant 4: No MUST_NOT claim has lost negation
    # -------------------------------------------------------------------------
    def test_invariant_4_no_must_not_claim_has_lost_negation(self):
        content = "Employee may reverse engineer proprietary software."
        ev = ImmutableEvidenceSpan.from_content(
            verbatim_quote=content,
            clause_text=content,
            content=content,
        )
        res = UniversalGateEvaluator.evaluate(
            claim_text="Employee may reverse engineer proprietary software.",  # Missing negation
            subject="Employee",
            predicate="must_not_reverse_engineer",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
        )
        assert res.gates["text_integrity"] is False
        assert res.is_canonical is False
        assert any("contradicts affirmative claim text" in r for r in res.rejection_reasons)

    # -------------------------------------------------------------------------
    # Invariant 5: No canonical claim is compound
    # -------------------------------------------------------------------------
    def test_invariant_5_no_canonical_claim_is_compound(self):
        content = "Customer may transfer licenses to (1) an Affiliate or (2) a third party upon written notice."
        ev = ImmutableEvidenceSpan.from_content(
            verbatim_quote=content,
            clause_text=content,
            content=content,
        )
        res = UniversalGateEvaluator.evaluate(
            claim_text=content,
            subject="Customer",
            predicate="may_transfer_perpetual_license",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
        )
        assert res.gates["atomicity_valid"] is False
        assert res.is_canonical is False
        assert res.certification_tier == "QUARANTINED"

    # -------------------------------------------------------------------------
    # Invariant 6: No canonical claim is a duplicate
    # -------------------------------------------------------------------------
    def test_invariant_6_no_canonical_claim_is_duplicate(self):
        cascade = SemanticDeduplicationCascade()
        content = "Customer must pay all undisputed invoices within thirty calendar days of invoice date."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        
        c1 = UniversalClaim(
            claim_id="clm_orig_1",
            claim_text=content,
            evidence=ev,
            subject=SubjectEntity(raw_text="Customer", canonical_entity="Customer"),
            predicate=PredicateAction(raw_text="must pay", normalized_action="must_pay_within_30_days"),
        )
        c2 = UniversalClaim(
            claim_id="clm_dup_2",
            claim_text=content,
            evidence=ev,
            subject=SubjectEntity(raw_text="Customer", canonical_entity="Customer"),
            predicate=PredicateAction(raw_text="must pay", normalized_action="must_pay_within_30_days"),
        )

        r1 = cascade.collapse_if_duplicate(c1)
        assert r1.is_canonical is False  # initially candidate
        r2 = cascade.collapse_if_duplicate(c2)
        assert r2.lifecycle_state == ClaimLifecycleState.DUPLICATE
        assert r2.duplicate_of == "clm_orig_1"

    # -------------------------------------------------------------------------
    # Invariant 7: No canonical claim is a definition/reference/description
    # -------------------------------------------------------------------------
    def test_invariant_7_no_canonical_claim_is_non_rule(self):
        content = "More details about cancellation can be found in the product terms."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        res = UniversalGateEvaluator.evaluate(
            claim_text=content,
            subject="More details",
            predicate="refer_to",
            claim_type="REFERENCE",
            evidence=ev,
            source_content=content,
        )
        assert res.gates["claim_type_allowed"] is False
        assert res.is_canonical is False
        assert res.certification_tier == "NON_RULE"

    # -------------------------------------------------------------------------
    # Invariant 8: No canonical claim has an unresolved pronoun
    # -------------------------------------------------------------------------
    def test_invariant_8_no_canonical_claim_has_unresolved_pronoun(self):
        content = "Service provider remains responsible for their performance."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        res = UniversalGateEvaluator.evaluate(
            claim_text=content,
            subject="Service provider",
            predicate="responsible_for_own_taxes",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
            clause_text=content,
        )
        assert res.gates["counterparty_resolved"] is False
        assert res.is_canonical is False
        assert any("Ungrounded pronoun 'their'" in r for r in res.rejection_reasons)

    # -------------------------------------------------------------------------
    # Invariant 9: Role direction conflict routes to REVIEW_REQUIRED
    # -------------------------------------------------------------------------
    def test_invariant_9_role_direction_conflict_routes_to_review(self):
        content = "During any period of material breach, Vendor may suspend services for security risks or material breach."
        quote = "Vendor may suspend services for security risks or material breach."
        ev = ImmutableEvidenceSpan.from_content(
            verbatim_quote=quote,
            clause_text=content,
            content=content,
        )
        res = UniversalGateEvaluator.evaluate(
            claim_text=quote,
            subject="Customer",
            predicate="may_suspend_for_security_or_breach",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
            clause_text=content,
        )
        assert res.gates["counterparty_resolved"] is False
        assert res.is_canonical is False
        assert res.certification_tier == "REVIEW_REQUIRED"
        assert any("Role direction requires review" in r for r in res.rejection_reasons)

    # -------------------------------------------------------------------------
    # Invariant 10: Every canonical claim passes all 10 gates
    # -------------------------------------------------------------------------
    def test_invariant_10_every_canonical_claim_passes_all_10_gates(self):
        content = "Customer must pay all undisputed invoices within thirty calendar days of invoice date."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        res = UniversalGateEvaluator.evaluate(
            claim_text=content,
            subject="Customer",
            predicate="must_pay_within_30_days",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
        )
        assert res.all_gates_passed is True
        assert res.is_canonical is True
        assert res.certification_tier == "AUTOMATED_CERTIFIED"
        for gate_name, val in res.gates.items():
            if gate_name != "human_approved_if_required":
                assert val is True, f"Gate {gate_name} unexpectedly failed"

    # -------------------------------------------------------------------------
    # Invariant 11: Every repair is rerunnable and produces the same result
    # -------------------------------------------------------------------------
    def test_invariant_11_repairs_are_rerunnable_and_deterministic(self):
        engine = DeclarativeRepairEngine()
        content = "(ii) Customer must pay all undisputed invoices within thirty calendar days."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        claim = UniversalClaim(
            claim_id="clm_rep_1",
            claim_text=content,
            evidence=ev,
            subject=SubjectEntity(raw_text="Customer", canonical_entity="Customer"),
            predicate=PredicateAction(raw_text="must pay", normalized_action="must_pay_within_30_days"),
        )
        rep1, audits1 = engine.evaluate_and_repair(claim)
        assert rep1.claim_text == "Customer must pay all undisputed invoices within thirty calendar days."
        assert len(audits1) >= 1

        # Rerunning on repaired claim produces idempotent outcome
        rep2, audits2 = engine.evaluate_and_repair(rep1)
        assert rep2.claim_text == rep1.claim_text
        assert len(audits2) == 0

    # -------------------------------------------------------------------------
    # Invariant 12: Split children link to parent and shared evidence
    # -------------------------------------------------------------------------
    def test_invariant_12_split_children_link_to_parent_and_evidence(self):
        content = "Customer may sublicense its rights in deliverables to Affiliates, but Affiliates may not sublicense."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        parent = UniversalClaim(
            claim_id="clm_parent_100",
            claim_text=content,
            evidence=ev,
            subject=SubjectEntity(raw_text="Customer", canonical_entity="Customer"),
            predicate=PredicateAction(raw_text="may sublicense", normalized_action="may_sublicense"),
        )
        children = CompoundClaimSplitter.split(parent)
        assert len(children) == 2
        for i, child in enumerate(children, start=1):
            assert child.parent_claim_id == "clm_parent_100"
            assert child.child_index == i
            assert child.evidence.verbatim_quote == parent.evidence.verbatim_quote

    # -------------------------------------------------------------------------
    # Invariant 13: Every rejected claim has machine-readable reasons
    # -------------------------------------------------------------------------
    def test_invariant_13_every_rejected_claim_has_machine_readable_reasons(self):
        content = "100 Technology Parkway, Suite 400, Austin, TX 78759 USA."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        res = UniversalGateEvaluator.evaluate(
            claim_text=content,
            subject="100 Technology Parkway",
            predicate="locate",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
        )
        assert res.certification_tier == "REJECTED"
        assert len(res.rejection_reasons) > 0
        assert any(isinstance(r, str) and len(r) > 5 for r in res.rejection_reasons)

    # -------------------------------------------------------------------------
    # Invariant 14: Every review claim has routing reasons
    # -------------------------------------------------------------------------
    def test_invariant_14_every_review_claim_has_routing_reasons(self):
        content = "Termination without cause will not affect accrued obligations."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        res = UniversalGateEvaluator.evaluate(
            claim_text=content,
            subject="Termination without cause",  # Grammatical syntax fragment
            predicate="affect",
            claim_type="RULE",
            evidence=ev,
            source_content=content,
        )
        assert res.certification_tier == "REVIEW_REQUIRED"
        assert len(res.rejection_reasons) > 0
        assert any("syntax fragment" in r for r in res.rejection_reasons)


class TestCrossDocumentSyntheticCorpus:
    """End-to-end evaluation against 5 synthetic cross-document fixtures."""

    @pytest.mark.parametrize(
        "fixture_filename",
        [
            "contract_fixture.json",
            "policy_fixture.json",
            "invoice_fixture.json",
            "employment_fixture.json",
            "nda_fixture.json",
        ],
    )
    def test_synthetic_document_fixture_end_to_end(self, fixture_filename: str):
        path = FIXTURES_DIR / fixture_filename
        assert path.exists(), f"Fixture file not found: {path}"

        with open(path, "r", encoding="utf-8") as f:
            doc_data = json.load(f)

        content = doc_data["content"]
        for item in doc_data["claims"]:
            cid = item["claim_id"]
            quote = item["verbatim_quote"]
            clause = item["clause_text"]
            expected = item["expected_tier"]

            ev = ImmutableEvidenceSpan.from_content(
                verbatim_quote=quote,
                clause_text=clause,
                content=content,
                document_uri=f"file://{doc_data['document_id']}",
            )

            res = UniversalGateEvaluator.evaluate(
                claim_text=quote,
                subject=item["subject"],
                predicate=item["predicate"],
                object_text=item.get("object"),
                claim_type=item["claim_type"],
                evidence=ev,
                source_content=content,
                clause_text=clause,
            )

            assert res.certification_tier == expected, (
                f"Claim {cid} in {fixture_filename} expected {expected}, got {res.certification_tier}. "
                f"Reasons: {res.rejection_reasons}"
            )


class TestRiskPolicyAndAgentGate:
    """Verifies that retrieval gating enforces risk policy."""

    def test_risk_gate_blocks_quarantined_and_rejected(self):
        content = "Customer may transfer licenses to (1) an Affiliate or (2) a third party."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        claim = UniversalClaim(
            claim_id="clm_risk_1",
            claim_text=content,
            evidence=ev,
            subject=SubjectEntity(raw_text="Customer", canonical_entity="Customer"),
            predicate=PredicateAction(raw_text="may transfer", normalized_action="may_transfer_perpetual_license"),
            lifecycle_state=ClaimLifecycleState.QUARANTINED,
            certification_tier="QUARANTINED",
        )
        decision, reason = RiskPolicyEvaluator.evaluate_access(claim, proposed_action="answer_question")
        assert decision == AgentAccessDecision.BLOCKED

    def test_risk_gate_allows_citation_for_non_rules(self):
        content = "Confidential Information refers to technical data."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        claim = UniversalClaim(
            claim_id="clm_risk_2",
            claim_text=content,
            evidence=ev,
            subject=SubjectEntity(raw_text="Confidential Information", canonical_entity="Confidential Information"),
            predicate=PredicateAction(raw_text="refers to", normalized_action="refer_to"),
            claim_type=ClaimType.DEFINITION,
            lifecycle_state=ClaimLifecycleState.NON_RULE,
            certification_tier="NON_RULE",
        )
        decision, reason = RiskPolicyEvaluator.evaluate_access(claim, proposed_action="read_context")
        assert decision == AgentAccessDecision.CITATION_ONLY

    def test_risk_gate_requires_human_confirmation_for_high_risk_actions(self):
        content = "Either party may terminate this Agreement without cause upon 60 days prior written notice."
        ev = ImmutableEvidenceSpan.from_content(content, content, content)
        claim = UniversalClaim(
            claim_id="clm_risk_3",
            claim_text=content,
            evidence=ev,
            subject=SubjectEntity(raw_text="Either party", canonical_entity="Either party"),
            predicate=PredicateAction(raw_text="may terminate", normalized_action="may_terminate_without_cause"),
            claim_type=ClaimType.RULE,
            lifecycle_state=ClaimLifecycleState.AUTOMATED_CERTIFIED,
            certification_tier="AUTOMATED_CERTIFIED",
            is_canonical=True,
        )
        policy = RiskPolicyConfig(
            high_risk_predicates=["may_terminate_without_cause"],
            human_confirmation_required_for_high_risk=True,
        )
        # Autonomous question answering is allowed
        dec_read, _ = RiskPolicyEvaluator.evaluate_access(claim, proposed_action="cite_clause", policy=policy)
        assert dec_read == AgentAccessDecision.FULL_AUTONOMOUS

        # Write/execution action requires confirmation
        dec_act, _ = RiskPolicyEvaluator.evaluate_access(claim, proposed_action="terminate_contract_action", policy=policy)
        assert dec_act == AgentAccessDecision.HUMAN_CONFIRMATION_REQUIRED
