"""
Unit and Property-Based Regression Test Suite for Semantic Predicate Grounding and Entailment.

Validates that Gate 4 (clause_entails_claim), Gate 7 (predicate_valid), Gate 5 (subject_valid),
and Gate 10 (claim_type_allowed) correctly prevent semantic predicate/evidence mismatches.

Covers the 7 targeted error classes identified in the Microsoft Customer Agreement audit:
1. Return Window vs. Audit License Acquisition / Remedy Notice
2. Invoicing Credit Assessment vs Recurring Auto-Debit Charges
3. Invoicing Security Collateral vs Refund Eligibility
4. Payment Due Date Entailment (Immediate vs 30 Days vs Indefinite)
5. Operational Delegation vs Professional Standards Warranty
6. Trade Law Operative Rules vs Non-Rule Descriptive Scope
7. Formal Writing & Signature Subject Integrity (Waiver vs Notice)
"""

import pytest
from app.schemas.evidence import ImmutableEvidenceSpan
from app.services.universal_gate_evaluator import UniversalGateEvaluator


def _create_evidence(text: str) -> ImmutableEvidenceSpan:
    return ImmutableEvidenceSpan.from_content(
        verbatim_quote=text,
        clause_text=text,
        content=text,
    )


class TestSemanticEntailmentRegression:
    """Positive and Negative test cases for semantic predicate entailment."""

    # -------------------------------------------------------------------------
    # Error Class 1: Return Window vs. Audit License Acquisition / Warranty Notice
    # -------------------------------------------------------------------------
    def test_return_window_negative_audit_license_acquisition(self):
        """Audit remedy to order licenses within 30 days is NOT a product return window."""
        text = (
            "If verification reveals any unlicensed use, Customer must, within 30 days, "
            "order sufficient licenses to cover the period of its unlicensed use."
        )
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="has_return_window",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.is_canonical is False
        assert any("return window" in r.lower() or "entailment" in r.lower() for r in res.rejection_reasons)

    def test_return_window_negative_warranty_notification_remedy(self):
        """Warranty breach remedy notice within 90 days is NOT a return window."""
        text = (
            "If Microsoft fails to do so, and Customer notifies Microsoft within 90 days "
            "from the completion of the work giving rise to the warranty claim, then Microsoft "
            "will, at its discretion, either re-perform the Professional Services or return the amount Customer paid for them."
        )
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="has_return_window",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.is_canonical is False

    def test_return_window_positive_actual_product_return(self):
        """Legitimate product return window clause entails has_return_window."""
        text = "Customer may return the Product within thirty (30) days of purchase for a full refund."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="has_return_window",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is True
        assert res.gates["predicate_valid"] is True

    # -------------------------------------------------------------------------
    # Error Class 2: Invoicing Credit Assessment vs Recurring Charges
    # -------------------------------------------------------------------------
    def test_recurring_charges_negative_credit_assessment(self):
        """Credit report authorization for invoicing eligibility is NOT recurring billing charges."""
        text = (
            "Customer authorizes Microsoft to obtain information about Customer's financial condition, "
            "which may include credit reports, to assess Customer's eligibility for invoicing."
        )
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="authorizes_recurring_charges",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.is_canonical is False

    def test_recurring_charges_positive_periodic_billing(self):
        """Legitimate automated subscription charge entails authorizes_recurring_charges."""
        text = (
            "By choosing a recurring payment method, Customer authorizes Microsoft to charge "
            "the payment method periodically for each renewal term."
        )
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="authorizes_recurring_charges",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is True

    # -------------------------------------------------------------------------
    # Error Class 3: Invoicing Security Collateral vs Refund Eligibility
    # -------------------------------------------------------------------------
    def test_refund_eligibility_negative_security_collateral(self):
        """Security deposit / collateral for invoicing is NOT refund eligibility."""
        text = "Customer may be required to provide security in a form acceptable to Microsoft to be eligible for invoicing."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="has_refund_eligibility",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.is_canonical is False

    def test_refund_eligibility_positive_fee_reimbursement(self):
        """Actual fee reimbursement clause entails has_refund_eligibility."""
        text = "Customer is eligible for a pro-rata refund of prepaid fees if the subscription is canceled."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="has_refund_eligibility",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is True

    # -------------------------------------------------------------------------
    # Error Class 4: Payment Due Date Entailment (Immediate vs 30 Days vs Indefinite)
    # -------------------------------------------------------------------------
    def test_payment_deadline_negative_immediate_receipt_contradiction(self):
        """Payment due 'immediately upon receipt' directly contradicts 'must_pay_within_30_days'."""
        text = (
            "Customer must pay for all Professional Services provided as of the "
            "termination date immediately upon receipt of an invoice."
        )
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_pay_within_30_days",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.is_canonical is False

    def test_payment_deadline_negative_no_deadline_in_sentence(self):
        """General liability for pre-termination services has no 30-day deadline."""
        text = "Customer will pay for all services provided or used before termination."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_pay_within_30_days",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.is_canonical is False

    def test_payment_deadline_positive_explicit_30_days(self):
        """Sentence with explicit 30-day deadline entails must_pay_within_30_days."""
        text = "Customer must pay all undisputed invoice amounts within thirty calendar days of invoice date."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_pay_within_30_days",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is True

    def test_payment_immediate_positive_dedicated_predicate(self):
        """Immediate payment clause entails must_pay_unpaid_invoices_immediately."""
        text = (
            "Customer must pay for all Professional Services provided as of the "
            "termination date immediately upon receipt of an invoice."
        )
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_pay_unpaid_invoices_immediately",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is True
        assert res.gates["predicate_valid"] is True

    # -------------------------------------------------------------------------
    # Error Class 5: Operational Delegation vs Professional Standards Warranty
    # -------------------------------------------------------------------------
    def test_warranty_negative_operational_subcontracting(self):
        """Permission to use affiliates and subcontractors is NOT a professional standards warranty."""
        text = "Microsoft may perform its obligations under this Agreement through its Affiliates and use subcontractors to provide certain services."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Microsoft",
            predicate="warrants_professional_standards",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.is_canonical is False

    def test_warranty_positive_professional_care_standard(self):
        """Actual warranty of professional skill entails warrants_professional_standards."""
        text = "Microsoft warrants that it will perform the Professional Services with professional care and skill."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Microsoft",
            predicate="warrants_professional_standards",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is True

    # -------------------------------------------------------------------------
    # Error Class 6: Trade Law Operative Rules vs Non-Rule
    # -------------------------------------------------------------------------
    def test_trade_law_suspension_is_an_operative_rule(self):
        """Trade law termination/suspension right must be classified as an operative RULE, not NON_RULE."""
        text = (
            "Microsoft may suspend or terminate this Agreement to the extent that Microsoft reasonably "
            "believes that performance would cause it to violate Trade Laws or put it at risk of becoming subject to sanctions."
        )
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Microsoft",
            predicate="may_suspend_for_trade_laws",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["claim_type_allowed"] is True
        assert res.certification_tier != "NON_RULE"

    def test_trade_law_compliance_is_an_operative_rule(self):
        """Mandatory trade law compliance obligation must be classified as an operative RULE."""
        text = "Each party will comply with all laws and regulations applicable to the import or export of the Products and Services Deliverables."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Each party",
            predicate="must_comply_with_trade_laws",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["claim_type_allowed"] is True
        assert res.certification_tier != "NON_RULE"

    # -------------------------------------------------------------------------
    # Error Class 7: Formal Writing & Signature Subject Integrity
    # -------------------------------------------------------------------------
    def test_waiver_subject_and_signature_requirement(self):
        """Waiver must have Waiver subject and must_be_in_writing_and_signed predicate."""
        text = "Any waiver must be in writing and signed by the waiving party."
        ev = _create_evidence(text)
        # Positive case:
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Waiver",
            predicate="must_be_in_writing_and_signed",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is True
        assert res.gates["subject_valid"] is True

        # Negative case: generic 'Either party' should fail subject specificity for a legal instrument
        res_neg = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Either party",
            predicate="must_be_in_writing",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        # Should detect that the signature requirement was omitted or subject misattributed
        assert res_neg.gates["clause_entails_claim"] is False or res_neg.gates["text_integrity"] is False or not res_neg.is_canonical

    # -------------------------------------------------------------------------
    # Dimension 1: The Same Verb with Different Objects
    # -------------------------------------------------------------------------
    def test_same_verb_different_objects_pay_taxes_vs_invoices(self):
        """Action 'pay' applied to 'taxes' cannot entail payment of 'invoices'."""
        text = "Customer will pay all applicable value added taxes owed under this Agreement."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_pay_unpaid_invoices_immediately",
            object_text="unpaid invoices",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision in ("INSUFFICIENT_EVIDENCE", "CONTRADICTED")

    def test_same_verb_different_objects_modify_product_vs_agreement(self):
        """Vendor permission to modify a Product does not entail Agreement modification restriction."""
        text = "Microsoft may modify or discontinue offering a Product or convert a Product to a Cloud Service."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Microsoft",
            predicate="must_not_modify_agreement",
            object_text="this Agreement",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision == "INSUFFICIENT_EVIDENCE"
        assert "object mismatch" in res.entailment_reason.lower()

    # -------------------------------------------------------------------------
    # Dimension 2: The Same Deadline Attached to Different Actions
    # -------------------------------------------------------------------------
    def test_same_deadline_different_actions_cure_breach_vs_pay(self):
        """A 30-day deadline to cure breach cannot entail a 30-day payment deadline."""
        text = "Either party may terminate this Agreement if the other party fails to cure a material breach within 30 days."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_pay_within_30_days",
            object_text="invoices",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision == "INSUFFICIENT_EVIDENCE"

    def test_same_deadline_different_actions_audit_remedy_vs_return(self):
        """A 30-day deadline to order licenses after audit cannot entail a 30-day return window."""
        text = "Customer must, within 30 days, order sufficient licenses to cover the period of its unlicensed use."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="has_return_window",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision == "INSUFFICIENT_EVIDENCE"
        assert "audit licensing remediation" in res.entailment_reason.lower()

    # -------------------------------------------------------------------------
    # Dimension 3: Permission versus Prohibition
    # -------------------------------------------------------------------------
    def test_permission_vs_prohibition_modality_contradiction(self):
        """Permission to amend agreement directly contradicts prohibition predicate."""
        text = "Customer may modify this Agreement upon 30 days written notice."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_not_modify_agreement",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision == "CONTRADICTED"
        assert "direct contradiction" in res.entailment_reason.lower()

    def test_general_permission_vs_prohibition_direct_contradiction(self):
        """Permissive transfer right directly contradicts prohibition predicate."""
        text = "Customer may transfer perpetual licenses to an affiliated entity."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="prohibited_from_transfer",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision == "CONTRADICTED"

    # -------------------------------------------------------------------------
    # Dimension 4: Role Direction & Refund Payer versus Recipient
    # -------------------------------------------------------------------------
    def test_refund_payer_vs_recipient_role_reversal(self):
        """Obligation on vendor to refund Customer contradicts an obligation on Customer to refund."""
        text = "If Microsoft fails to do so, Microsoft will return the amount Customer paid for them."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_refund",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision == "CONTRADICTED"
        assert "role direction reversal" in res.entailment_reason.lower()

    # -------------------------------------------------------------------------
    # Dimension 5: Explicit Absence of a Deadline vs Direct Incompatible Deadline
    # -------------------------------------------------------------------------
    def test_explicit_absence_of_deadline_is_insufficient_evidence(self):
        """Pre-termination payment duty with no numerical timeframe is INSUFFICIENT_EVIDENCE for Net 30."""
        text = "Customer will pay for all services provided or used before termination."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_pay_within_30_days",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision == "INSUFFICIENT_EVIDENCE"
        assert "deadline absent" in res.entailment_reason.lower()

    def test_immediate_due_date_is_direct_deadline_contradiction(self):
        """Payment due immediately upon invoice receipt CONTRADICTS Net 30."""
        text = "Customer must pay for all Professional Services provided as of the termination date immediately upon receipt of an invoice."
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer",
            predicate="must_pay_within_30_days",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is False
        assert res.entailment_decision == "CONTRADICTED"
        assert "direct deadline contradiction" in res.entailment_reason.lower()

    # -------------------------------------------------------------------------
    # Dimension 6: Exact Monetary Basis and Lookback Representation
    # -------------------------------------------------------------------------
    def test_liability_cap_preserves_required_to_pay_basis(self):
        """Liability cap must preserve exact 'required to pay' basis and mutual applicability."""
        text = (
            "For each Product licensed on a subscription basis, each party's maximum aggregate liability "
            "to the other under this Agreement is limited to direct damages finally awarded in an amount "
            "not to exceed the amounts Customer was required to pay for the Products giving rise to the liability during the prior 12 months."
        )
        ev = _create_evidence(text)
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Each party",
            predicate="has_liability_cap_12_months",
            object_text="direct damages not to exceed amounts Customer was required to pay in prior 12 months",
            claim_type="RULE",
            evidence=ev,
            source_content=text,
        )
        assert res.gates["clause_entails_claim"] is True
        assert res.gates["predicate_valid"] is True
        assert res.is_canonical is True

    # -------------------------------------------------------------------------
    # Dimension 7: Revision Lineage Preservation
    # -------------------------------------------------------------------------
    def test_claim_revision_lineage_preserves_original_and_revised(self):
        """Original defective claim must be evaluated as-is and rejected, while revised claim is verified independently."""
        from app.services.claim_revision_lineage import ClaimRevisionManager

        text = "All notices must be in writing."
        ev = _create_evidence(text)
        orig_id = "cand:env-123:99:7d123f9fe1e2:24d1e3ea29"

        orig_res, rev_res, lineage_rec = ClaimRevisionManager.evaluate_and_revise(
            original_candidate_id=orig_id,
            subject="Either party",
            predicate="must_be_in_writing",
            object_text="written format",
            claim_text=text,
            evidence_span=ev,
            proposed_subject="Notice",
            proposed_predicate="must_be_in_writing",
            proposed_object="written format",
            proposed_claim_text="All notices must be in writing.",
            revision_reason="Subject correction from generic Either party to unilateral legal entity Notice",
            pipeline_run_id="run-456",
            envelope_id="env-123",
            unit_id="99",
        )

        # 1. Original representation was evaluated as-is and NOT certified
        assert orig_res.is_canonical is False
        assert orig_res.certification_tier == "REVIEW_REQUIRED"
        assert orig_res.entailment_decision == "INSUFFICIENT_EVIDENCE"

        # 2. Revised representation was evaluated independently and certified
        assert rev_res is not None
        assert rev_res.is_canonical is True
        assert rev_res.certification_tier == "AUTOMATED_CERTIFIED"
        assert rev_res.entailment_decision == "SUPPORTED"

        # 3. Lineage record links both distinct candidate IDs
        assert lineage_rec is not None
        assert lineage_rec.original_candidate_id == orig_id
        assert lineage_rec.revised_candidate_id.startswith("cand:env-123:99:")
        assert lineage_rec.original_candidate_id != lineage_rec.revised_candidate_id
        assert lineage_rec.pipeline_run_id == "run-456"
        assert lineage_rec.original_gate_status == "REVIEW_REQUIRED"
        assert lineage_rec.revised_gate_status == "AUTOMATED_CERTIFIED"

    def test_original_trade_law_suspension_misclassified_as_security_breach_is_not_certified(self):
        """Original claim with trade law evidence misclassified as security/breach suspension must NOT be certified."""
        from app.services.claim_revision_lineage import ClaimRevisionManager

        text = "Microsoft may suspend or terminate this Agreement to the extent that Microsoft reasonably considers necessary to prevent a violation of Trade Laws or to comply with a sanction, embargo, or other requirement."
        ev = _create_evidence(text)
        orig_id = "cand:ca5819b9-d96e-5b38-8742-9d5e019d3974:113:282900fce780:8d564f28e9"

        orig_res, rev_res, lineage_rec = ClaimRevisionManager.evaluate_and_revise(
            original_candidate_id=orig_id,
            subject="Microsoft",
            predicate="may_suspend_for_security_or_breach",
            object_text="this Agreement",
            claim_text=text,
            evidence_span=ev,
            proposed_subject="Microsoft",
            proposed_predicate="may_suspend_for_trade_laws",
            proposed_object="this Agreement",
            proposed_claim_text=text,
            revision_reason="Predicate correction from security/breach suspension to trade laws and sanctions suspension",
            pipeline_run_id="run-789",
            envelope_id="ca5819b9-d96e-5b38-8742-9d5e019d3974",
            unit_id="113",
        )

        # Original representation must fail Gate 4 and be REVIEW_REQUIRED
        assert orig_res.is_canonical is False
        assert orig_res.certification_tier == "REVIEW_REQUIRED"
        assert orig_res.entailment_decision == "INSUFFICIENT_EVIDENCE"
        assert "trade law" in orig_res.entailment_reason.lower()

        # Revised representation passes independently
        assert rev_res is not None
        assert rev_res.is_canonical is True
        assert rev_res.certification_tier == "AUTOMATED_CERTIFIED"
        assert rev_res.entailment_decision == "SUPPORTED"

    def test_original_waiver_with_contracting_party_and_missing_signature_is_not_certified(self):
        """Original claim with Either party and missing signature condition must NOT be certified."""
        from app.services.claim_revision_lineage import ClaimRevisionManager

        text = "Any waiver must be in writing and signed by the waiving party."
        ev = _create_evidence(text)
        orig_id = "cand:ca5819b9-d96e-5b38-8742-9d5e019d3974:94:f2cbad984704:19754b4912"

        orig_res, rev_res, lineage_rec = ClaimRevisionManager.evaluate_and_revise(
            original_candidate_id=orig_id,
            subject="Either party",
            predicate="must_be_in_writing",
            object_text="written format",
            claim_text=text,
            evidence_span=ev,
            proposed_subject="Waiver",
            proposed_predicate="must_be_in_writing_and_signed",
            proposed_object="the waiving party",
            proposed_claim_text=text,
            revision_reason="Subject correction from Either party to Waiver and predicate condition preservation for signature",
            pipeline_run_id="run-789",
            envelope_id="ca5819b9-d96e-5b38-8742-9d5e019d3974",
            unit_id="94",
        )

        # Original representation must fail Gate 4 and be REVIEW_REQUIRED
        assert orig_res.is_canonical is False
        assert orig_res.certification_tier == "REVIEW_REQUIRED"
        assert orig_res.entailment_decision == "INSUFFICIENT_EVIDENCE"

        # Revised representation passes independently
        assert rev_res is not None
        assert rev_res.is_canonical is True
        assert rev_res.certification_tier == "AUTOMATED_CERTIFIED"
        assert rev_res.entailment_decision == "SUPPORTED"


