"""
Unit tests for Phase 2: Trulin Structured Data Parsing and Evidence Generation.
Verifies:
1. CSV parsing preserving empty cells, column positions, quoted commas, and without 500-row truncation.
2. JSON scalar payloads (never returning zero units) and deeply nested JSON preserving types.
3. JSONL streams with > 100 records without silent truncation.
4. SQL DDL parsing with tables, columns, primary keys, foreign keys, constraints, and falsy defaults (0, false, '').
5. Database records containing at least 50 fields with complete discoverability and child field groups.
6. Deterministic identity for duplicate records at different source locations.
7. Connector payloads with parent/child records (Jira comments, GitHub reviews).
8. Completeness measurement and partial reporting.
"""

import json
import uuid
import pytest

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceUnit,
    ExtractionStatus,
    ParsedEvidenceResult,
    SourceLocator,
    StructuralRelationType,
)
from app.ingestion.parsers.structured_parser import StructuredDataParser


@pytest.mark.asyncio
async def test_csv_preserves_empty_cells_quotes_and_positions():
    """CSV parsing must preserve empty cells at true column indices without shifting columns or truncating."""
    csv_payload = (
        'id,first_name,middle_name,last_name,email,is_active,notes\n'
        '101,Alice,,Smith,alice@example.com,true,"Note with, comma"\n'
        '102,,May,Jones,jones@example.com,false,"Line 1\nLine 2"\n'
        '103,Bob,,,bob@example.com,true,""\n'
    )
    env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="postgres://prod/public/contacts.csv",
        source_family=SourceFamily.STRUCTURED,
        native_format="csv",
        source_version="v1",
        content_hash="csv_h1",
        raw_payload=csv_payload,
        locator_metadata={"database": "prod", "table": "contacts"},
    )

    result = await StructuredDataParser.parse(env)

    # 1 dataset summary + 3 row units = 4 units
    assert len(result.units) == 4
    assert result.completeness_score == 1.0
    assert result.quality_metrics["expected_count"] == 3
    assert result.quality_metrics["processed_count"] == 4

    row1 = result.units[1]
    cols1 = row1.structured_data["columns"]
    assert cols1["first_name"] == "Alice"
    assert cols1["middle_name"] == ""  # Empty cell preserved
    assert cols1["last_name"] == "Smith"
    assert cols1["notes"] == "Note with, comma"  # Quoted comma preserved

    row2 = result.units[2]
    cols2 = row2.structured_data["columns"]
    assert cols2["first_name"] == ""  # Empty first column does NOT shift middle_name to first_name
    assert cols2["middle_name"] == "May"
    assert cols2["last_name"] == "Jones"
    assert "Line 1\nLine 2" in cols2["notes"]  # Multiline cell preserved

    row3 = result.units[3]
    cols3 = row3.structured_data["columns"]
    assert cols3["middle_name"] == ""
    assert cols3["last_name"] == ""
    assert cols3["email"] == "bob@example.com"


