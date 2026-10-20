import pytest
from app.ingestion.universal_file_parser import UniversalFileParser


def test_parse_csv_tabular_file():
    csv_bytes = b"Tier,Discount,SLA\nEnterprise,20%,99.99%\nStandard,5%,99.5%"
    text = UniversalFileParser.parse_file("pricing_matrix.csv", csv_bytes, "Pricing Matrix")
    assert "Pricing Matrix" in text
    assert "| Enterprise | 20% | 99.99% |" in text
    assert "---" in text


def test_parse_json_file():
    json_bytes = b'{"service": "auth", "port": 8080, "mtls_enabled": true}'
    text = UniversalFileParser.parse_file("config.json", json_bytes, "Auth Config")
    assert "Auth Config" in text
    assert "mtls_enabled" in text
    assert "```json" in text


def test_parse_html_file():
    html_bytes = b"<html><head><title>Test</title><script>var x = 1;</script></head><body><h1>Security Mandate</h1><p>All endpoints must enforce TLS 1.3.</p></body></html>"
    text = UniversalFileParser.parse_file("security.html", html_bytes, "Security Mandate")
    assert "Security Mandate" in text
    assert "All endpoints must enforce TLS 1.3." in text
    assert "var x = 1" not in text


def test_parse_xml_file():
    xml_bytes = b"<root><policy><name>RefundPolicy</name><days>60</days></policy></root>"
    text = UniversalFileParser.parse_file("policy.xml", xml_bytes, "XML Policy")
    assert "RefundPolicy" in text
    assert "60" in text


def test_parse_yaml_and_config_file():
    yaml_bytes = b"server:\n  port: 443\n  ssl: true\n"
    text = UniversalFileParser.parse_file("application.yaml", yaml_bytes, "App Config")
    assert "App Config" in text
    assert "```yaml" in text
    assert "ssl: true" in text


def test_parse_plain_text_with_null_bytes():
    raw_bytes = "Employee Handbook\x00 with hidden null bytes and unicode \u2014 rules.".encode("utf-8")
    text = UniversalFileParser.parse_file("handbook.txt", raw_bytes, "Handbook")
    assert "\x00" not in text
    assert "Employee Handbook" in text


def test_repair_ocr_text_segmentation():
    from app.ingestion.universal_file_parser import repair_ocr_text
    raw = "Startforfree Terms of Service TABLEOFCONTENTS next30days"
    repaired = repair_ocr_text(raw)
    assert "TABLE OF CONTENTS" in repaired or "TABLEOFCONTENTS" in repaired
    assert "30 days" in repaired or "next 30 days" in repaired


def test_parse_pdf_structured_and_blocks():
    import pymupdf
    # Create an in-memory PDF with 2 pages
    doc = pymupdf.open()
    p1 = doc.new_page()
    p1.insert_text((50, 72), "1. Account Terms\nAll users must provide a valid email address.")
    p2 = doc.new_page()
    p2.insert_text((50, 72), "2. Payment of Fees\nMonthly fees must be paid within 14 days.")
    pdf_bytes = doc.tobytes()
    doc.close()

    parsed = UniversalFileParser.parse_structured("contract.pdf", pdf_bytes, "Test Contract")
    assert parsed.title == "Test Contract"
    assert len(parsed.pages) == 2
    assert parsed.pages[0].page_number == 1
    assert parsed.pages[1].page_number == 2
    assert "Account Terms" in parsed.full_text
    assert "Payment of Fees" in parsed.full_text
    assert parsed.extraction_quality >= 0.8
    assert len(parsed.blocks) >= 2

