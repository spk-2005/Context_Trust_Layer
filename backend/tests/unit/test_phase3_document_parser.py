import io
import os
import re
import sys
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.ingestion.universal_file_parser import (
    UniversalFileParser,
    ContentBlockType,
    repair_ocr_text,
    mask_protected_tokens,
    unmask_protected_tokens,
)
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.db.enums import SourceFamily


def test_ocr_token_protection():
    """Verify repair_ocr_text protects dates, amounts, percentages, versions, and technical IDs."""
    sample = (
        "Compliant with AES256 and TLS1.3 for v2.0 on the 15th with $100k budget. "
        "Contact admin@example.com or visit https://example.com/api/v1. "
        "Complete migration within next30days and 50% discount."
    )
    repaired = repair_ocr_text(sample)

    # Protected tokens must NOT be split
    assert "AES256" in repaired
    assert "TLS1.3" in repaired
    assert "v2.0" in repaired
    assert "15th" in repaired
    assert "$100k" in repaired
    assert "admin@example.com" in repaired
    assert "https://example.com/api/v1" in repaired
    assert "50%" in repaired

    # Run-together words should be repaired
    assert "next 30 days" in repaired


def test_pdf_native_text_and_table_extraction():
    """Verify PyMuPDF extracts native text, bounding boxes, and tables with empty cell preservation."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)

    # Insert heading and paragraph
    page.insert_text((50, 50), "Section 1: Security Controls", fontsize=16)
    page.insert_text((50, 80), "All databases must enforce encryption at rest using AES-256.", fontsize=11)

    # Draw a table with 3 columns: Metric, Status, Notes
    # Row 0: Headers
    page.insert_text((50, 120), "Control ID", fontsize=10)
    page.insert_text((200, 120), "Status", fontsize=10)
    page.insert_text((350, 120), "Notes", fontsize=10)
    # Row 1: Data with an empty cell in 'Notes'
    page.insert_text((50, 140), "SEC-01", fontsize=10)
    page.insert_text((200, 140), "Enforced", fontsize=10)
    # Note col is empty
    # Row 2: Data
    page.insert_text((50, 160), "SEC-02", fontsize=10)
    page.insert_text((200, 160), "Pending", fontsize=10)
    page.insert_text((350, 160), "Review in Q4", fontsize=10)

    # Draw lines so find_tables identifies the grid
    page.draw_rect(pymupdf.Rect(45, 105, 500, 175))
    page.draw_line(pymupdf.Point(45, 125), pymupdf.Point(500, 125))
    page.draw_line(pymupdf.Point(45, 145), pymupdf.Point(500, 145))
    page.draw_line(pymupdf.Point(195, 105), pymupdf.Point(195, 175))
    page.draw_line(pymupdf.Point(345, 105), pymupdf.Point(345, 175))

    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = UniversalFileParser.parse_structured("security_policy.pdf", pdf_bytes)

    assert parsed.file_type == "pdf"
    assert parsed.is_scanned is False
    assert len(parsed.pages) == 1
    assert parsed.pages[0].selected_text_source == "native"
    assert "Section 1: Security Controls" in parsed.full_text
    assert "SEC-01" in parsed.full_text
    assert parsed.extraction_quality > 0.6


def test_pdf_short_native_page_not_classified_as_scanned():
    """Verify that a legitimate short page (e.g. 25 chars) is NOT marked as scanned."""
    import pymupdf

    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    # Legitimate short cover page / section divider
    page.insert_text((100, 200), "Part I: System Architecture", fontsize=18)
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = UniversalFileParser.parse_structured("architecture.pdf", pdf_bytes)

    assert len(parsed.pages) == 1
    page_res = parsed.pages[0]
    assert page_res.is_scanned_image is False
    assert page_res.selected_text_source == "native"
    assert "System Architecture" in page_res.text


def test_docx_interleaved_document_order():
    """Verify docx parses paragraphs, headings, and tables in exact sequential order."""
    import docx

    doc = docx.Document()
    doc.add_heading("Section 1: Infrastructure", level=1)
    doc.add_paragraph("All servers must reside in dedicated private VPC subnets.")

    t1 = doc.add_table(rows=2, cols=2)
    t1.cell(0, 0).text = "Subnet"
    t1.cell(0, 1).text = "CIDR"
    t1.cell(1, 0).text = "Private-A"
    t1.cell(1, 1).text = "10.0.1.0/24"

    doc.add_paragraph("Post-table audit notes: verified by CloudSec team.")

    doc.add_heading("Section 2: Database", level=1)
    doc.add_paragraph("Databases require Multi-AZ deployment.")

    bio = io.BytesIO()
    doc.save(bio)
    docx_bytes = bio.getvalue()

    parsed = UniversalFileParser.parse_structured("infra_guide.docx", docx_bytes)

    assert parsed.file_type == "docx"
    assert len(parsed.blocks) >= 5

    # Check block types in sequence
    b_types = [b.block_type for b in parsed.blocks]
    assert b_types[0] == ContentBlockType.HEADING
    assert b_types[1] == ContentBlockType.PARAGRAPH
    assert b_types[2] == ContentBlockType.TABLE
    assert b_types[3] == ContentBlockType.PARAGRAPH
    assert b_types[4] == ContentBlockType.HEADING

    # Verify paragraph after table comes strictly AFTER the table block
    assert "Post-table audit notes" in parsed.blocks[3].text
    assert parsed.blocks[3].heading_path[-1] == "Section 1: Infrastructure"
    assert parsed.blocks[4].heading_path[-1] == "Section 2: Database"


def test_xlsx_workbook_structure_and_formulas():
    """Verify openpyxl preserves sheet order, hidden sheets, cell coordinates, sparse cells, and formulas."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Financial Summary"

    ws1["A1"] = "Metric"
    ws1["B1"] = "Amount"
    ws1["C1"] = "Formula Note"

    ws1["A2"] = "Gross Revenue"
    ws1["B2"] = 1200000
    ws1["C2"] = "=B2"

    # Row 3 has sparse empty cell at A3
    ws1["B3"] = 450000

    ws1.merge_cells("A4:B4")
    ws1["A4"] = "Net Income Summary"

    ws2 = wb.create_sheet(title="Confidential Audits")
    ws2.sheet_state = "hidden"
    ws2["A1"] = "Audit Ref"
    ws2["B1"] = "AUD-9902"

    bio = io.BytesIO()
    wb.save(bio)
    xlsx_bytes = bio.getvalue()

    parsed = UniversalFileParser.parse_structured("financials.xlsx", xlsx_bytes)

    assert parsed.file_type == "xlsx"
    assert len(parsed.tables) == 2

    # Sheet 1 assertions
    t1 = parsed.tables[0]
    assert t1["sheet_name"] == "Financial Summary"
    assert t1["is_hidden"] is False
    assert "A4:B4" in t1["merged_ranges"]
    assert len(t1["cell_metadata"]) >= 4

    # Formula preserved in cell metadata
    cell_c2_meta = t1["cell_metadata"][1][2]
    assert cell_c2_meta["coordinate"] == "C2"
    assert cell_c2_meta["formula"] == "=B2"

    # Sparse row 3 preserves empty cell at col 1 without shifting col 2
    row3_meta = t1["cell_metadata"][2]
    assert row3_meta[0]["coordinate"] == "A3"
    assert row3_meta[0]["value"] is None
    assert row3_meta[1]["coordinate"] == "B3"
    assert row3_meta[1]["value"] == 450000

    # Sheet 2 assertions
    t2 = parsed.tables[1]
    assert t2["sheet_name"] == "Confidential Audits"
    assert t2["is_hidden"] is True