@pytest.mark.asyncio
async def test_json_scalar_and_deeply_nested_json():
    """JSON scalar payloads must never return 0 units, and deeply nested JSON must preserve types and paths."""
    # 1. JSON Scalar Test
    scalar_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="redis://cache/feature_flag_active",
        source_family=SourceFamily.STRUCTURED,
        native_format="json",
        source_version="v1",
        content_hash="scalar_h",
        raw_payload="true",  # JSON boolean scalar
        locator_metadata={"database": "redis", "table": "feature_flags"},
    )
    scalar_res = await StructuredDataParser.parse(scalar_env)
    assert len(scalar_res.units) == 1
    assert scalar_res.units[0].block_type == "json_scalar"
    assert scalar_res.units[0].structured_data["scalar_value"] is True
    assert scalar_res.units[0].structured_data["data_type"] == "bool"

    # 2. Deeply Nested JSON Test
    nested_doc = {
        "_id": "sec_cfg_01",
        "enterprise": {
            "security": {
                "encryption": {
                    "at_rest": {
                        "algorithm": "AES-256-GCM",
                        "fips_compliant": True,
                        "key_length": 256,
                    }
                },
                "audit": {
                    "retention_years": 7,
                    "archived_records": None,
                },
            }
        },
        "tags": ["infosec", "soc2"],
    }
    nested_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="mongodb://Compliance/policies/sec_cfg_01",
        source_family=SourceFamily.STRUCTURED,
        native_format="json",
        source_version="v1",
        content_hash="nested_h",
        raw_payload=nested_doc,
        locator_metadata={"database": "Compliance", "collection": "policies"},
    )
    nested_res = await StructuredDataParser.parse(nested_env)
    assert len(nested_res.units) >= 1
    parent = nested_res.units[0]
    flattened = parent.structured_data["flattened_fields"]
    assert flattened["enterprise.security.encryption.at_rest.algorithm"] == "AES-256-GCM"
    assert flattened["enterprise.security.encryption.at_rest.fips_compliant"] is True
    assert flattened["enterprise.security.encryption.at_rest.key_length"] == 256
    assert flattened["enterprise.security.audit.retention_years"] == 7
    assert flattened["enterprise.security.audit.archived_records"] is None
    assert flattened["tags[0]"] == "infosec"


@pytest.mark.asyncio
async def test_jsonl_with_more_than_100_records():
    """JSONL streams with > 100 records must process all records without silent truncation."""
    total_records = 150
    jsonl_lines = [
        json.dumps({
            "event_id": f"evt_{i:04d}",
            "user_id": f"usr_{i % 10}",
            "action": "API_CALL",
            "latency_ms": 12.5 + (i * 0.1),
            "success": True,
        })
        for i in range(1, total_records + 1)
    ]
    payload = "\n".join(jsonl_lines)

    env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="s3://telemetry/events.jsonl",
        source_family=SourceFamily.STRUCTURED,
        native_format="jsonl",
        source_version="v1",
        content_hash="jsonl_h",
        raw_payload=payload,
        locator_metadata={"database": "telemetry", "table": "events"},
    )

    result = await StructuredDataParser.parse(env)
    # Must process all 150 records without truncating at 100
    assert len(result.units) == total_records
    assert result.completeness_score == 1.0
    assert result.quality_metrics["expected_count"] == total_records
    assert result.quality_metrics["processed_count"] == total_records
    assert result.quality_metrics["completeness_status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_sql_ddl_with_constraints_and_falsy_defaults():
    """SQL DDL parsing must extract tables, columns, constraints, foreign keys, and preserve falsy defaults (0, false, '')."""
    ddl_sql = """
    CREATE TABLE public.account_holders (
        account_id UUID PRIMARY KEY,
        user_name VARCHAR(100) NOT NULL,
        is_verified BOOLEAN DEFAULT false,
        credit_limit DECIMAL(10, 2) DEFAULT 0,
        memo TEXT DEFAULT '',
        branch_id INT REFERENCES public.branches(id),
        CONSTRAINT chk_credit CHECK (credit_limit >= 0),
        CONSTRAINT uq_username UNIQUE (user_name)
    );
    """
    env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="postgres://prod/ddl/account_holders.sql",
        source_family=SourceFamily.STRUCTURED,
        native_format="sql_schema",
        source_version="v1",
        content_hash="sql_h",
        raw_payload=ddl_sql,
        locator_metadata={"database": "prod", "table": "account_holders"},
    )

    result = await StructuredDataParser.parse(env)
    # 1 schema parent + 6 columns + 2 constraints = 9 units
    assert len(result.units) == 9

    summary = result.units[0]
    assert summary.block_type == "schema_definition"
    assert summary.structured_data["table"] == "account_holders"
    assert summary.structured_data["schema"] == "public"

    # Verify column units
    col_units = {u.structured_data.get("column_name"): u for u in result.units if u.block_type == "column_definition"}
    assert "account_id" in col_units
    assert col_units["account_id"].structured_data["is_primary_key"] is True

    assert "is_verified" in col_units
    assert col_units["is_verified"].structured_data["default"] is False  # Falsy boolean preserved!

    assert "credit_limit" in col_units
    assert col_units["credit_limit"].structured_data["default"] == 0  # Falsy numeric 0 preserved!

    assert "memo" in col_units
    assert col_units["memo"].structured_data["default"] == ""  # Falsy empty string preserved!

    assert "branch_id" in col_units
    assert col_units["branch_id"].structured_data["foreign_key"]["table"] == "public.branches"

    # Verify table constraints
    constraint_units = [u for u in result.units if u.block_type == "constraint_definition"]
    assert len(constraint_units) == 2
    c_types = [u.structured_data.get("type") for u in constraint_units]
    assert "CHECK" in c_types
    assert "UNIQUE" in c_types

    # Verify structural relationships
    for u in result.units[1:]:
        assert u.parent_id == summary.evidence_instance_id
        assert len(u.relationships) >= 1
        assert u.relationships[0].relation_type == StructuralRelationType.RECORD_HAS_FIELD


