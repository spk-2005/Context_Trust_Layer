"""
Unit tests for Reproducible Claim Repair Engine & Audit Registry (Sprint AF-14).
Validates:
1. Declarative repair application (scoped premise, quote expansion, condition inference).
2. Compound claim splitting into atomic children with parent quarantine.
3. Before-and-after entailment verification tracking.
4. Export and rerunnability of the repair audit ledger.
"""

import json
from pathlib import Path
import pytest

from app.extraction.claim_repair_engine import (
    ClaimRepairEngine,
    ClaimRepairRegistry,
    RepairDisposition,
)
from app.schemas.canonical_claim_v3 import (
    CanonicalClaimV3,
    ClaimStatus,
    CounterpartyPayload,
    EvidenceV3,
    GatesV3,
    ModalityV3,
    ObjectPayload,
    PredicatePayload,
    ProvenanceV3,
    SubjectPayload,
)


@pytest.fixture
def raw_claim_013():
    return CanonicalClaimV3(
        claim_id="doc057:af:013",
        document_id="DOC-057",
        clause_id="SEC-01-013",
        document_type="contract",
        status=ClaimStatus.REVIEW,
        subject=SubjectPayload(raw_text="Customer", canonical_entity="Customer"),
        counterparty=CounterpartyPayload(raw_text="Microsoft", canonical_entity="Microsoft", relationship="OBLIGEE"),
        predicate=PredicatePayload(raw_text="prohibit", normalized_action="prohibited_from_commercial_hosting"),
        object=ObjectPayload(
            raw_text="commercial hosting",
            normalized_object="distribute, sublicense, rent, lease, or lend Products/Deliverables, or use them to offer hosting services to third parties",
        ),
        modality=ModalityV3.MUST_NOT,
        conditions=[],
        evidence=EvidenceV3(
            verbatim_quote="(vii) distribute, sublicense, rent, lease, or lend any Products or Services Deliverables, in whole or in part",
            clause_text="Microsoft Customer Agreement: Page 2 of 11 (vii) distribute, sublicense, rent, lease, or lend any Products or Services Deliverables, in whole or in part, or use them to offer hosting services to third parties; (g) Customer may only transfer perpetual licenses solely in connection with the transfer of hardware.",
            page=2,
            char_start=6100,
            char_end=6200,
        ),
        provenance=ProvenanceV3(),
        gates=GatesV3(span_exists=True, subject_valid=True, predicate_valid=True),
    )


@pytest.fixture
def raw_claim_024():
    return CanonicalClaimV3(
        claim_id="doc057:af:024",
        document_id="DOC-057",
        clause_id="SEC-01-024",
        document_type="contract",
        status=ClaimStatus.REVIEW,
        subject=SubjectPayload(raw_text="Customer", canonical_entity="Customer"),
        counterparty=CounterpartyPayload(raw_text="Affiliates", canonical_entity="Affiliates", relationship="BENEFICIARY"),
        predicate=PredicatePayload(raw_text="sublicense", normalized_action="may_sublicense_deliverables"),
        object=ObjectPayload(
            raw_text="Deliverables",
            normalized_object="its rights in Services Deliverables to its Affiliates (Affiliates may not further sublicense)",
        ),
        modality=ModalityV3.MAY,
        conditions=[],
        evidence=EvidenceV3(
            verbatim_quote="Customer may sublicense its rights in Services Deliverables to its Affiliates, but Customer's Affiliates may not further sublicense",
            clause_text="business purposes in connection with its use of Products and are nontransferable except as expressly permitted under this Agreement or applicable law. Customer may sublicense its rights in Services Deliverables to its Affiliates, but Customer's Affiliates may not further sublicense these rights.",
            page=2,
            char_start=8100,
            char_end=8250,
        ),
        provenance=ProvenanceV3(),
        gates=GatesV3(span_exists=True, subject_valid=True, predicate_valid=True),
    )


def test_repair_scoped_premise(raw_claim_013):
    """Verify REP-CLAUSE-SCOPE-001 transforms unentailed claim into CANONICAL with audit record."""
    engine = ClaimRepairEngine()
    repaired, rec, children = engine.apply_repair(raw_claim_013)

    assert rec is not None
    assert rec.repair_rule_id == "REP-CLAUSE-SCOPE-001"
    assert rec.disposition == RepairDisposition.REPAIR
    assert rec.before_clause_entails_claim is False
    assert rec.after_clause_entails_claim is True

    # Repaired claim now satisfies gates and becomes CANONICAL
    assert repaired.gates.clause_entails_claim is True
    assert repaired.status == ClaimStatus.CANONICAL
    assert len(children) == 0


