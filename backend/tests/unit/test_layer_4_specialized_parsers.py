"""
Unit tests for Layer 4: Specialized Source-Family Parsers.
Verifies DocumentParser, StructuredDataParser, ConversationParser, MetadataParser,
and their integration with Layer 3 CanonicalSourceEnvelope and Dispatcher.
"""

import uuid
import pytest
from datetime import datetime, timezone

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.dispatcher import (
    SourceEnvelopeRouter,
    TargetParserCategory,
    global_envelope_router,
)
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.parsers.conversation_parser import ConversationParser
from app.ingestion.parsers.metadata_parser import MetadataParser
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit


@pytest.mark.asyncio
async def test_layer_4_document_parser_headings_clauses_tables():
    """Verifies that DocumentParser extracts AST headings, clauses, and markdown tables with exact offsets."""
    markdown_doc = """# Enterprise Cloud Policy

## 1. Access Control
- All employees must enable MFA before accessing production.
- Section 1.2: Root credentials must be rotated every 90 days.

| Role | Access Tier | Approval Required |
| :--- | :--- | :--- |
| Developer | Staging | Team Lead |
| SRE Lead | Production | VP Engineering |

Paragraph text describing general guidelines.
"""
    envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="github://org/repo/policy.md",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="markdown",
        source_version="commit_sha_123",
        content_hash="abc_hash",
        raw_payload=markdown_doc,
        locator_metadata={"path": "policy.md", "repo": "org/repo"},
    )

    result = await DocumentParser.parse(envelope)

    assert isinstance(result, ParsedEvidenceResult)
    assert result.source_family == SourceFamily.DOCUMENT
    assert result.parser_name == "DocumentParser"
    assert len(result.units) > 0

    # Verify headings
    headings = [u for u in result.units if u.block_type == "heading"]
    assert len(headings) >= 2
    assert headings[0].content_text == "Enterprise Cloud Policy"
    assert headings[1].content_text == "1. Access Control"
    assert headings[1].hierarchical_context == ["Enterprise Cloud Policy", "1. Access Control"]

    # Verify clauses
    clauses = [u for u in result.units if u.block_type == "clause"]
    assert len(clauses) >= 2
    assert "MFA" in clauses[0].content_text
    assert "90 days" in clauses[1].content_text

    # Verify table rows
    table_rows = [u for u in result.units if u.block_type == "table_row"]
    assert len(table_rows) == 2
    assert table_rows[0].structured_data["columns"]["Role"] == "Developer"
    assert table_rows[1].structured_data["columns"]["Role"] == "SRE Lead"

    # Verify exact character offsets
    for u in result.units:
        assert "start_char" in u.locator
        assert "end_char" in u.locator
        assert u.locator["end_char"] >= u.locator["start_char"]


@pytest.mark.asyncio
async def test_layer_4_structured_parser_relational_and_bson():
    """Verifies that StructuredDataParser extracts schemas and individual JSON/BSON records with nested paths."""
    # 1. SQL Schema Test
    schema_payload = {
        "columns": [
            {"column_name": "user_id", "data_type": "uuid", "is_nullable": False},
            {"column_name": "email", "data_type": "varchar(255)", "is_nullable": False},
            {"column_name": "is_active", "data_type": "boolean", "column_default": True},
        ]
    }
    schema_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="postgres://prod_db/public/users",
        source_family=SourceFamily.STRUCTURED,
        source_intent=SourceIntent.OPERATIONAL_DATA,
        native_format="sql_schema",
        source_version="1",
        content_hash="schema_hash",
        raw_payload=schema_payload,
        locator_metadata={"database": "prod_db", "table": "users"},
    )

    schema_result = await StructuredDataParser.parse(schema_env)
    assert len(schema_result.units) == 4  # 1 schema summary + 3 column units
    assert schema_result.units[0].block_type == "schema_definition"
    assert schema_result.units[1].block_type == "column_definition"
    assert schema_result.units[1].structured_data["column_name"] == "user_id"

    # 2. MongoDB BSON Document Test with nested paths
    bson_doc = {
        "_id": "67074b1e5a1b3c0012345678",
        "policy_id": "SEC-MONGO-01",
        "security": {
            "encryption": "AES-256-GCM",
            "key_rotation_days": 90,
            "enforce_tls": True,
        },
        "tags": ["prod", "compliance"],
    }
    bson_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="mongodb://Departmental/security_configs/67074b1e5a1b3c0012345678",
        source_family=SourceFamily.STRUCTURED,
        source_intent=SourceIntent.OPERATIONAL_DATA,
        native_format="json",
        source_version="1",
        content_hash="bson_hash",
        raw_payload=bson_doc,
        locator_metadata={"database": "Departmental", "collection": "security_configs"},
    )

    bson_result = await StructuredDataParser.parse(bson_env)
    assert len(bson_result.units) == 1
    unit = bson_result.units[0]
    assert unit.block_type == "database_record"
    assert unit.structured_data["record_id"] == "67074b1e5a1b3c0012345678"
    assert unit.structured_data["flattened_fields"]["security.encryption"] == "AES-256-GCM"
    assert unit.structured_data["flattened_fields"]["security.key_rotation_days"] == 90
    assert unit.structured_data["flattened_fields"]["tags[0]"] == "prod"