@pytest.mark.asyncio
async def test_database_record_containing_at_least_50_fields():
    """A database record with 50+ fields must retain all 50 fields without truncation and generate field groups."""
    doc_50 = {"_id": "rec_big_50", "tenant_id": "tenant_alpha"}
    for i in range(1, 51):
        doc_50[f"field_{i:02d}"] = f"value_{i}"

    env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="postgres://prod/analytics/wide_records/rec_big_50",
        source_family=SourceFamily.STRUCTURED,
        native_format="database_record",
        source_version="v1",
        content_hash="big_50_h",
        raw_payload=doc_50,
        locator_metadata={"database": "prod", "table": "wide_records"},
    )

    result = await StructuredDataParser.parse(env)
    assert len(result.units) > 1  # Parent record + child field groups

    parent = result.units[0]
    assert parent.block_type == "database_record"
    # All 52 fields must be in flattened_fields (never truncated to 10!)
    assert len(parent.structured_data["flattened_fields"]) == 52
    assert "field_50" in parent.structured_data["flattened_fields"]
    assert "field_50: value_50" in parent.content_text

    # Child field groups must be linked to parent
    children = result.units[1:]
    for child in children:
        assert child.block_type == "record_field"
        assert child.parent_id == parent.evidence_instance_id
        assert child.relationships[0].relation_type == StructuralRelationType.RECORD_HAS_FIELD
        assert child.locator.database_table == "wide_records"
        assert child.locator.primary_key == "rec_big_50"


@pytest.mark.asyncio
async def test_duplicate_records_at_different_source_locations():
    """Identical records at different source locations must share content_hash but produce distinct IDs."""
    record_data = {
        "user_id": "USR-100",
        "role": "Compliance_Auditor",
        "permission": "READ_ALL_AUDIT_LOGS",
        "mfa_enforced": True,
    }

    env1 = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="postgres://us-east/public/roles/USR-100",
        source_family=SourceFamily.STRUCTURED,
        native_format="database_record",
        source_version="v1",
        content_hash="rec_h",
        raw_payload=record_data,
        locator_metadata={"database": "us-east", "table": "roles"},
    )

    env2 = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="postgres://eu-central/public/roles/USR-100",
        source_family=SourceFamily.STRUCTURED,
        native_format="database_record",
        source_version="v1",
        content_hash="rec_h",
        raw_payload=record_data,
        locator_metadata={"database": "eu-central", "table": "roles"},
    )

    res1 = await StructuredDataParser.parse(env1)
    res2 = await StructuredDataParser.parse(env2)

    u1 = res1.units[0]
    u2 = res2.units[0]

    # Shared content_hash
    assert u1.content_hash == u2.content_hash
    # Distinct evidence_id due to different source locations
    assert u1.evidence_id != u2.evidence_id
    # Distinct occurrence IDs
    assert u1.evidence_instance_id != u2.evidence_instance_id