def test_compound_split_creates_atomic_child(raw_claim_024):
    """Verify REP-COMPOUND-SPLIT-003 splits compound claim into atomic child and quarantines parent."""
    engine = ClaimRepairEngine()
    repaired_parent, rec, children = engine.apply_repair(raw_claim_024)

    assert rec is not None
    assert rec.repair_rule_id == "REP-COMPOUND-SPLIT-003"
    assert rec.disposition == RepairDisposition.SPLIT

    # Parent remains in REVIEW (never CANONICAL)
    assert repaired_parent.status == ClaimStatus.REVIEW
    assert repaired_parent.gates.clause_entails_claim is False

    # Atomic child is created and certified CANONICAL
    assert len(children) == 1
    child = children[0]
    assert child.claim_id == "doc057:af:024.01"
    assert child.status == ClaimStatus.CANONICAL
    assert child.gates.clause_entails_claim is True
    assert child.provenance.parent_claim_id == "doc057:af:024"


@pytest.fixture
def raw_claim_014():
    return CanonicalClaimV3(
        claim_id="doc057:af:014",
        document_id="DOC-057",
        clause_id="SEC-01-014",
        document_type="contract",
        status=ClaimStatus.REVIEW,
        subject=SubjectPayload(raw_text="Customer", canonical_entity="Customer"),
        counterparty=CounterpartyPayload(raw_text="Microsoft", canonical_entity="Microsoft", relationship="OBLIGEE"),
        predicate=PredicatePayload(raw_text="transfer", normalized_action="may_transfer_perpetual_license"),
        object=ObjectPayload(
            raw_text="perpetual licenses",
            normalized_object="fully-paid, perpetual licenses solely in connection with hardware transfer",
        ),
        modality=ModalityV3.MAY,
        conditions=[],
        evidence=EvidenceV3(
            verbatim_quote="Customer may only transfer fully-paid, perpetual licenses",
            clause_text="Customer may only transfer fully-paid, perpetual licenses to (1) an Affiliate or (2) a third party solely in connection with the transfer of the hardware to which they were assigned.",
            page=2,
            char_start=6300,
            char_end=6450,
        ),
        provenance=ProvenanceV3(),
        gates=GatesV3(span_exists=True, subject_valid=True, predicate_valid=True),
    )


@pytest.fixture
def raw_claim_043():
    return CanonicalClaimV3(
        claim_id="doc057:af:043",
        document_id="DOC-057",
        clause_id="SEC-05-043",
        document_type="contract",
        status=ClaimStatus.REVIEW,
        subject=SubjectPayload(raw_text="Each party", canonical_entity="Each party"),
        counterparty=CounterpartyPayload(raw_text="Other party", canonical_entity="Other party", relationship="OBLIGEE"),
        predicate=PredicatePayload(raw_text="provide defense cooperation", normalized_action="must_provide_defense_cooperation"),
        object=ObjectPayload(
            raw_text="defense assistance",
            normalized_object="all requested assistance, information, and authority",
        ),
        modality=ModalityV3.MUST,
        conditions=[],
        evidence=EvidenceV3(
            verbatim_quote="The party being def",  # Truncated quote defect
            clause_text="The party being defended must provide the defending party with all requested assistance, information, and authority. The defending party will reimburse the other party for reasonable out-of-pocket expenses.",
            page=4,
            char_start=14000,
            char_end=14150,
        ),
        provenance=ProvenanceV3(),
        gates=GatesV3(span_exists=True, subject_valid=True, predicate_valid=True),
    )


@pytest.fixture
def raw_claim_055():
    return CanonicalClaimV3(
        claim_id="doc057:af:055",
        document_id="DOC-057",
        clause_id="SEC-06-055",
        document_type="contract",
        status=ClaimStatus.REVIEW,
        subject=SubjectPayload(raw_text="Customer", canonical_entity="Customer"),
        counterparty=CounterpartyPayload(raw_text="Microsoft", canonical_entity="Microsoft", relationship="OBLIGEE"),
        predicate=PredicatePayload(raw_text="recurring charges", normalized_action="authorizes_recurring_charges"),
        object=ObjectPayload(
            raw_text="payment method charges",
            normalized_object="Microsoft to charge payment method periodically for each subscription until terminated",
        ),
        modality=ModalityV3.MUST,
        conditions=[],  # Missing renewal condition defect
        evidence=EvidenceV3(
            verbatim_quote="Customer authorizes Microsoft to charge Customer's payment method periodically for each subscription or billing period until the subscription is terminated.",
            clause_text="Recurring Payments. For subscriptions that renew automatically, Customer authorizes Microsoft to charge Customer's payment method periodically for each subscription or billing period until the subscription is terminated.",
            page=6,
            char_start=23000,
            char_end=23200,
        ),
        provenance=ProvenanceV3(),
        gates=GatesV3(span_exists=True, subject_valid=True, predicate_valid=True),
    )


