"""
Unit tests for Universal Semantic Fidelity, Exact Lexical Adherence, and Multi-Domain Modal Logic.
Validates:
1. Zero lexical drift (no hallucinated words like 'active', 'balances', 'annual')
2. Boolean disjunction/conjunction fidelity (exact preservation of 'or' vs 'and')
3. Structured condition and cross-reference extraction
4. Correct deontic modality across multiple domains (OBLIGATION, PROHIBITION, PERMISSION, BENEFIT, POLICY_FACT)
5. Macro summary segregation (is_canonical=False)
6. Generalization across diverse corporate domains (SecOps, Vendor Contracts, SLAs, HR policies)
"""

import uuid
import pytest
from app.ingestion.envelope import EnvelopeFactory, SourceIntent
from app.ingestion.parsers.document_parser import DocumentParser
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.models import ExtractionStrategyType


@pytest.fixture
def org_and_source():
    return uuid.uuid4(), uuid.uuid4()


@pytest.mark.asyncio
async def test_audit_claims_exact_semantic_fidelity(org_and_source):
    """
    Validates all 11 flagged audit claims from the policy review:
    #11: Clean S-P-O with separate condition upon offboarding
    #12: Shipping cost benefit (not obligation) with agreed-upon method condition
    #13: Preserves exact asset retention condition without Boolean mutation
    #14: Preserves exact 'outstanding loans or advances' without 'active' or 'balances'
    #15: Preserves both 'HR Portal' and 'exit' in investment proof condition
    #16: Preserves exact 'allotted quota' without hallucinated 'annual'
    #17: Discretionary company right is PERMISSION ('holds_the_right'), not MUST
    #18: Joining bonus has offer letter cross-reference and condition
    #19 & #21: Summaries have is_canonical=False
    #20: Confidentiality is PROHIBITION
    #23: WFH allowance has 1-year condition and Home Office Allowance Policy cross-reference
    """
    org_id, src_id = org_and_source

    policy_content = """# Employee Notice Period Policy
Statement of Confidentiality
The unauthorized use or disclosure of this information in any media is prohibited.

## Policy Summary
Deductions from Full & Final Salary may include laptop and asset values, loan adjustments, taxes, WFH allowance recovery, excess leaves, short notice periods, joining bonus recovery, and EPF/VPF deductions.

## 3.2 Points to Remember
- Employees must return all Wingify property upon offboarding.
- Shipping costs will be covered by Wingify through a mutually agreed-upon method.

## 3.3 Deduction from Full & Final Salary
- If the employee retains the laptop and other company assets, their value will be deducted from the Full and Final Salary as per the Asset Management Policy.
- Any outstanding loans or advances the employee takes will be fully adjusted from their Full and Final Salary.
- If investment proofs, as declared on the HR Portal, are not provided during exit, taxes will be deducted accordingly.
- WFH Allowance will be recovered based on the Home Office Allowance Policy if the exit is within a year of joining.
- Recovery will be made for any excess leaves taken beyond the allotted quota.
- If the employee does not serve the full notice period, the company holds the right to recover the amount equivalent to the short notice period.
- Joining Bonus recovery will be as per the terms mentioned in the offer letter.
- EPF (Employee Provident Fund) and VPF (Voluntary Provident Fund) deductions will be made and deposited into the employee's account.
"""

    envelope = EnvelopeFactory.create_from_file_upload(
        filename="Wingify_Notice_Policy.md",
        raw_bytes=policy_content.encode("utf-8"),
        parsed_content=policy_content,
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )

    evidence = await DocumentParser.parse(envelope)
    candidates = CandidateDiscoveryEngine.discover_candidates(evidence.units)

    extracted_claims = []
    for u, strat, reason in candidates:
        claims = DomainRuleExtractor.extract_from_unit(u)
        extracted_claims.extend(claims)

    # 1. Claim #11: Clean S-P-O separation for property return
    c11 = next((c for c in extracted_claims if "return all wingify property" in c.claim_text.lower()), None)
    assert c11 is not None, "Claim #11 property return not found"
    assert c11.subject == "Employees"
    assert c11.predicate == "return"
    assert c11.object == "All Wingify property"
    assert "upon offboarding" not in c11.object.lower(), "Object must not contain the condition"
    assert any("upon offboarding" in cond.lower() for cond in c11.conditions)
    assert c11.modality == "OBLIGATION"

    # 2. Claim #12: Shipping costs coverage
    c12 = next((c for c in extracted_claims if "shipping costs" in c.claim_text.lower()), None)
    assert c12 is not None, "Claim #12 shipping costs not found"
    assert c12.modality == "POLICY_FACT"
    assert c12.claim_type == "company_benefit"
    assert any("mutually agreed-upon method" in cond.lower() for cond in c12.conditions)

    # 3. Claim #13: Laptop and asset retention condition
    c13 = next((c for c in extracted_claims if "retains the laptop and other company assets" in c.claim_text.lower()), None)
    assert c13 is not None, "Claim #13 asset retention not found"
    assert any("Asset Management Policy" in ref for ref in c13.cross_references)
    assert "laptop and other company assets" in c13.conditions[0]

    # 4. Claim #14: Zero-drift loans (no 'active' or 'balances')
    c14 = next((c for c in extracted_claims if "outstanding loans or advances" in c.claim_text.lower()), None)
    assert c14 is not None, "Claim #14 loans not found"
    assert "active" not in c14.conditions[0].lower(), "Must not inject 'active' into loan condition"
    assert "balances" not in c14.conditions[0].lower(), "Must not inject 'balances' into loan condition"
    assert "outstanding loans or advances" in c14.conditions[0].lower()

    # 5. Claim #15: Both 'HR Portal' and 'exit' in investment proof condition
    c15 = next((c for c in extracted_claims if "investment proofs" in c.claim_text.lower()), None)
    assert c15 is not None, "Claim #15 investment proofs not found"
    cond_text = " ".join(c15.conditions).lower()
    assert "hr portal" in cond_text, "Condition must preserve 'HR Portal'"
    assert "exit" in cond_text, "Condition must preserve 'exit'"

    # 6. Claim #16: Excess leaves (no 'annual')
    c16 = next((c for c in extracted_claims if c.claim_type != "derived_summary" and "excess leaves" in c.claim_text.lower()), None)
    assert c16 is not None, "Claim #16 excess leaves not found"
    assert "annual" not in c16.claim_text.lower()
    assert "annual" not in c16.object.lower()
    assert len(c16.conditions) > 0, "Claim #16 must have conditions"
    assert "annual" not in c16.conditions[0].lower()
    assert "allotted quota" in c16.conditions[0].lower()

    # 7. Claim #17: Short notice is PERMISSION ('holds_the_right')
    c17 = next((c for c in extracted_claims if "short notice period" in c.claim_text.lower() and "holds the right" in c.claim_text.lower()), None)
    assert c17 is not None, "Claim #17 short notice not found"
    assert c17.modality == "PERMISSION"
    assert c17.modal_operator == "holds_the_right"
    assert any("full notice period" in cond.lower() for cond in c17.conditions)

    # 8. Claim #18: Joining bonus cross-reference
    c18 = next((c for c in extracted_claims if c.claim_type != "derived_summary" and "joining bonus" in c.claim_text.lower()), None)
    assert c18 is not None, "Claim #18 joining bonus not found"
    assert any("Offer Letter" in ref for ref in c18.cross_references)
    assert any("offer letter" in cond.lower() for cond in c18.conditions)

    # 9. Claims #19 & #21: Macro summary is_canonical=False
    summaries = [c for c in extracted_claims if c.claim_type == "derived_summary"]
    assert len(summaries) >= 1
    for s in summaries:
        assert s.is_canonical is False, "Macro summaries must have is_canonical=False"

    # 10. Claim #20: Prohibition
    c20 = next((c for c in extracted_claims if "unauthorized use or disclosure" in c.claim_text.lower()), None)
    assert c20 is not None, "Claim #20 confidentiality not found"
    assert c20.modality == "PROHIBITION"

    # 11. Claim #23: WFH allowance 1-year condition and Home Office Policy
    c23 = next((c for c in extracted_claims if c.claim_type != "derived_summary" and "wfh allowance" in c.claim_text.lower()), None)
    assert c23 is not None, "Claim #23 WFH allowance not found"
    assert any("Home Office Allowance Policy" in ref for ref in c23.cross_references)
    assert any("1 year" in cond for cond in c23.conditions)


