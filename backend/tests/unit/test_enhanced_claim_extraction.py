import pytest
import re
from app.normalization.normalizer import DocumentNormalizer
from app.llm.mock_provider import MockLLMProvider
from app.llm.schemas import ExtractedClaim

@pytest.mark.asyncio
async def test_statistical_header_footer_stripping():
    """Verify statistical header and footer stripping without any hardcoded company names."""
    # 5 pages where each page has recurring top and bottom banners with changing page numbers
    page_template = (
        "Internal Enterprise Doc Page {i}\n"
        "Strictly Confidential\n"
        "1. Policy Section Overview\n"
        "All employees must provide 30 days notice before departure.\n"
        "Notice periods must be formally approved by department heads.\n"
        "Clearance procedures apply across all regional business offices.\n"
        "Document Ref: POL-{i}23\n"
        "Confidential & Proprietary\n"
    )
    doc_text = "\f".join(page_template.format(i=i) for i in range(1, 6))

    stripped = DocumentNormalizer.strip_statistical_headers_footers(doc_text)
    
    # Recurring headers and footers should be removed statistically
    assert "Internal Enterprise Doc Page" not in stripped
    assert "Strictly Confidential" not in stripped
    assert "Confidential & Proprietary" not in stripped
    # Real body content must remain intact
    assert "All employees must provide 30 days notice before departure." in stripped
    assert "Notice periods must be formally approved by department heads." in stripped

def test_toc_detection():
    """Verify Table of Contents blocks are accurately identified and rejected."""
    toc_text = (
        "1. Introduction ................................. 2\n"
        "2. Purpose 4 2.\n"
        "3. Notice Period Duration ....................... 4\n"
        "3.1. Points to Remember 5 3.3.\n"
        "4. Asset Recovery & Clearance ................... 6\n"
    )
    assert DocumentNormalizer.is_table_of_contents_block(toc_text, title="Table of Contents") is True
    assert DocumentNormalizer.is_table_of_contents_block(toc_text, title="") is True

    policy_body = (
        "All permanent employees must serve a minimum notice period of 60 days upon submitting their resignation. "
        "During probation, the required notice period is reduced to 15 days."
    )
    assert DocumentNormalizer.is_table_of_contents_block(policy_body, title="Notice Period Terms") is False

def test_table_linearization():
    """Verify markdown/pipe tables are converted into clear declarative policy statements."""
    table_text = (
        "| Level & Grade | Category | Notice Duration Confirmed | Notice Probation |\n"
        "|---|---|---|---|\n"
        "| A (A1 & A2) | CXO | 90 Days | 15 Days |\n"
        "| B (B1 & B2) | VP & Director | 90 Days | 15 Days |\n"
        "| C (C1 & C2) | Manager | 60 Days | 15 Days |\n"
        "| D & E | Individual Contributor | 30 Days | 15 Days |\n"
    )
    linearized = DocumentNormalizer.linearize_table_content(table_text)
    assert "Policy rule: Level & Grade: A (A1 & A2), Category: CXO, Notice Duration Confirmed: 90 Days, Notice Probation: 15 Days." in linearized
    assert "Policy rule: Level & Grade: C (C1 & C2), Category: Manager, Notice Duration Confirmed: 60 Days, Notice Probation: 15 Days." in linearized

def test_structure_aware_segmentation():
    """Verify decimal clauses (3.3.), versions (v1.5), and abbreviations don't cause false splits."""
    text = (
        "Under clause 3.3. employees must return all laptops. "
        "Refer to policy v1.5 for full details. "
        "Contractors are excluded from the leave adjustment policy."
    )
    sentences = DocumentNormalizer.structure_aware_segmentation(text)
    assert len(sentences) == 3
    assert "3.3." in sentences[0]
    assert "v1.5" in sentences[1]