def test_html_dom_extraction():
    """Verify HTML DOM parsing strips script/style and extracts headings, lists, and tables."""
    html_content = """<!DOCTYPE html>
    <html>
    <head>
        <title>Compliance Overview</title>
        <style>body { font-family: sans-serif; } .secret { display: none; }</style>
        <script>console.log("malicious code execution");</script>
    </head>
    <body>
        <h1>1. Access Management</h1>
        <p>MFA is mandatory for all access points.</p>
        <ul>
            <li>FIDO2 security keys</li>
            <li>Authenticator apps</li>
        </ul>
        <table>
            <thead><tr><th>Role</th><th>Approval Level</th></tr></thead>
            <tbody>
                <tr><td>Developer</td><td>Manager</td></tr>
                <tr><td>DBA</td><td>VP Security</td></tr>
            </tbody>
        </table>
    </body>
    </html>
    """
    parsed = UniversalFileParser.parse_structured("compliance.html", html_content.encode("utf-8"))

    assert parsed.file_type == "html"
    assert "malicious code" not in parsed.full_text
    assert "font-family" not in parsed.full_text
    assert "1. Access Management" in parsed.full_text
    assert "MFA is mandatory" in parsed.full_text
    assert "FIDO2 security keys" in parsed.full_text
    assert "Developer" in parsed.full_text
    assert "VP Security" in parsed.full_text