@pytest.mark.asyncio
async def test_layer_4_conversation_parser_slack_and_jira():
    """Verifies that ConversationParser preserves reply hierarchy, speakers, and temporal order."""
    chat_thread = [
        {
            "id": "msg_001",
            "speaker": "Alice (VP Eng)",
            "text": "Can we approve the Sev-1 hotfix deployment during change freeze?",
            "timestamp": "2026-10-10T16:05:00Z",
            "parent_id": None,
        },
        {
            "id": "msg_002",
            "speaker": "Bob (SRE Lead)",
            "text": "Yes, co-signing the exemption rule SEC-902 under emergency mandate v2.0.",
            "timestamp": "2026-10-10T16:07:00Z",
            "parent_id": "msg_001",
        },
    ]

    conv_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="slack://ops-war-room/thread/msg_001",
        source_family=SourceFamily.CONVERSATION,
        source_intent=SourceIntent.PROPOSALS_DISCUSSIONS,
        native_format="chat_thread",
        source_version="1",
        content_hash="chat_hash",
        raw_payload=chat_thread,
        locator_metadata={"channel": "ops-war-room", "thread_id": "msg_001"},
    )

    conv_result = await ConversationParser.parse(conv_env)
    assert len(conv_result.units) == 2
    assert conv_result.units[0].structured_data["speaker"] == "Alice (VP Eng)"
    assert conv_result.units[1].structured_data["speaker"] == "Bob (SRE Lead)"
    assert conv_result.units[1].structured_data["parent_id"] == "msg_001"
    assert conv_result.quality_metrics["speakers_detected"] == 2


@pytest.mark.asyncio
async def test_layer_4_metadata_parser_bi_and_lineage():
    """Verifies that MetadataParser extracts BI metrics, calculation formulae, and lineage DAG dependencies."""
    bi_model = {
        "metrics": [
            {
                "name": "daily_active_users",
                "formula": "COUNT(DISTINCT user_id) WHERE active = true",
                "description": "Daily unique authenticated users",
            },
            {
                "name": "churn_rate_pct",
                "formula": "churned_users / total_users * 100",
                "description": "30-day trailing customer churn rate",
            },
        ]
    }

    meta_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="dbt://analytics/models/user_metrics.yml",
        source_family=SourceFamily.METADATA,
        source_intent=SourceIntent.ANALYTICS_METRIC,
        native_format="bi_model",
        source_version="1",
        content_hash="bi_hash",
        raw_payload=bi_model,
        locator_metadata={"model": "user_metrics"},
    )

    meta_result = await MetadataParser.parse(meta_env)
    assert len(meta_result.units) == 2
    assert meta_result.units[0].block_type == "metric_definition"
    assert meta_result.units[0].structured_data["name"] == "daily_active_users"
    assert "COUNT(DISTINCT user_id)" in meta_result.units[0].content_text


@pytest.mark.asyncio
async def test_layer_3_and_4_end_to_end_router_dispatch():
    """Verifies that global_envelope_router automatically routes and executes Layer 4 parsers."""
    # Document envelope
    doc_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="github://repo/main/secops.md",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="markdown",
        source_version="1",
        content_hash="h1",
        raw_payload="# Security Policy\n- Mandatory AES-256 encryption.",
        locator_metadata={"path": "secops.md"},
    )

    # Structured envelope
    struct_env = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="mongodb://Departmental/security_configs/doc1",
        source_family=SourceFamily.STRUCTURED,
        source_intent=SourceIntent.OPERATIONAL_DATA,
        native_format="json",
        source_version="1",
        content_hash="h2",
        raw_payload={"_id": "doc1", "encryption": "AES-256-GCM"},
        locator_metadata={"database": "Departmental", "collection": "security_configs"},
    )

    batch_output = await global_envelope_router.batch_dispatch([doc_env, struct_env])

    assert batch_output["total_envelopes"] == 2
    assert len(batch_output["results"]) == 2
    assert batch_output["routing_decisions"][0]["target_parser"] == "documents_and_files"
    assert batch_output["routing_decisions"][1]["target_parser"] == "structured_data"

    # Verify that results are full ParsedEvidenceResult dicts with units
    doc_res = batch_output["results"][0]
    struct_res = batch_output["results"][1]

    assert doc_res["parser_name"] == "DocumentParser"
    assert len(doc_res["units"]) >= 1
    assert struct_res["parser_name"] == "StructuredDataParser"
    assert len(struct_res["units"]) == 1
    assert struct_res["units"][0]["structured_data"]["record_id"] == "doc1"