@pytest.mark.asyncio
async def test_general_multi_domain_semantic_fidelity(org_and_source):
    """
    Validates that the universal engine extracts accurate modality, conditions,
    and cross-references from completely non-HR domains:
    - Cloud Infrastructure / SecOps
    - Enterprise SLA
    - Vendor Procurement Agreement
    """
    org_id, src_id = org_and_source

    multi_domain_doc = """# Cloud Infrastructure Security & Vendor Service Agreement

## 1. Cloud Security Protocols
Engineers must rotate IAM access keys every 90 days.
The unauthorized export of production customer data is strictly prohibited.
If CPU utilization exceeds 85% for 5 consecutive minutes, the autoscaler holds the right to provision additional compute nodes as per the Scaling Policy.

## 2. SLA & Operations
Travel expenses will be covered by Enterprise Client through approved expense reports.
If monthly service availability falls below 99.9%, the subscriber is permitted to claim a credit penalty as per the Service Level Agreement.
Contractors must return all security badges upon contract termination.
"""

    envelope = EnvelopeFactory.create_from_file_upload(
        filename="Multi_Domain_Doc.md",
        raw_bytes=multi_domain_doc.encode("utf-8"),
        parsed_content=multi_domain_doc,
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )

    evidence = await DocumentParser.parse(envelope)
    candidates = CandidateDiscoveryEngine.discover_candidates(evidence.units)

    extracted = []
    for u, strat, reason in candidates:
        claims = DomainRuleExtractor.extract_from_unit(u)
        extracted.extend(claims)

    assert len(extracted) >= 5, f"Expected at least 5 claims from multi-domain document, got {len(extracted)}"

    # 1. SecOps Obligation with temporal condition
    iam_claim = next((c for c in extracted if "iam access keys" in c.claim_text.lower()), None)
    assert iam_claim is not None, "IAM rotation claim not found"
    assert iam_claim.modality == "OBLIGATION"
    assert iam_claim.predicate == "rotate"

    # 2. SecOps Prohibition
    export_claim = next((c for c in extracted if "unauthorized export" in c.claim_text.lower()), None)
    assert export_claim is not None, "Data export prohibition claim not found"
    assert export_claim.modality == "PROHIBITION"

    # 3. Discretionary scaling right with condition and cross-reference
    scale_claim = next((c for c in extracted if "autoscaler holds the right" in c.claim_text.lower()), None)
    assert scale_claim is not None, "Autoscaler right claim not found"
    assert scale_claim.modality == "PERMISSION"
    assert "holds" in scale_claim.modal_operator.lower()
    assert any("Scaling Policy" in ref for ref in scale_claim.cross_references)
    assert any("cpu utilization exceeds 85%" in cond.lower() for cond in scale_claim.conditions)

    # 4. Expense reimbursement benefit
    travel_claim = next((c for c in extracted if "travel expenses" in c.claim_text.lower()), None)
    assert travel_claim is not None, "Travel expenses claim not found"
    assert travel_claim.modality == "POLICY_FACT"

    # 5. SLA claim with condition and SLA cross-reference
    sla_claim = next((c for c in extracted if "credit penalty" in c.claim_text.lower()), None)
    assert sla_claim is not None, "SLA claim not found"
    assert sla_claim.modality == "PERMISSION"
    assert any("Service Level Agreement" in ref for ref in sla_claim.cross_references)
    assert any("service availability falls below 99.9%" in cond.lower() for cond in sla_claim.conditions)

    # 6. Contractor property return obligation with termination condition
    badge_claim = next((c for c in extracted if "security badges" in c.claim_text.lower()), None)
    assert badge_claim is not None, "Security badge return claim not found"
    assert badge_claim.modality == "OBLIGATION"
    assert any("contract termination" in cond.lower() for cond in badge_claim.conditions)
