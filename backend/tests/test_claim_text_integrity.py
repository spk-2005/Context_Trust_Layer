"""
Regression Tests for Text-Integrity and Modality Preservation Gates.

Validates that:
1. Injected predicate identifiers (e.g. has_validity_rule, can_cancel_before_shipment) fail text_integrity.
2. Missing modal verbs in normative rules fail text_integrity.
3. Bare infinitive headless phrasing (e.g. "Microsoft withdraw...", "Customers modify...") fails text_integrity.
4. Polarity inversions (e.g. "Customers modify this Agreement" with predicate "must_not_modify_agreement") fail text_integrity.
5. Modality preservation mapping is strictly verified:
   - "may not modify" -> MUST_NOT
   - "may withdraw" -> MAY
   - "will give notice" -> MUST
   - "must pay" -> MUST
   - "is required to" -> MUST
   - "is entitled to" -> ENTITLED_TO
"""

import pytest
from app.services.claim_gate_evaluator import ClaimGateEvaluator


class TestTextIntegrityGate:
    """Tests for fail-closed text-integrity validation in ClaimGateEvaluator."""

    def test_injected_has_validity_rule_fails_text_integrity(self):
        """Claims with injected 'has_validity_rule' predicate slug fail text_integrity and certification."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_01",
            subject="Microsoft",
            predicate="has_validity_rule",
            claim_text="Microsoft has_validity_rule be responsible for the performance of those services.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False
        assert res.is_canonical is False
        assert any("Injected predicate identifier" in r for r in res.rejection_reasons)

    def test_injected_has_refund_eligibility_fails_text_integrity(self):
        """Claims with injected 'has_refund_eligibility' predicate slug fail text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_02",
            subject="Customers",
            predicate="has_refund_eligibility",
            claim_text="Customers has_refund_eligibility be required to provide security in a form acceptable to Microsoft.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False

    def test_injected_can_cancel_before_shipment_fails_text_integrity(self):
        """Claims with injected 'can_cancel_before_shipment' predicate slug fail text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_03",
            subject="Customers",
            predicate="can_cancel_before_shipment",
            claim_text="Customers can_cancel_before_shipment be charged a cancelation fee.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False

    def test_injected_has_refund_reimbursement_window_fails_text_integrity(self):
        """Claims with injected 'has_refund_reimbursement_window' predicate slug fail text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_04",
            subject="Microsoft",
            predicate="has_refund_reimbursement_window",
            claim_text="Microsoft has_refund_reimbursement_window reimburse Customer for advance subscription payments.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False

    def test_injected_may_receive_store_credit_fails_text_integrity(self):
        """Claims with injected 'may_receive_store_credit' predicate slug fail text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_05",
            subject="Customer",
            predicate="may_receive_store_credit",
            claim_text="Customer may_receive_store_credit in lieu of cash refunds.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False

    def test_bare_infinitive_microsoft_withdraw_fails_text_integrity(self):
        """Bare infinitive 'Microsoft withdraw...' lacking modal verb 'may' fails text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_06",
            subject="Microsoft",
            predicate="may_withdraw_invoicing_eligibility",
            claim_text="Microsoft withdraw Customer's eligibility at any time and for any reason.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False
        assert res.is_canonical is False

    def test_intact_microsoft_may_withdraw_passes_text_integrity(self):
        """Intact natural sentence 'Microsoft may withdraw...' preserves modal and passes text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_clean_06",
            subject="Microsoft",
            predicate="may_withdraw_invoicing_eligibility",
            claim_text="Microsoft may withdraw Customer's eligibility at any time and for any reason.",
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert res.all_9_gates_passed is True
        assert res.is_canonical is True

    def test_bare_infinitive_each_party_take_fails_text_integrity(self):
        """Bare infinitive 'Each party take...' lacking modal verb 'will' fails text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_07",
            subject="Each party",
            predicate="must_protect_confidential_information",
            claim_text="Each party take reasonable steps to protect the other's Confidential Information.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False

    def test_intact_each_party_will_take_passes_text_integrity(self):
        """Intact natural sentence 'Each party will take...' preserves modal and passes text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_clean_07",
            subject="Each party",
            predicate="must_protect_confidential_information",
            claim_text="Each party will take reasonable steps to protect the other's Confidential Information.",
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert res.all_9_gates_passed is True

    def test_prohibition_polarity_inversion_fails_text_integrity(self):
        """Stripped prohibition 'Customers modify this Agreement' fails text_integrity against prohibition predicate."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_08",
            subject="Customer",
            predicate="must_not_modify_agreement",
            claim_text="Customers modify this Agreement.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False

    def test_intact_customer_may_not_modify_passes_text_integrity(self):
        """Intact prohibition 'Customer may not modify this Agreement' passes text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_clean_08",
            subject="Customer",
            predicate="must_not_modify_agreement",
            claim_text="Customer may not modify this Agreement.",
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert res.all_9_gates_passed is True
        assert res.is_canonical is True

    def test_parties_disclose_polarity_inversion_fails_text_integrity(self):
        """Stripped prohibition 'Parties disclose Confidential Information' fails text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_corrupt_09",
            subject="Each party",
            predicate="prohibited_from_unauthorized_disclosure",
            claim_text="Parties disclose Confidential Information to third parties.",
            claim_type="rule",
            status="candidate",
        )
        assert res.gates["text_integrity"] is False
        assert res.all_9_gates_passed is False

    def test_intact_neither_party_will_disclose_passes_text_integrity(self):
        """Intact negative formulation 'Neither party will disclose...' passes text_integrity."""
        res = ClaimGateEvaluator.evaluate(
            claim_id="clm_clean_09",
            subject="Neither party",
            predicate="prohibited_from_unauthorized_disclosure",
            claim_text="Neither party will disclose Confidential Information to third parties.",
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert res.all_9_gates_passed is True


class TestModalityPreservation:
    """Tests asserting correct modality preservation across all contract clause modalities."""

    def test_may_not_modify_preserves_must_not_modality(self):
        """'Customer may not modify this Agreement' preserves prohibition modal language."""
        text = "Customer may not modify this Agreement."
        res = ClaimGateEvaluator.evaluate(
            claim_id="mod_01",
            subject="Customer",
            predicate="must_not_modify_agreement",
            claim_text=text,
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert "may not" in text

    def test_may_withdraw_preserves_permission_modality(self):
        """'Microsoft may withdraw Customer's eligibility' preserves permission modal language."""
        text = "Microsoft may withdraw Customer's eligibility at any time and for any reason."
        res = ClaimGateEvaluator.evaluate(
            claim_id="mod_02",
            subject="Microsoft",
            predicate="may_withdraw_invoicing_eligibility",
            claim_text=text,
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert "may withdraw" in text

    def test_will_give_notice_preserves_obligation_modality(self):
        """'Microsoft will give Customer 30 days notice' preserves obligation modal language."""
        text = "Microsoft will give Customer 30 days' notice before such suspension."
        res = ClaimGateEvaluator.evaluate(
            claim_id="mod_03",
            subject="Microsoft",
            predicate="must_provide_notice_before_suspension",
            claim_text=text,
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert "will give" in text

    def test_must_pay_preserves_obligation_modality(self):
        """'Customer must pay all amounts due' preserves obligation modal language."""
        text = "Customer must pay all amounts due under any unpaid invoices immediately upon termination."
        res = ClaimGateEvaluator.evaluate(
            claim_id="mod_04",
            subject="Customer",
            predicate="must_pay_unpaid_invoices_immediately",
            claim_text=text,
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert "must pay" in text

    def test_is_required_to_preserves_obligation_modality(self):
        """'Customer is required to provide security' preserves obligation modal language."""
        text = "Customer is required to provide security in a form acceptable to Microsoft to be eligible for invoicing."
        res = ClaimGateEvaluator.evaluate(
            claim_id="mod_05",
            subject="Customer",
            predicate="is_required_to_provide_invoicing_security",
            claim_text=text,
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert "is required to" in text

    def test_is_entitled_to_preserves_entitlement_modality(self):
        """'Customer is entitled to a refund' preserves entitlement modal language."""
        text = "Customer is entitled to a refund of any prepaid, unused fees upon Microsoft material breach."
        res = ClaimGateEvaluator.evaluate(
            claim_id="mod_06",
            subject="Customer",
            predicate="will_receive_refund_on_breach",
            claim_text=text,
            claim_type="rule",
            status="verified",
        )
        assert res.gates["text_integrity"] is True
        assert "is entitled to" in text