@pytest.fixture
def raw_claim_057():
    return CanonicalClaimV3(
        claim_id="doc057:af:057",
        document_id="DOC-057",
        clause_id="SEC-07-057",
        document_type="contract",
        status=ClaimStatus.REVIEW,
        subject=SubjectPayload(raw_text="Microsoft", canonical_entity="Microsoft"),
        counterparty=CounterpartyPayload(raw_text="Customer", canonical_entity="Customer", relationship="BENEFICIARY"),
        predicate=PredicatePayload(raw_text="income taxes", normalized_action="must_pay_income_taxes"),
        object=ObjectPayload(
            raw_text="net income taxes",
            normalized_object="all taxes based upon its net income, gross receipts, and property ownership",
        ),
        modality=ModalityV3.MUST,
        conditions=[],
        evidence=EvidenceV3(
            verbatim_quote="Microsoft will be responsible for all taxes based upon its net income",
            clause_text="Taxes. Customer is responsible for all applicable taxes... Microsoft will be responsible for all taxes based upon its net income, gross receipts taxes imposed in lieu of taxes on income or profits, and taxes on its property ownership.",
            page=7,
            char_start=26000,
            char_end=26300,
        ),
        provenance=ProvenanceV3(),
        gates=GatesV3(span_exists=True, subject_valid=True, predicate_valid=True),
    )


def test_repair_condition_infer_014(raw_claim_014):
    """Verify REP-CONDITION-INFER-002 adds required Affiliate and fully-paid conditions."""
    engine = ClaimRepairEngine()
    repaired, rec, _ = engine.apply_repair(raw_claim_014)

    assert rec is not None
    assert rec.repair_rule_id == "REP-CONDITION-INFER-002"
    assert len(repaired.conditions) == 2
    assert repaired.gates.clause_entails_claim is True
    assert repaired.status == ClaimStatus.CANONICAL


def test_repair_quote_expand_043(raw_claim_043):
    """Verify REP-QUOTE-EXPAND-004 restores truncated verbatim quote."""
    engine = ClaimRepairEngine()
    repaired, rec, _ = engine.apply_repair(raw_claim_043)

    assert rec is not None
    assert rec.repair_rule_id == "REP-QUOTE-EXPAND-004"
    assert "The party being defended must provide" in repaired.evidence.verbatim_quote
    assert repaired.gates.clause_entails_claim is True
    assert repaired.status == ClaimStatus.CANONICAL


def test_repair_modality_trigger_055(raw_claim_055):
    """Verify REP-MODALITY-TRIGGER-005 attaches renewal trigger condition."""
    engine = ClaimRepairEngine()
    repaired, rec, _ = engine.apply_repair(raw_claim_055)

    assert rec is not None
    assert rec.repair_rule_id == "REP-MODALITY-TRIGGER-005"
    assert any("renew automatically" in c.text for c in repaired.conditions)
    assert repaired.gates.clause_entails_claim is True
    assert repaired.status == ClaimStatus.CANONICAL


def test_repair_tax_scope_057(raw_claim_057):
    """Verify REP-TAX-SCOPE-006 scopes clause strictly to Microsoft income tax sentence."""
    engine = ClaimRepairEngine()
    repaired, rec, _ = engine.apply_repair(raw_claim_057)

    assert rec is not None
    assert rec.repair_rule_id == "REP-TAX-SCOPE-006"
    assert "Customer is responsible for all applicable taxes" not in repaired.evidence.clause_text
    assert repaired.gates.clause_entails_claim is True
    assert repaired.status == ClaimStatus.CANONICAL


def test_unregistered_claim_untouched():
    """Verify engine passes through claims with no repair rule registered."""
    claim = CanonicalClaimV3(
        claim_id="doc057:af:999",
        document_id="DOC-057",
        clause_id="SEC-01",
        document_type="contract",
        status=ClaimStatus.CANONICAL,
        subject=SubjectPayload(raw_text="Customer", canonical_entity="Customer"),
        counterparty=None,
        predicate=PredicatePayload(raw_text="pay", normalized_action="must_pay"),
        object=ObjectPayload(raw_text="fees", normalized_object="fees"),
        modality=ModalityV3.MUST,
        conditions=[],
        evidence=EvidenceV3(verbatim_quote="Customer must pay fees.", clause_text="Customer must pay fees."),
        provenance=ProvenanceV3(),
        gates=GatesV3(span_exists=True, clause_entails_claim=True, subject_valid=True, predicate_valid=True),
    )

    engine = ClaimRepairEngine()
    repaired, rec, children = engine.apply_repair(claim)

    assert rec is None
    assert repaired.claim_id == "doc057:af:999"
    assert len(children) == 0


def test_export_repair_ledger(tmp_path, raw_claim_013):
    """Verify exported ledger contains complete JSON audit fields."""
    engine = ClaimRepairEngine()
    engine.apply_repair(raw_claim_013)

    out_file = tmp_path / "claim_repair_ledger.json"
    engine.export_ledger(out_file)

    assert out_file.exists()
    data = json.loads(out_file.read_text(encoding="utf-8"))
    assert len(data) == 1
    entry = data[0]
    assert entry["claim_id"] == "doc057:af:013"
    assert entry["repair_rule_id"] == "REP-CLAUSE-SCOPE-001"
    assert "original_clause_text" in entry
    assert "repaired_clause_text" in entry
    assert entry["before_clause_entails_claim"] is False
    assert entry["after_clause_entails_claim"] is True