def test_rtf_extraction():
    """Verify RTF control words, Unicode escapes, and hex escapes are cleanly decoded."""
    rtf_content = (
        r"{\rtf1\ansi\ansicpg1252\deff0"
        r"{\fonttbl{\f0\fnil\fcharset0 Calibri;}}"
        r"{\colortbl ;\red0\green0\blue0;}"
        r"\f0\fs24\b Policy Statement\b0\par"
        r"This document covers ISO-27001 compliance.\par"
        r"Copyright \'a9 2026. Em-dash \emdash here.\par"
        r"}"
    )
    parsed = UniversalFileParser.parse_structured("policy.rtf", rtf_content.encode("latin-1"))

    assert parsed.file_type == "rtf"
    assert "fonttbl" not in parsed.full_text
    assert "colortbl" not in parsed.full_text
    assert "Policy Statement" in parsed.full_text
    assert "ISO-27001" in parsed.full_text
    assert "©" in parsed.full_text or "Copyright" in parsed.full_text
    assert "—" in parsed.full_text or "Em-dash" in parsed.full_text


def test_markdown_structured_blocks():
    """Verify markdown preserves code blocks and tables as distinct ContentBlocks."""
    md_content = """---
title: System Guide
version: 1.0
---

# Architecture Overview

General system architecture details.

```python
# Fenced code block with symbols
def verify_hash(val):
    # This comment should not be a heading
    return val == 'sha256'
```

| Component | Port | Protocol |
| --- | --- | --- |
| API Gateway | 443 | HTTPS |
| Internal RPC | 8080 | gRPC |

- Item 1: High availability
- Item 2: Zero trust
"""
    parsed = UniversalFileParser.parse_structured("guide.md", md_content.encode("utf-8"))

    assert parsed.file_type == "markdown"
    b_types = [b.block_type for b in parsed.blocks]

    # Verify code block was extracted as CODE_OR_CONFIG
    code_blocks = [b for b in parsed.blocks if b.block_type == ContentBlockType.CODE_OR_CONFIG]
    assert len(code_blocks) >= 1
    assert "def verify_hash" in code_blocks[0].text
    assert "This comment should not be a heading" in code_blocks[0].text

    # Verify table block was extracted as TABLE
    table_blocks = [b for b in parsed.blocks if b.block_type == ContentBlockType.TABLE]
    assert len(table_blocks) >= 1
    assert table_blocks[0].table_data["headers"] == ["Component", "Port", "Protocol"]

    # Verify list items
    list_blocks = [b for b in parsed.blocks if b.block_type == ContentBlockType.LIST_ITEM]
    assert len(list_blocks) == 2


def test_legacy_binary_cfbf_rejection():
    """Verify legacy binary formats (.doc/.xls with CFBF magic bytes) are rejected with quality 0.0."""
    cfbf_bytes = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 512
    parsed = UniversalFileParser.parse_structured("legacy_policy.doc", cfbf_bytes)

    assert parsed.extraction_quality == 0.0
    assert any("Legacy binary format" in w for w in parsed.warnings)
    assert "[Legacy binary file 'legacy_policy.doc' cannot be parsed as modern OpenXML" in parsed.full_text


@pytest.mark.asyncio
async def test_document_parser_table_continuation_and_locator_authoritative():
    """Verify table continuation does not cause line/char drift and parser locator is authoritative."""
    text_content = """# Section 1: Overview

| Column 1 | Column 2 |
| --- | --- |
| Row 1 | Cell 1 |
|  | Wrapped multiline continuation |
| Row 2 | Cell 2 |

This paragraph follows the table.
"""
    envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="test_doc_001",
        source_family=SourceFamily.DOCUMENT,
        source_version="v1.0",
        native_format="markdown",
        content_hash="hash_001",
        raw_payload=text_content,
        locator_metadata={"line": 9999, "line_start": 9999},  # external stale metadata
    )

    res = await DocumentParser.parse(envelope)
    units = res.units

    # Heading (line 1), Row 1 (line 5), Row 2 (line 7), Paragraph (line 9)
    para_units = [u for u in units if u.block_type == "paragraph"]
    assert len(para_units) >= 1
    para_unit = para_units[0]

    # Verify authoritativeness: external line 9999 must NOT overwrite parser computed line 9
    assert para_unit.locator.line != 9999
    assert para_unit.locator.line_start != 9999
    assert para_unit.locator.line == 9

    # Verify table continuation merged into Row 1
    table_units = [u for u in units if u.block_type == "table_row"]
    assert len(table_units) == 2
    assert "Wrapped multiline continuation" in table_units[0].normalized_content