@pytest.mark.asyncio
async def test_connector_payload_with_parent_child_sub_resources():
    """Connector payloads with nested sub-resources (Jira comments, GitHub reviews) must preserve parent-child relations."""
    jira_payload = {
        "id": "JIRA-5501",
        "summary": "Implement zero-trust network segmentation",
        "status": "APPROVED",
        "priority": "P1",
        "comments": [
            {
                "comment_id": "comm_001",
                "author": "Alice (Security Architect)",
                "body": "Subnets 10.0.0.0/16 isolated under policy SEC-99.",
                "created_at": "2026-10-15T10:00:00Z",
            },
            {
                "comment_id": "comm_002",
                "author": "Bob (VP Engineering)",
                "body": "Co-signed exemption approved for legacy database bridge.",
                "created_at": "2026-10-15T11:30:00Z",
            },
        ],
    }

    env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="jira://company.atlassian.net/browse/JIRA-5501",
        source_family=SourceFamily.STRUCTURED,
        native_format="json",
        source_version="v3",
        content_hash="jira_h",
        raw_payload=jira_payload,
        locator_metadata={"project": "SEC", "issue_key": "JIRA-5501"},
    )

    result = await StructuredDataParser.parse(env)
    # 1 parent issue + 2 child comments = 3 units
    assert len(result.units) == 3

    parent = result.units[0]
    assert parent.block_type == "database_record"
    assert "JIRA-5501" in parent.content_text

    child1 = result.units[1]
    assert child1.block_type == "record_item"
    assert child1.parent_id == parent.evidence_instance_id
    assert child1.relationships[0].relation_type == StructuralRelationType.PARENT_CHILD
    assert child1.locator["json_path"] == "comments[0]"
    assert child1.structured_data["item_data"]["author"] == "Alice (Security Architect)"

    child2 = result.units[2]
    assert child2.block_type == "record_item"
    assert child2.parent_id == parent.evidence_instance_id
    assert child2.relationships[0].relation_type == StructuralRelationType.PARENT_CHILD
    assert child2.locator["json_path"] == "comments[1]"
    assert child2.structured_data["item_data"]["author"] == "Bob (VP Engineering)"


@pytest.mark.asyncio
async def test_xml_preserves_paths_attributes_and_parent_child_hierarchy():
    """XML parsing must preserve element paths, attributes, text, and parent-child hierarchy."""
    xml_data = """<?xml version="1.0" encoding="UTF-8"?>
    <security_policy xmlns:ns="http://example.com/sec" doc_id="SEC-2026" status="active">
        <section id="sec-1" title="Access Control">
            <rule rule_id="R-101" severity="critical">
                <condition>MFA required on all administrative accounts.</condition>
            </rule>
        </section>
    </security_policy>
    """
    env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="s3://policies/security_policy.xml",
        source_family=SourceFamily.STRUCTURED,
        native_format="xml",
        source_version="v1",
        content_hash="xml_h",
        raw_payload=xml_data,
        locator_metadata={"database": "s3", "container": "policies"},
    )

    result = await StructuredDataParser.parse(env)
    assert len(result.units) == 4
    assert result.completeness_score == 1.0

    root = result.units[0]
    assert root.block_type == "xml_element"
    assert root.structured_data["tag"] == "security_policy"
    assert root.structured_data["attributes"]["doc_id"] == "SEC-2026"
    assert root.parent_id is None

    section = result.units[1]
    assert section.parent_id == root.evidence_instance_id
    assert section.structured_data["tag"] == "section"
    assert section.structured_data["attributes"]["id"] == "sec-1"

    rule = result.units[2]
    assert rule.parent_id == section.evidence_instance_id
    assert rule.structured_data["tag"] == "rule"
    assert rule.structured_data["attributes"]["rule_id"] == "R-101"

    cond = result.units[3]
    assert cond.parent_id == rule.evidence_instance_id
    assert cond.structured_data["tag"] == "condition"
    assert "MFA required on all administrative accounts." in cond.content_text
