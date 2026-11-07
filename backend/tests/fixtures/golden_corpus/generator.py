"""
Golden Corpus Generator & Manifest Builder for Trulin Phase 8.

Generates 18 version-controlled test fixtures and manifest.json containing
manually verified ground truth annotations across extraction, evidence units,
locators, candidate claims, conditions, exceptions, and validation status.
"""

from __future__ import annotations

import io
import json
import os
from pathlib import Path
from typing import Any, Dict


def generate_all_fixtures(output_dir: Path) -> Dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest: Dict[str, Any] = {
        "version": "1.0.0",
        "description": "Trulin Phase 8 Golden Corpus with verified ground truth expectations",
        "fixtures": {},
    }

    # -------------------------------------------------------------------------
    # 1. Native text PDF (native_text.pdf)
    # -------------------------------------------------------------------------
    import pymupdf
    doc1 = pymupdf.open()
    p1 = doc1.new_page(width=595, height=842)
    p1.insert_text((50, 50), "1. Data Retention Policy", fontsize=16)
    p1.insert_text((50, 80), "Customer account records must be preserved for 7 years following account closure.", fontsize=11)
    p1.insert_text((50, 110), "Audit logs are retained for 3 years.", fontsize=11)

    p2 = doc1.new_page(width=595, height=842)
    p2.insert_text((50, 50), "2. Access Control Rules", fontsize=16)
    p2.insert_text((50, 80), "All administrative accounts must enforce Multi-Factor Authentication (MFA).", fontsize=11)

    pdf1_path = output_dir / "native_text.pdf"
    doc1.save(str(pdf1_path))
    doc1.close()

    manifest["fixtures"]["native_text_pdf"] = {
        "filename": "native_text.pdf",
        "format": "pdf",
        "expected_pages": 2,
        "expected_blocks": 5,
        "expected_tables": 0,
        "expected_content": ["Data Retention Policy", "Customer account records must be preserved for 7 years", "Multi-Factor Authentication"],
        "expected_candidate_claims": [
            {"subject": "Customer account records", "predicate": "must be preserved for", "object": "7 years", "modality": "OBLIGATION"},
            {"subject": "All administrative accounts", "predicate": "must enforce", "object": "Multi-Factor Authentication", "modality": "OBLIGATION"},
        ],
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 2. Scanned PDF with OCR tokens (scanned_page.pdf)
    # -------------------------------------------------------------------------
    doc2 = pymupdf.open()
    p_scan = doc2.new_page(width=595, height=842)
    # Background rect representing scanned page
    p_scan.draw_rect(pymupdf.Rect(30, 30, 565, 812), color=(0.9, 0.9, 0.9), fill=(0.97, 0.97, 0.97))
    p_scan.insert_text((50, 60), "PURCHASE ORDER MEMORANDUM", fontsize=14)
    # Text with protected tokens and run-together words for repair_ocr_text testing
    p_scan.insert_text((50, 100), "Compliant with AES256 and TLS1.3 for v2.0 on the 15th with $100k budget.", fontsize=10)
    p_scan.insert_text((50, 130), "Contact admin@example.com or visit https://example.com/api/v1.", fontsize=10)
    p_scan.insert_text((50, 160), "Complete migration within next30days and 50% discount.", fontsize=10)

    pdf2_path = output_dir / "scanned_page.pdf"
    doc2.save(str(pdf2_path))
    doc2.close()

    manifest["fixtures"]["scanned_pdf"] = {
        "filename": "scanned_page.pdf",
        "format": "pdf",
        "is_scanned_simulation": True,
        "expected_pages": 1,
        "expected_protected_tokens": ["AES256", "TLS1.3", "v2.0", "15th", "$100k", "admin@example.com", "https://example.com/api/v1", "50%"],
        "ocr_ground_truth_text": "Compliant with AES256 and TLS1.3 for v2.0 on the 15th with $100k budget. Contact admin@example.com or visit https://example.com/api/v1. Complete migration within next 30 days and 50% discount.",
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 3. Complex PDF table (complex_table.pdf)
    # -------------------------------------------------------------------------
    doc3 = pymupdf.open()
    p_tbl = doc3.new_page(width=595, height=842)
    p_tbl.insert_text((50, 40), "Approval Authority Matrix", fontsize=14)
    # Draw table bounding lines
    p_tbl.draw_rect(pymupdf.Rect(45, 60, 520, 160))
    p_tbl.draw_line(pymupdf.Point(45, 90), pymupdf.Point(520, 90))
    p_tbl.draw_line(pymupdf.Point(45, 120), pymupdf.Point(520, 120))
    p_tbl.draw_line(pymupdf.Point(160, 60), pymupdf.Point(160, 160))
    p_tbl.draw_line(pymupdf.Point(280, 60), pymupdf.Point(280, 160))
    p_tbl.draw_line(pymupdf.Point(400, 60), pymupdf.Point(400, 160))

    # Headers
    p_tbl.insert_text((50, 80), "Tier", fontsize=10)
    p_tbl.insert_text((170, 80), "Max Expense", fontsize=10)
    p_tbl.insert_text((290, 80), "Approver", fontsize=10)
    p_tbl.insert_text((410, 80), "Notes", fontsize=10)

    # Row 1 (Note cell empty)
    p_tbl.insert_text((50, 110), "Standard", fontsize=10)
    p_tbl.insert_text((170, 110), "$1,000", fontsize=10)
    p_tbl.insert_text((290, 110), "Manager", fontsize=10)

    # Row 2
    p_tbl.insert_text((50, 145), "Executive", fontsize=10)
    p_tbl.insert_text((170, 145), "$10,000", fontsize=10)
    p_tbl.insert_text((290, 145), "Director", fontsize=10)
    p_tbl.insert_text((410, 145), "Written approval", fontsize=10)

    pdf3_path = output_dir / "complex_table.pdf"
    doc3.save(str(pdf3_path))
    doc3.close()

    manifest["fixtures"]["complex_pdf_table"] = {
        "filename": "complex_table.pdf",
        "format": "pdf",
        "expected_tables": 1,
        "expected_columns": ["Tier", "Max Expense", "Approver", "Notes"],
        "expected_empty_cells": 1,
        "expected_candidate_claims": [
            {"subject": "Standard", "predicate": "has_limit", "object": "$1,000", "column_header": "Max Expense"},
            {"subject": "Executive", "predicate": "has_limit", "object": "$10,000", "column_header": "Max Expense"},
        ],
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 4. Multi-page PDF table (multipage_table.pdf)
    # -------------------------------------------------------------------------
    doc4 = pymupdf.open()
    # Page 1
    p4_1 = doc4.new_page(width=595, height=842)
    p4_1.insert_text((50, 40), "Asset Registry (Part 1)", fontsize=14)
    p4_1.draw_rect(pymupdf.Rect(45, 60, 500, 160))
    p4_1.draw_line(pymupdf.Point(45, 90), pymupdf.Point(500, 90))
    p4_1.draw_line(pymupdf.Point(45, 125), pymupdf.Point(500, 125))
    p4_1.draw_line(pymupdf.Point(180, 60), pymupdf.Point(180, 160))
    p4_1.draw_line(pymupdf.Point(340, 60), pymupdf.Point(340, 160))
    p4_1.insert_text((50, 80), "Asset ID", fontsize=10)
    p4_1.insert_text((190, 80), "Classification", fontsize=10)
    p4_1.insert_text((350, 80), "Department", fontsize=10)
    p4_1.insert_text((50, 110), "AST-001", fontsize=10)
    p4_1.insert_text((190, 110), "Confidential", fontsize=10)
    p4_1.insert_text((350, 110), "Finance", fontsize=10)
    p4_1.insert_text((50, 145), "AST-002", fontsize=10)
    p4_1.insert_text((190, 145), "Restricted", fontsize=10)
    p4_1.insert_text((350, 145), "Security", fontsize=10)

    # Page 2 Continuation
    p4_2 = doc4.new_page(width=595, height=842)
    p4_2.insert_text((50, 40), "Asset Registry (Part 2 - Continuation)", fontsize=14)
    p4_2.draw_rect(pymupdf.Rect(45, 60, 500, 130))
    p4_2.draw_line(pymupdf.Point(45, 90), pymupdf.Point(500, 90))
    p4_2.draw_line(pymupdf.Point(180, 60), pymupdf.Point(180, 130))
    p4_2.draw_line(pymupdf.Point(340, 60), pymupdf.Point(340, 130))
    p4_2.insert_text((50, 80), "Asset ID", fontsize=10)
    p4_2.insert_text((190, 80), "Classification", fontsize=10)
    p4_2.insert_text((350, 80), "Department", fontsize=10)
    p4_2.insert_text((50, 115), "AST-003", fontsize=10)
    p4_2.insert_text((190, 115), "Public", fontsize=10)
    p4_2.insert_text((350, 115), "Marketing", fontsize=10)

    pdf4_path = output_dir / "multipage_table.pdf"
    doc4.save(str(pdf4_path))
    doc4.close()

    manifest["fixtures"]["multipage_pdf_table"] = {
        "filename": "multipage_table.pdf",
        "format": "pdf",
        "expected_pages": 2,
        "expected_tables": 2,
        "is_continuation": True,
        "expected_candidate_claims": [
            {"subject": "AST-001", "predicate": "has_classification", "object": "Confidential"},
            {"subject": "AST-003", "predicate": "has_classification", "object": "Public"},
        ],
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 5. DOCX with interleaved paragraphs and tables (interleaved_policy.docx)
    # -------------------------------------------------------------------------
    import docx
    d = docx.Document()
    d.add_heading("1. Workplace Ergonomics", level=1)
    d.add_paragraph("All workstations must be evaluated within 30 days of hire.")
    t1 = d.add_table(rows=2, cols=2)
    t1.cell(0, 0).text = "Equipment"
    t1.cell(0, 1).text = "Allowance"
    t1.cell(1, 0).text = "Ergonomic Chair"
    t1.cell(1, 1).text = "$300"
    d.add_paragraph("Follow-up evaluations are conducted biannually.")
    d.add_heading("2. Equipment Disposal", level=1)
    t2 = d.add_table(rows=2, cols=2)
    t2.cell(0, 0).text = "Category"
    t2.cell(0, 1).text = "Method"
    t2.cell(1, 0).text = "Electronics"
    t2.cell(1, 1).text = "Certified Recycler"

    docx_path = output_dir / "interleaved_policy.docx"
    d.save(str(docx_path))

    manifest["fixtures"]["docx_interleaved"] = {
        "filename": "interleaved_policy.docx",
        "format": "docx",
        "expected_headings": ["1. Workplace Ergonomics", "2. Equipment Disposal"],
        "expected_paragraphs": 2,
        "expected_tables": 2,
        "expected_candidate_claims": [
            {"subject": "All workstations", "predicate": "must be evaluated within", "object": "30 days of hire", "modality": "OBLIGATION"},
            {"subject": "Ergonomic Chair", "predicate": "has_allowance", "object": "$300"},
        ],
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 6. XLSX with multiple sheets, sparse cells, formulas and merged cells
    # -------------------------------------------------------------------------
    import openpyxl
    wb = openpyxl.Workbook()
    ws1 = wb.active
    ws1.title = "Executive Summary"
    ws1.merge_cells("A1:B1")
    ws1["A1"] = "FY2026 Financial Plan"
    ws1["A2"] = "Metric"
    ws1["B2"] = "Amount"
    ws1["A3"] = "Operating Budget"
    ws1["B3"] = 500000
    ws1["A4"] = "Security Allocation"
    ws1["B4"] = "=B3*0.15"

    ws2 = wb.create_sheet(title="Sparse Records")
    ws2["A1"] = "Record ID"
    ws2["B1"] = "Tag"
    ws2["C1"] = "Status"
    ws2["A2"] = "REC-01"
    # B2 is empty
    ws2["C2"] = "Active"
    ws2["A3"] = "REC-02"
    ws2["B3"] = "TAG-99"
    # C3 is empty

    ws3 = wb.create_sheet(title="Internal Audit")
    ws3.sheet_state = "hidden"
    ws3["A1"] = "Audit Ref"
    ws3["B1"] = "AUD-8801"

    xlsx_path = output_dir / "multi_sheet_sparse.xlsx"
    wb.save(str(xlsx_path))

    manifest["fixtures"]["xlsx_multi_sheet_sparse"] = {
        "filename": "multi_sheet_sparse.xlsx",
        "format": "xlsx",
        "expected_sheets": 3,
        "hidden_sheets": ["Internal Audit"],
        "merged_ranges": ["A1:B1"],
        "expected_formulas": ["=B3*0.15"],
        "expected_empty_cells": 2,
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 7. CSV with empty fields and quoted commas (quoted_empty_fields.csv)
    # -------------------------------------------------------------------------
    csv_rows = [
        "id,product_name,category,price,in_stock,notes",
        '1,Widget A,Electronics,29.99,true,"Standard, sealed"',
        '2,,Hardware,15.00,false,"Missing name"',
        '3,Super Gadget,,49.99,true,""',
        '4,Tool Set,Hardware,89.00,true,"Heavy duty, 50-piece"',
        '5,Sensor,,12.50,,',
        '6,Adapter,Electronics,9.99,true,"USB-C to HDMI, 4K"',
        '7,Cable,Accessories,4.99,true,""',
        '8,,Accessories,2.50,false,"No label"',
        '9,Display,Electronics,199.99,true,"IPS, 27-inch"',
        '10,Mount,Hardware,34.00,true,"VESA compatible, steel"',
        '11,Keyboard,Electronics,65.00,false,"Mechanical, tactile"',
        '12,Mouse,Electronics,,true,"Wireless, optical"',
        '13,Pad,Accessories,12.00,true,"XL cloth, stitched"',
        '14,Stand,Hardware,45.00,false,"Adjustable, aluminum"',
        '15,Case,Accessories,18.00,true,"Water resistant, padded"',
    ]
    csv_text = "\n".join(csv_rows) + "\n"
    csv_path = output_dir / "quoted_empty_fields.csv"
    csv_path.write_text(csv_text, encoding="utf-8")

    manifest["fixtures"]["csv_quoted_empty"] = {
        "filename": "quoted_empty_fields.csv",
        "format": "csv",
        "expected_rows": 15,
        "expected_columns": ["id", "product_name", "category", "price", "in_stock", "notes"],
        "expected_empty_cells": 6,
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 8. Nested JSON and JSON scalar (nested_and_scalar.json & scalar_payload.json)
    # -------------------------------------------------------------------------
    nested_obj = {
        "service": "IdentityGate",
        "version": "2.4.0",
        "active": True,
        "policies": [
            {
                "name": "PasswordPolicy",
                "rules": {
                    "min_length": 14,
                    "require_special": True,
                    "expiry_days": 90,
                },
            }
        ],
        "metadata": {
            "cluster": "us-east-1",
            "backup_enabled": None,
        },
    }
    json_path = output_dir / "nested_and_scalar.json"
    json_path.write_text(json.dumps(nested_obj, indent=2), encoding="utf-8")

    scalar_path = output_dir / "scalar_payload.json"
    scalar_path.write_text("true\n", encoding="utf-8")

    manifest["fixtures"]["nested_json"] = {
        "filename": "nested_and_scalar.json",
        "format": "json",
        "expected_fields": 8,
        "expected_candidate_claims": [
            {"subject": "IdentityGate", "predicate": "has_version", "object": "2.4.0"},
            {"subject": "PasswordPolicy.rules", "predicate": "has_min_length", "object": 14},
        ],
        "expected_validation_status": "SUPPORTED",
    }

    manifest["fixtures"]["scalar_json"] = {
        "filename": "scalar_payload.json",
        "format": "json",
        "is_scalar": True,
        "scalar_value": True,
        "expected_units": 1,
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 9. JSONL with more than 100 records (audit_records.jsonl)
    # -------------------------------------------------------------------------
    jsonl_lines = []
    for i in range(1, 126):  # 125 records
        jsonl_lines.append(json.dumps({
            "record_id": f"REC-{i:04d}",
            "timestamp": "2026-11-01T00:00:00Z",
            "event": "AUDIT_LOG",
            "actor": f"agent_{i % 5}",
            "is_authorized": True,
        }))
    jsonl_path = output_dir / "audit_records.jsonl"
    jsonl_path.write_text("\n".join(jsonl_lines) + "\n", encoding="utf-8")

    manifest["fixtures"]["jsonl_large"] = {
        "filename": "audit_records.jsonl",
        "format": "jsonl",
        "expected_records": 125,
        "must_not_truncate_at_100": True,
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 10. XML with attributes and namespaces (config_namespaces.xml)
    # -------------------------------------------------------------------------
    xml_content = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<sec:securityConfig xmlns:sec="http://trulin.io/security" xmlns:gov="http://trulin.io/governance">\n'
        '  <gov:policy id="POL-901" version="2.0">\n'
        '    <gov:rule id="RULE-01" level="mandatory">\n'
        '      <sec:enforceTLS version="1.3">All endpoints must enforce TLS 1.3 encryption.</sec:enforceTLS>\n'
        '    </gov:rule>\n'
        '    <gov:rule id="RULE-02" level="recommended">\n'
        '      <sec:rotateKeys frequency="90days">API keys should rotate every 90 days.</sec:rotateKeys>\n'
        '    </gov:rule>\n'
        '  </gov:policy>\n'
        '</sec:securityConfig>\n'
    )
    xml_path = output_dir / "config_namespaces.xml"
    xml_path.write_text(xml_content, encoding="utf-8")

    manifest["fixtures"]["xml_namespaces"] = {
        "filename": "config_namespaces.xml",
        "format": "xml",
        "expected_elements": ["policy", "rule", "enforceTLS", "rotateKeys"],
        "expected_attributes": ["id", "version", "level", "frequency"],
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 11. SQL DDL (schema_constraints.sql)
    # -------------------------------------------------------------------------
    sql_content = (
        "CREATE TABLE accounts (\n"
        "    id SERIAL PRIMARY KEY,\n"
        "    account_name VARCHAR(100) NOT NULL UNIQUE,\n"
        "    balance NUMERIC(12, 2) DEFAULT 0.00,\n"
        "    is_active BOOLEAN DEFAULT false,\n"
        "    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP\n"
        ");\n\n"
        "CREATE TABLE transactions (\n"
        "    tx_id UUID PRIMARY KEY,\n"
        "    account_id INT NOT NULL REFERENCES accounts(id),\n"
        "    amount NUMERIC(12, 2) NOT NULL,\n"
        "    status VARCHAR(20) DEFAULT 'pending'\n"
        ");\n"
    )
    sql_path = output_dir / "schema_constraints.sql"
    sql_path.write_text(sql_content, encoding="utf-8")

    manifest["fixtures"]["sql_ddl"] = {
        "filename": "schema_constraints.sql",
        "format": "sql",
        "expected_tables": ["accounts", "transactions"],
        "expected_falsy_defaults": {"balance": 0.00, "is_active": False},
        "expected_constraints": ["PRIMARY KEY", "NOT NULL", "UNIQUE", "REFERENCES"],
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 12. Database record with at least 50 fields (wide_relational_record.json)
    # -------------------------------------------------------------------------
    wide_record = {f"field_{i:02d}": f"val_{i}" if i % 2 == 0 else i * 10 for i in range(1, 56)}
    wide_record["user_id"] = "USR-998811"
    wide_record["is_compliant"] = True
    wide_path = output_dir / "wide_relational_record.json"
    wide_path.write_text(json.dumps(wide_record, indent=2), encoding="utf-8")

    manifest["fixtures"]["database_wide_record"] = {
        "filename": "wide_relational_record.json",
        "format": "json",
        "field_count": len(wide_record),
        "expected_min_fields": 50,
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 13. HTML with nested tables (nested_tables.html)
    # -------------------------------------------------------------------------
    html_content = (
        "<!DOCTYPE html>\n"
        "<html>\n"
        "<head>\n"
        "  <title>Governance Framework</title>\n"
        "  <style>body { font-family: Arial; } .hidden { display: none; }</style>\n"
        "  <script>console.log('strip me');</script>\n"
        "</head>\n"
        "<body>\n"
        "  <h1>Enterprise Governance Overview</h1>\n"
        "  <p>All internal applications must adhere to the data privacy charter.</p>\n"
        "  <table border='1' id='outer_table'>\n"
        "    <tr><th>Domain</th><th>Controls</th></tr>\n"
        "    <tr>\n"
        "      <td>Access Control</td>\n"
        "      <td>\n"
        "        <table border='1' id='inner_table'>\n"
        "          <tr><th>Control Code</th><th>Status</th></tr>\n"
        "          <tr><td>AC-01</td><td>Enforced</td></tr>\n"
        "        </table>\n"
        "      </td>\n"
        "    </tr>\n"
        "  </table>\n"
        "  <ul>\n"
        "    <li>Weekly credential rotation</li>\n"
        "    <li>Biometric entry logs</li>\n"
        "  </ul>\n"
        "</body>\n"
        "</html>\n"
    )
    html_path = output_dir / "nested_tables.html"
    html_path.write_text(html_content, encoding="utf-8")

    manifest["fixtures"]["html_nested_tables"] = {
        "filename": "nested_tables.html",
        "format": "html",
        "expected_headings": ["Enterprise Governance Overview"],
        "expected_tables": 2,
        "expected_list_items": 2,
        "scripts_stripped": True,
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 14. Markdown with headings, lists, links and code blocks (governance_readme.md)
    # -------------------------------------------------------------------------
    md_content = (
        "# Security Governance Readme\n\n"
        "## 1. Scope and Objective\n"
        "All engineers must complete secure code training within 60 days of onboarding.\n\n"
        "## 2. Automated Pipeline\n"
        "- Static code analysis (SAST) in CI\n"
        "- Dependency vulnerability scanning\n\n"
        "Refer to [Security Guidelines](https://internal.trulin.io/security) for details.\n\n"
        "```python\n"
        "def verify_signature(payload, secret):\n"
        "    return hmac.compare_digest(payload, secret)\n"
        "```\n"
    )
    md_path = output_dir / "governance_readme.md"
    md_path.write_text(md_content, encoding="utf-8")

    manifest["fixtures"]["markdown_rich"] = {
        "filename": "governance_readme.md",
        "format": "md",
        "expected_headings": ["Security Governance Readme", "1. Scope and Objective", "2. Automated Pipeline"],
        "expected_code_blocks": 1,
        "expected_links": 1,
        "expected_candidate_claims": [
            {"subject": "All engineers", "predicate": "must complete", "object": "secure code training within 60 days", "modality": "OBLIGATION"},
        ],
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 15. Duplicate text at different source locations (duplicate_provisions.md)
    # -------------------------------------------------------------------------
    dup_content = (
        "# Corporate Security Standard\n\n"
        "## 2. Onboarding Requirements\n"
        "All employees must complete security awareness training annually.\n\n"
        "## 8. Annual Compliance Checklist\n"
        "All employees must complete security awareness training annually.\n"
    )
    dup_path = output_dir / "duplicate_provisions.md"
    dup_path.write_text(dup_content, encoding="utf-8")

    manifest["fixtures"]["duplicate_text_different_locations"] = {
        "filename": "duplicate_provisions.md",
        "format": "md",
        "exact_duplicate_phrase": "All employees must complete security awareness training annually.",
        "expected_locations_count": 2,
        "must_preserve_both_locators": True,
        "expected_validation_status": "SUPPORTED",
    }

    # -------------------------------------------------------------------------
    # 16. Northwind Refund Handbook (northwind_handbook.md)
    # -------------------------------------------------------------------------
    northwind_content = (
        "# Northwind Refund and Return Policy\n\n"
        "## 6. Digital Goods\n"
        "All digital goods, downloadable software, and virtual licenses are non-refundable once delivered.\n\n"
        "## 6.1 Video Courses\n"
        "Video courses may be refunded within 7 days of purchase, provided less than 20% of the course has been viewed.\n\n"
        "## 7. Perishable Goods\n"
        "Perishable goods past 14 days are non-refundable, except if damaged upon delivery.\n\n"
        "## 8. Definitions\n"
        "High-value transactions are defined as orders exceeding $10,000 USD.\n"
    )
    nw_path = output_dir / "northwind_handbook.md"
    nw_path.write_text(northwind_content, encoding="utf-8")

    manifest["fixtures"]["northwind_handbook"] = {
        "filename": "northwind_handbook.md",
        "format": "md",
        "expected_candidate_claims": [
            {
                "subject": "All digital goods",
                "predicate": "are non-refundable",
                "object": "once delivered",
                "modality": "PROHIBITION",
                "expected_section": "6. Digital Goods",
                "validation_status": "SUPPORTED",
            },
            {
                "subject": "Video courses",
                "predicate": "has_refund_window",
                "object": "7 days of purchase",
                "conditions": ["less than 20% of the course has been viewed"],
                "modality": "PERMISSION",
                "expected_section": "6.1 Video Courses",
                "validation_status": "SUPPORTED",
                "must_not_link_to_section": "6. Digital Goods",
            },
            {
                "subject": "Perishable goods past 14 days",
                "predicate": "are non-refundable",
                "exceptions": ["damaged upon delivery"],
                "modality": "PROHIBITION",
                "expected_section": "7. Perishable Goods",
                "validation_status": "SUPPORTED",
            },
            {
                "subject": "High-value transactions",
                "predicate": "are defined as",
                "object": "orders exceeding $10,000 USD",
                "modality": "POLICY_FACT",
                "expected_section": "8. Definitions",
                "validation_status": "SUPPORTED",
            },
        ],
    }

    # -------------------------------------------------------------------------
    # 17. Conflicting source versions (conflicting_v1.md & conflicting_v2.md)
    # -------------------------------------------------------------------------
    v1_content = (
        "# Customer Service Policy v1.0\n\n"
        "## Returns\n"
        "Standard customer return window is 30 days from purchase.\n"
    )
    v2_content = (
        "# Customer Service Policy v2.0\n\n"
        "## Returns\n"
        "Standard customer return window is 14 days from purchase.\n"
    )
    (output_dir / "conflicting_v1.md").write_text(v1_content, encoding="utf-8")
    (output_dir / "conflicting_v2.md").write_text(v2_content, encoding="utf-8")

    manifest["fixtures"]["conflicting_versions"] = {
        "v1_file": "conflicting_v1.md",
        "v2_file": "conflicting_v2.md",
        "v1_version": "v1.0",
        "v2_version": "v2.0",
        "subject": "Standard customer return window",
        "v1_value": "30 days from purchase",
        "v2_value": "14 days from purchase",
        "distinct_candidate_preservation": True,
        "conflict_type": "TEMPORAL_SUPERSEDED_OR_CONTRADICTION",
    }

    # -------------------------------------------------------------------------
    # 18. Connector messages and structured payloads (slack_jira_connector.json)
    # -------------------------------------------------------------------------
    connector_payload = {
        "slack": {
            "channel_id": "C012345",
            "channel_name": "governance-announcements",
            "messages": [
                {
                    "message_id": "msg_001",
                    "user": "U9988",
                    "timestamp": "1700001000.000100",
                    "text": "Annual SOC2 audit begins on October 1st for all cloud infrastructure.",
                    "replies_count": 0,
                }
            ],
        },
        "jira": {
            "issue_key": "SEC-402",
            "summary": "Enforce AES-256 for all S3 buckets",
            "status": "In Progress",
            "priority": "High",
            "labels": ["compliance", "soc2"],
            "comments": [
                {"author": "lead_sec", "body": "Enforcement script is scheduled for execution."}
            ],
        },
    }
    connector_path = output_dir / "slack_jira_connector.json"
    connector_path.write_text(json.dumps(connector_payload, indent=2), encoding="utf-8")

    manifest["fixtures"]["connector_payload"] = {
        "filename": "slack_jira_connector.json",
        "format": "json",
        "connectors": ["slack", "jira"],
        "expected_candidate_claims": [
            {"subject": "Annual SOC2 audit", "predicate": "begins on", "object": "October 1st"},
            {"subject": "SEC-402", "predicate": "has_status", "object": "In Progress"},
        ],
        "expected_validation_status": "SUPPORTED",
    }

    # Write manifest.json
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    return manifest


if __name__ == "__main__":
    fixtures_dir = Path(__file__).resolve().parent
    m = generate_all_fixtures(fixtures_dir)
    print(f"Generated {len(m['fixtures'])} fixture definitions and manifest.json at {fixtures_dir}")

