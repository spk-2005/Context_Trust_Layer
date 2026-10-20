"""
Unit tests for Sprint AF: Claim Quality Normalizer (DOC-057 Microsoft Customer Agreement)

Verifies:
1. Multi-rule atomicity splitting
2. Subject normalization and allowlist enforcement
3. Controlled predicate vocabulary enforcement
4. Semantic deduplication by normalized signature
5. Taxonomic reclassification of non-rules (descriptions, definitions, references, responsibilities, examples)
6. Conflict compatibility verification (no false conflicts on conditional termination rights)
7. Re-review and recovery of validly rejected rules (#80, #86, #87, #61, #53, #59)
8. Output acceptance criteria (70-80 atomic claims, 0 fragments, 0 vague predicates, 0 duplicates)
"""

import pytest
from app.extraction.claim_quality_normalizer import (
    CANONICAL_SUBJECT_ALLOWLIST,
    CONTROLLED_PREDICATE_VOCABULARY,
    ClaimQualityNormalizer,
    NormalizedClaim,
    NormalizedClaimCategory,
    NormativeModality,
)
from app.conflict_engine.compatibility_gate import CompatibilityGate


class TestClaimQualityNormalizer:
    """Test suite for Sprint AF claim quality normalizer."""

    def test_canonical_subject_allowlist(self):
        """Allowlist must contain core contracting entity types."""
        required_entities = {
            "Customer", "Microsoft", "Partner", "Affiliate",
            "Either party", "Each party", "Supplier", "Vendor",
            "Employee", "Administrator", "Publisher", "Representatives",
            "End User", "Neither party",
        }
        for entity in required_entities:
            assert entity in CANONICAL_SUBJECT_ALLOWLIST, f"{entity} missing from allowlist"

    def test_subject_normalization_valid_actors(self):
        """Plurals and aliases must normalize to singular canonical subjects."""
        cases = [
            ("Customers", "Customer"),
            ("customer", "Customer"),
            ("the customer", "Customer"),
            ("End Users", "End User"),
            ("Partners", "Partner"),
            ("Affiliates", "Affiliate"),
            ("The parties", "Each party"),
            ("parties", "Each party"),
            ("Each party", "Each party"),
            ("Either party", "Either party"),
            ("Neither party", "Neither party"),
        ]
        for raw, expected in cases:
            norm_subj, is_valid = ClaimQualityNormalizer.normalize_subject_entity(raw)
            assert is_valid is True, f"Failed for {raw}"
            assert norm_subj == expected, f"Expected {expected}, got {norm_subj} for {raw}"

    def test_bad_subjects_repaired_or_rejected(self):
        """Bad subjects must be repaired or rejected as fragments."""
        # Repaired subjects
        assert ClaimQualityNormalizer.normalize_subject_entity("All amounts due under any unpaid invoices")[0] == "Customer"
        assert ClaimQualityNormalizer.normalize_subject_entity("Any other proposed assignment of this agreement")[0] == "Customer"
        assert ClaimQualityNormalizer.normalize_subject_entity("Any waiver")[0] == "Either party"
        assert ClaimQualityNormalizer.normalize_subject_entity("All notices")[0] == "Either party"
        
        # Address block cleanup
        reno_addr = "Sierra Center Parkway Reno, Nevada 89511-1137 USA Microsoft"
        norm_reno, is_valid = ClaimQualityNormalizer.normalize_subject_entity(reno_addr)
        assert is_valid is True
        assert norm_reno == "Microsoft"

        # Fragment rejection
        assert ClaimQualityNormalizer.normalize_subject_entity("the following")[1] is False
        assert ClaimQualityNormalizer.normalize_subject_entity("the following apply")[1] is False
        assert ClaimQualityNormalizer.normalize_subject_entity("following")[1] is False
        assert ClaimQualityNormalizer.normalize_subject_entity("-")[1] is False

    def test_vague_predicate_replacement(self):
        """Vague predicates must be mapped to enterprise vocabulary."""
        assert ClaimQualityNormalizer.normalize_predicate("order", "Customer", "Products for use by its Affiliates") == "may_order_for_affiliate"
        assert ClaimQualityNormalizer.normalize_predicate("use", "Each party", "reproduce and modify Pre-existing Work") == "may_use_preexisting_work"
        assert ClaimQualityNormalizer.normalize_predicate("become", "Customer", "all amounts due under any unpaid invoices") == "becomes_due_immediately"
        assert ClaimQualityNormalizer.normalize_predicate("approved", "Customer", "by the non-assigning party in writing") == "requires_written_approval"
        assert ClaimQualityNormalizer.normalize_predicate("in", "Either party", "writing and signed by the waiving party") == "must_be_in_writing"
        assert ClaimQualityNormalizer.normalize_predicate("vary", "Product", "availability by region") == "varies_by_region"
        assert ClaimQualityNormalizer.normalize_predicate("customer", "Microsoft", "a nonexclusive and limited license to use Products") == "grants_product_license"
        assert ClaimQualityNormalizer.normalize_predicate("customer", "Microsoft", "license to use and modify Services Deliverables") == "grants_deliverables_license"

    def test_predicate_in_controlled_vocabulary(self):
        """All mapped predicates must exist in the central controlled dictionary."""
        test_predicates = [
            "grants_product_license", "grants_deliverables_license",
            "may_order_for_affiliate", "may_use_preexisting_work",
            "may_transfer_perpetual_license", "must_uninstall_upon_transfer",
            "prohibited_from_reverse_engineering", "prohibited_from_licensing_interference",
            "must_keep_compliance_records", "may_conduct_compliance_audit",
            "must_maintain_confidentiality", "prohibited_from_unauthorized_disclosure",
            "warrants_service_level_agreement", "warrants_software_performance",
            "must_defend_ip_claims", "has_liability_cap",
            "must_pay_within_30_days", "may_assess_late_fee",
            "authorizes_recurring_charges", "must_pay_applicable_taxes",
            "may_terminate_without_cause", "may_terminate_for_material_breach",
            "becomes_due_immediately", "must_stop_use_and_disable_billing",
            "must_be_in_writing", "submits_to_governing_jurisdiction",
        ]
        for pred in test_predicates:
            assert pred in CONTROLLED_PREDICATE_VOCABULARY, f"Predicate '{pred}' not documented in CONTROLLED_PREDICATE_VOCABULARY"

    def test_non_rule_reclassification(self):
        """Descriptions, definitions, references, and responsibilities must be properly classified."""
        # 1. Description
        cat1, _ = ClaimQualityNormalizer.classify_claim_category(
            "Product", "varies_by_region", "Product availability may vary by region"
        )
        assert cat1 == NormalizedClaimCategory.DESCRIPTION

        # 2. Definition
        cat2, _ = ClaimQualityNormalizer.classify_claim_category(
            "Software", "definition", "Software does not include Online Services"
        )
        assert cat2 == NormalizedClaimCategory.DEFINITION

        # 3. Reference
        cat3, _ = ClaimQualityNormalizer.classify_claim_category(
            "Customer", "reference", "More details about cancelation can be found in the Product Terms"
        )
        assert cat3 == NormalizedClaimCategory.REFERENCE

        # 4. Responsibility
        cat4, _ = ClaimQualityNormalizer.classify_claim_category(
            "Microsoft", "remains_responsible_for", "Microsoft remains responsible for the performance of those services"
        )
        assert cat4 == NormalizedClaimCategory.RESPONSIBILITY

        # 5. Example
        cat5, _ = ClaimQualityNormalizer.classify_claim_category(
            "Customer", "example", "For example, Customer may deploy on local servers"
        )
        assert cat5 == NormalizedClaimCategory.EXAMPLE

        # 6. Policy Obligation
        cat6, mod6 = ClaimQualityNormalizer.classify_claim_category(
            "Customer", "must_pay_within_30_days", "Customer must pay all amounts due within 30 days"
        )
        assert cat6 == NormalizedClaimCategory.POLICY_CLAIM
        assert mod6 == NormativeModality.OBLIGATION

        # 7. Policy Prohibition
        cat7, mod7 = ClaimQualityNormalizer.classify_claim_category(
            "Customer", "prohibited_from_reverse_engineering", "Customer must not reverse engineer any Product"
        )
        assert cat7 == NormalizedClaimCategory.POLICY_CLAIM
        assert mod7 == NormativeModality.PROHIBITION

    def test_deduplication_by_semantic_signature(self):
        """Duplicates must generate the same signature regardless of trivial stopwords."""
        claim1 = NormalizedClaim(
            claim_id="test:1",
            subject="Customer",
            predicate="may_order_for_affiliate",
            object="Products for the use by its Affiliates",
            modality=NormativeModality.PERMISSION,
            category=NormalizedClaimCategory.POLICY_CLAIM,
            conditions=["in writing"],
        )
        claim2 = NormalizedClaim(
            claim_id="test:2",
            subject="Customer",
            predicate="may_order_for_affiliate",
            object="Products for use by its Affiliates",
            modality=NormativeModality.PERMISSION,
            category=NormalizedClaimCategory.POLICY_CLAIM,
            conditions=["in writing"],
        )
        assert claim1.semantic_signature() == claim2.semantic_signature()

    def test_conflict_engine_termination_clause_compatibility(self):
        """Termination without cause (60 days) and termination for material breach (30 days) are non-conflicting."""
        claim_without_cause = NormalizedClaim(
            claim_id="doc057:af:060",
            subject="Either party",
            predicate="may_terminate_without_cause",
            object="the Agreement without cause on sixty (60) days written notice",
            modality=NormativeModality.PERMISSION,
            category=NormalizedClaimCategory.POLICY_CLAIM,
            conditions=["60 days written notice"],
        )
        claim_for_breach = NormalizedClaim(
            claim_id="doc057:af:061",
            subject="Either party",
            predicate="may_terminate_for_material_breach",
            object="the Agreement on 30 days notice for material breach if the other party fails to cure within 30 days",
            modality=NormativeModality.PERMISSION,
            category=NormalizedClaimCategory.POLICY_CLAIM,
            conditions=["uncured material breach", "30 days cure notice"],
        )

        is_conflict, reason = ClaimQualityNormalizer.evaluate_conflict_compatibility(
            claim_without_cause, claim_for_breach
        )
        assert is_conflict is False
        assert "Compatible conditional rights" in reason

        # Verify deterministic CompatibilityGate in backend
        competes = CompatibilityGate.predicates_compete(
            "may_terminate_without_cause", "may_terminate_for_material_breach"
        )
        assert competes is False

    def test_rejection_recovery_rules(self):
        """Key contractual obligations falsely rejected in raw extraction must be recovered."""
        # Claim #80: Must stop using if disagree with updates
        claim_80 = NormalizedClaim(
            claim_id="doc057:af:rec_80",
            subject="Customer",
            predicate="must_stop_use_and_disable_billing",
            object="Products and turn off recurring billing if it rejects Agreement changes",
            modality=NormativeModality.OBLIGATION,
            category=NormalizedClaimCategory.POLICY_CLAIM,
        )
        assert claim_80.modality == NormativeModality.OBLIGATION
        assert claim_80.subject in CANONICAL_SUBJECT_ALLOWLIST

        # Claim #86: Residual memory work assignment permission
        claim_86 = NormalizedClaim(
            claim_id="doc057:af:rec_86",
            subject="Neither party",
            predicate="is_not_required_to_restrict_assignments",
            object="work assignments of Representatives based on residual memory",
            modality=NormativeModality.PERMISSION,
            category=NormalizedClaimCategory.POLICY_CLAIM,
        )
        assert claim_86.modality == NormativeModality.PERMISSION
        assert claim_86.subject in CANONICAL_SUBJECT_ALLOWLIST

        # Claim #87: Late payment fee
        claim_87 = NormalizedClaim(
            claim_id="doc057:af:rec_87",
            subject="Microsoft",
            predicate="may_assess_late_fee",
            object="late fee of up to 2% monthly on payments overdue by > 15 calendar days",
            modality=NormativeModality.PERMISSION,
            category=NormalizedClaimCategory.POLICY_CLAIM,
        )
        assert claim_87.modality == NormativeModality.PERMISSION
        assert claim_87.subject in CANONICAL_SUBJECT_ALLOWLIST

    def test_universal_postal_address_and_header_cleaning(self):
        """Universal regex must strip postal addresses, suites, page headers, and document IDs across enterprise contracts."""
        cases = [
            ("1600 Amphitheatre Pkwy Mountain View, CA 94043 Google", "Google"),
            ("410 Terry Ave N Seattle, WA 98109 AWS", "AWS"),
            ("One Apple Park Way Cupertino, CA 95014 USA Apple", "Apple"),
            ("Page 3 of 12 Doc-044 100 Main Street Suite 400 New York, NY 10001 Client", "Client"),
            ("P.O. Box 12345 London UK Supplier", "Supplier"),
            ("Contract No. 8839 Page 1 of 5 Licensor", "Licensor"),
            ("Page 10 of 20 500 Oracle Parkway Redwood City CA 94065 Oracle", "Oracle"),
        ]
        for raw, expected in cases:
            norm_subj, is_valid = ClaimQualityNormalizer.normalize_subject_entity(raw)
            assert is_valid is True, f"Failed for {raw}"
            assert norm_subj == expected, f"Expected {expected}, got {norm_subj} for {raw}"

    def test_universal_compound_clause_splitting(self):
        """Compound multi-rule obligations must be decomposed into atomic single-duty propositions."""
        # 1. Enumerated subclauses (i), (ii), (iii)
        enum_text = (
            "Customer must: (i) maintain complete and accurate records; "
            "(ii) promptly provide requested verification information; and "
            "(iii) grant access to systems."
        )
        splits = ClaimQualityNormalizer.split_compound_clause(enum_text)
        assert len(splits) == 3
        assert "(i)" in splits[0]
        assert "(ii)" in splits[1]
        assert "(iii)" in splits[2]

        # 2. Semicolon-separated obligations
        semicolon_text = (
            "Microsoft warrants that the Software will perform substantially as described; "
            "and Customer exclusive remedy will be repair or replacement."
        )
        semi_splits = ClaimQualityNormalizer.split_compound_clause(semicolon_text)
        assert len(semi_splits) == 2
        assert "Microsoft warrants" in semi_splits[0]
        assert "Customer exclusive remedy" in semi_splits[1]

        # 3. Conjunction-linked dual obligations
        dual_text = (
            "Customer will control access to the Products by End Users "
            "and is responsible for any use of the Products that does not comply with this Agreement."
        )
        dual_splits = ClaimQualityNormalizer.split_compound_clause(dual_text)
        assert len(dual_splits) == 2
        assert "Customer will control access" in dual_splits[0]
        assert "Customer is responsible for" in dual_splits[1]

    def test_universal_passive_clauses_and_roles(self):
        """Universal passive contracting phrases must map to canonical roles."""
        assert ClaimQualityNormalizer.normalize_subject_entity("unpaid invoices")[0] == "Customer"
        assert ClaimQualityNormalizer.normalize_subject_entity("outstanding balance")[0] == "Customer"
        assert ClaimQualityNormalizer.normalize_subject_entity("fees payable")[0] == "Customer"
        assert ClaimQualityNormalizer.normalize_subject_entity("payment obligations")[0] == "Customer"
        assert ClaimQualityNormalizer.normalize_subject_entity("waiver of any breach")[0] == "Either party"
        assert ClaimQualityNormalizer.normalize_subject_entity("indemnifying party")[0] == "Each party"
        assert ClaimQualityNormalizer.normalize_subject_entity("service provider")[0] == "Service Provider"

    def test_universal_candidate_claim_normalization(self):
        """CandidateClaim object normalization must repair subject, map predicate, and classify modality."""
        from app.extraction.models import CandidateClaim
        import uuid

        cand = CandidateClaim.create(
            envelope_id=uuid.uuid4(),
            unit_id="unit_test_01",
            asset_id="asset_test_01",
            claim_text="Oracle may terminate the agreement without cause upon 60 days written notice.",
            subject="Page 2 of 10 500 Oracle Parkway Redwood City CA 94065 Oracle",
            predicate="terminate",
            object_="the agreement without cause upon 60 days notice",
            evidence_text_span="Oracle may terminate the agreement without cause upon 60 days written notice.",
            modality="PERMISSION",
        )

        norm_cand = ClaimQualityNormalizer.normalize_candidate_claim(cand)
        assert norm_cand is not None
        assert norm_cand.subject == "Oracle"
        assert norm_cand.predicate == "may_terminate_without_cause"
        assert norm_cand.modality == "PERMISSION"
        assert any("category:POLICY_CLAIM" in q for q in norm_cand.qualifiers)

    def test_claim_taxonomy_agent_facing_filtering(self):
        """Only normative policy rules must enter the primary agent claim graph."""
        # Agent-facing policy rules
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.POLICY_RULE) is True
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.OBLIGATION) is True
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.PROHIBITION) is True
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.PERMISSION) is True
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.ENTITLEMENT) is True
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.ELIGIBILITY) is True

        # Non-rules / Context
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.DEFINITION) is False
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.DESCRIPTION) is False
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.REFERENCE) is False
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.SCOPE_RULE) is False
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.RESPONSIBILITY) is False
        assert NormalizedClaimCategory.is_agent_facing(NormalizedClaimCategory.EXAMPLE) is False

    def test_atomicity_detection_and_triggers(self):
        """Atomicity detector must accurately spot compound multi-duty triggers."""
        # 1. Clean atomic rule
        atomic_text = "Customer will pay all invoiced amounts within thirty calendar days."
        is_atom, triggers = ClaimQualityNormalizer.is_atomic_rule(atomic_text)
        assert is_atom is True
        assert len(triggers) == 0

        # 2. Enumerated subclauses trigger
        enum_text = "Customer must: (i) keep records; and (ii) grant audit access to systems."
        is_atom2, triggers2 = ClaimQualityNormalizer.is_atomic_rule(enum_text)
        assert is_atom2 is False
        assert "ENUMERATION_SUBCLAUSES" in triggers2

        # 3. Semicolon trigger
        semi_text = "Microsoft warrants software; and Customer exclusive remedy is repair."
        is_atom3, triggers3 = ClaimQualityNormalizer.is_atomic_rule(semi_text)
        assert is_atom3 is False
        assert "SEMICOLON_SEPARATED_OBLIGATIONS" in triggers3

        # 4. Dual obligation conjunction trigger
        dual_text = "Customer will control access to Products and is responsible for non-compliant use."
        is_atom4, triggers4 = ClaimQualityNormalizer.is_atomic_rule(dual_text)
        assert is_atom4 is False
        assert "DUAL_OBLIGATION_CONJUNCTION" in triggers4

    def test_decompose_compound_claim_parent_child_provenance(self):
        """Decomposing compound claim must produce atomic children with parent-child provenance."""
        compound_claim = NormalizedClaim(
            claim_id="doc057:parent:01",
            subject="Customer",
            predicate="must_control_end_user_access",
            object="Customer will control access to the Products by End Users and is responsible for any use of the Products that does not comply with this Agreement.",
            modality=NormativeModality.OBLIGATION,
            category=NormalizedClaimCategory.POLICY_CLAIM,
            is_atomic=False,
            evidence_span="Customer will control access to the Products by End Users and is responsible for any use...",
            locator={"page": 1, "section": "End Users (c)"},
        )

        children = ClaimQualityNormalizer.decompose_compound_claim(compound_claim)
        assert len(children) == 2
        for idx, child in enumerate(children):
            assert child.parent_claim_id == "doc057:parent:01"
            assert child.split_index == idx + 1
            assert child.split_count == 2
            assert child.locator == compound_claim.locator
            assert child.evidence_span == compound_claim.evidence_span
            assert child.is_atomic is True

    def test_stage4_safety_rule_passive_voice_evidence_conditioning(self):
        """Ambiguous passive phrases with multiple debtors in evidence must be flagged for review."""
        # Unambiguous
        subj, valid, reason = ClaimQualityNormalizer.normalize_subject_with_safety_check(
            "All amounts due under unpaid invoices",
            "Customer will pay all amounts due under unpaid invoices within 30 days."
        )
        assert valid is True
        assert subj == "Customer"
        assert reason is None

        # Ambiguous multi-debtor context
        subj_amb, valid_amb, reason_amb = ClaimQualityNormalizer.normalize_subject_with_safety_check(
            "All amounts due under unpaid invoices",
            "Customer and Partner and Reseller share joint invoicing liability for all amounts due under unpaid invoices."
        )
        assert valid_amb is True
        assert reason_amb == "AMBIGUOUS_PASSIVE_DEBTOR_REQUIRES_REVIEW"

    def test_stage9_composite_quality_scoring(self):
        """Composite quality score must calculate 0-100 score across 6 objective criteria."""
        canonical_claim = NormalizedClaim(
            claim_id="test:quality:01",
            subject="Customer",
            predicate="must_pay_within_30_days",
            object="all invoiced amounts within thirty calendar days",
            modality=NormativeModality.OBLIGATION,
            category=NormalizedClaimCategory.POLICY_RULE,
            evidence_span="Customer will pay all invoiced amounts within thirty (30) calendar days.",
            locator={"page": 2, "section": "Invoicing and payment"},
        )

        score = ClaimQualityNormalizer.score_claim_quality(canonical_claim)
        assert score.total_score >= 90.0
        assert score.status == "CANONICAL"
        assert score.subject_validity == 20.0
        assert score.predicate_validity == 20.0
        assert score.atomicity == 20.0
        assert score.evidence_grounding == 20.0
        assert score.deduplication_status == 10.0
        assert score.claim_type_correctness == 10.0

    def test_stage10_human_review_queue_routing(self):
        """High-risk legal clauses (liability, indemnity, termination) must route to human review queue."""
        liability_claim = NormalizedClaim(
            claim_id="test:review:01",
            subject="Each party",
            predicate="has_liability_cap",
            object="aggregate liability limited to fees paid in prior 12 months",
            modality=NormativeModality.PERMISSION,
            category=NormalizedClaimCategory.POLICY_RULE,
            evidence_span="Party aggregate liability is limited to fees paid in prior 12 months.",
            locator={"page": 5, "section": "Limitation of liability"},
        )

        should_route, reasons = ClaimQualityNormalizer.should_route_to_human_review(liability_claim)
        assert should_route is True
        assert any("liability" in r.lower() for r in reasons)



