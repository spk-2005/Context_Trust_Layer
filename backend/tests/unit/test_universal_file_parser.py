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