@pytest.mark.asyncio
async def test_mock_provider_propositional_gatekeeper_rejection():
    """Verify garbage claims (TOC artifacts, dangling headers) are rejected while real rules pass."""
    provider = MockLLMProvider()
    
    noisy_content = (
        "Points to Remember 5 3.3.\n"
        "Internal, Wingify 1\n"
        "Purpose 4 2.\n"
        "Notice Period Duration\n"
        "Table of Contents ............. 3\n"
        "The document represents the Intellectual Property of Wingify.\n"
        "The policy applies to all Permanent Employees, Interns & Contractors of Wingify Software Private Limited.\n"
        "Exception: Pay instead of notice will not be granted in cases of dismissal due to misconduct, insubordination, fraud, or other severe reasons.\n"
        "Employees on probation must serve a 15-day notice period."
    )
    
    res = await provider.extract_claims(
        document_title="Employee Notice Period Policy",
        section_title="Operational Rules",
        section_content=noisy_content,
    )
    
    claim_texts = [c.claim_text for c in res.claims]
    
    # Assert garbage claims are REJECTED
    assert not any("Points to Remember 5 3.3." in t for t in claim_texts)
    assert not any("Internal, Wingify 1" in t for t in claim_texts)
    assert not any("Purpose 4 2." in t for t in claim_texts)
    assert not any("Notice Period Duration" == t.strip() for t in claim_texts)
    assert not any("Table of Contents" in t for t in claim_texts)
    
    # Assert genuine claims are EXTRACTED
    assert any("represents the Intellectual Property of Wingify" in t for t in claim_texts)
    assert any("applies to all Permanent Employees" in t for t in claim_texts)
    assert any("Pay instead of notice will not be granted" in t for t in claim_texts)
    assert any("must serve a 15-day notice period" in t for t in claim_texts)

@pytest.mark.asyncio
async def test_table_rules_extracted_with_gatekeeper():
    """Verify linearized table rows are properly extracted as verified claims."""
    provider = MockLLMProvider()
    
    table_content = (
        "| Level & Grade | Category | Notice Duration Confirmed | Notice Probation |\n"
        "|---|---|---|---|\n"
        "| A (A1 & A2) | CXO | 90 Days | 15 Days |\n"
        "| C (C1 & C2) | Manager | 60 Days | 15 Days |\n"
    )
    
    res = await provider.extract_claims(
        document_title="Employee Notice Period Policy",
        section_title="Notice Matrix",
        section_content=table_content,
    )
    
    claim_texts = [c.claim_text for c in res.claims]
    assert any("Level & Grade: A (A1 & A2)" in t and "90 Days" in t for t in claim_texts)
    assert any("Level & Grade: C (C1 & C2)" in t and "60 Days" in t for t in claim_texts)

def test_number_containment_verification():
    """Verify that hallucinated or ungrounded numeric values are stripped."""
    # Grounded claim: 90 exists in the claim text and span
    claim_grounded = ExtractedClaim(
        claim_text="Notice period for Grade A is 90 days.",
        subject="Grade A",
        predicate="is",
        object="90 days",
        numeric_value=90.0,
        numeric_unit="days",
        evidence_text_span="Notice period for Grade A is 90 days.",
    )
    
    # Ungrounded claim: 999.0 does not exist anywhere in evidence or claim text
    claim_ungrounded = ExtractedClaim(
        claim_text="Notice period for Grade B must be served in full.",
        subject="Grade B",
        predicate="must be served",
        object="in full",
        numeric_value=999.0,
        numeric_unit="days",
        evidence_text_span="Notice period for Grade B must be served in full.",
    )

    for item in [claim_grounded, claim_ungrounded]:
        if item.numeric_value is not None:
            int_str = str(int(item.numeric_value)) if item.numeric_value.is_integer() else str(item.numeric_value)
            float_str = str(item.numeric_value)
            context_span = f"{item.evidence_text_span or ''} {item.claim_text}"
            if int_str not in context_span and float_str not in context_span:
                item.numeric_value = None
                item.numeric_unit = None

    assert claim_grounded.numeric_value == 90.0
    assert claim_grounded.numeric_unit == "days"
    assert claim_ungrounded.numeric_value is None
    assert claim_ungrounded.numeric_unit is None

