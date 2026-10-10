import uuid
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.connector_registry import (
    ConnectorRegistry,
    resolve_source_family,
    get_default_intent,
    get_default_capabilities,
)
from app.schemas.source_scope import (
    DocumentScopeConfig,
    StructuredScopeConfig,
    ConversationScopeConfig,
    MetadataScopeConfig,
    SourceCapabilities,
    ScopeConfiguration,
)
from app.ingestion.connectors.postgres_connector import PostgresConnector
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.connectors.github_connector import GitHubConnector
from app.main import app


def test_source_family_classification():
    """Verify Layer 1 properly classifies heterogeneous connectors into distinct Source Families."""
    # Documents
    assert resolve_source_family("file") == SourceFamily.DOCUMENT
    assert resolve_source_family("manual_upload") == SourceFamily.DOCUMENT
    assert resolve_source_family("pdf") == SourceFamily.DOCUMENT
    assert resolve_source_family("markdown") == SourceFamily.DOCUMENT
    assert resolve_source_family("github") == SourceFamily.DOCUMENT
    assert resolve_source_family("confluence") == SourceFamily.DOCUMENT

    # Structured Data (matches both Layer 2 and Layer 1 names)
    assert resolve_source_family("postgresql") == SourceFamily.STRUCTURED
    assert resolve_source_family("postgresql") == SourceFamily.STRUCTURED_DATA
    assert resolve_source_family("postgres") == SourceFamily.STRUCTURED
    assert resolve_source_family("mongodb") == SourceFamily.STRUCTURED
    assert resolve_source_family("mysql") == SourceFamily.STRUCTURED
    assert resolve_source_family("snowflake") == SourceFamily.STRUCTURED

    # Conversations
    assert resolve_source_family("slack") == SourceFamily.CONVERSATION
    assert resolve_source_family("teams") == SourceFamily.CONVERSATION
    assert resolve_source_family("jira") == SourceFamily.CONVERSATION

    # Metadata & Operational (matches both Layer 2 and Layer 1 names)
    assert resolve_source_family("tableau") == SourceFamily.METADATA
    assert resolve_source_family("tableau") == SourceFamily.METADATA_OPERATIONAL
    assert resolve_source_family("power_bi") == SourceFamily.METADATA
    assert resolve_source_family("lineage") == SourceFamily.METADATA
    assert resolve_source_family("kafka") == SourceFamily.METADATA


def test_source_intent_classification():
    """Verify Layer 1 assigns correct semantic intent to avoid misinterpreting operational facts as policies."""
    assert get_default_intent("github") == SourceIntent.GOVERNANCE_POLICY
    assert get_default_intent("confluence") == SourceIntent.GOVERNANCE_POLICY
    assert get_default_intent("postgresql") == SourceIntent.OPERATIONAL_DATA
    assert get_default_intent("mongodb") == SourceIntent.OPERATIONAL_DATA
    assert get_default_intent("slack") == SourceIntent.PROPOSALS_DISCUSSIONS
    assert get_default_intent("tableau") == SourceIntent.ANALYTICS_METRIC


def test_source_capabilities_flags():
    """Verify Layer 1 connectors declare precise capabilities for incremental sync and discovery."""
    pg_caps = get_default_capabilities("postgresql")
    assert pg_caps["supports_incremental"] is True
    assert pg_caps["supports_schema_discovery"] is True
    assert pg_caps["pagination_type"] == "cursor"
    assert pg_caps["native_identifier_field"] == "primary_key"

    doc_caps = get_default_capabilities("github")
    assert doc_caps["supports_granular_selection"] is True
    assert doc_caps["pagination_type"] == "none"

    chat_caps = get_default_capabilities("slack")
    assert chat_caps["pagination_type"] == "page"


def test_typed_scope_configurations():
    """Verify Layer 1 scoped configurations reject invalid data and correctly structure scopes."""
    doc_scope = DocumentScopeConfig(
        file_globs=["**/*.md"],
        excluded_paths=["test/**"],
        max_file_size_mb=25,
    )
    assert doc_scope.max_file_size_mb == 25
    assert "**/*.md" in doc_scope.file_globs

    struct_scope = StructuredScopeConfig(
        database="production",
        schemas=["public", "analytics"],
        selected_entities=["expense_policies", "reimbursement_limits"],
        filter_predicates={"expense_policies": "active = true"},
    )
    assert struct_scope.database == "production"
    assert "expense_policies" in struct_scope.selected_entities
    assert struct_scope.extract_mode == "schema_and_records"

    scope_container = ScopeConfiguration(
        source_family=SourceFamily.STRUCTURED_DATA,
        source_intent=SourceIntent.OPERATIONAL_DATA,
        structured_scope=struct_scope,
    )
    assert scope_container.source_family == SourceFamily.STRUCTURED_DATA
    assert scope_container.structured_scope.database == "production"


@pytest.mark.anyio
async def test_connector_inventory_discovery_hooks():
    """Verify connector instances expose their source family and discovery inventory interface."""
    dummy_session = AsyncMock()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    # 1. PostgreSQL connector
    pg_conn = PostgresConnector(
        session=dummy_session,
        organization_id=org_id,
        source_id=src_id,
        host="localhost",
        database="testdb",
    )
    assert pg_conn.source_family == SourceFamily.STRUCTURED_DATA
    assert pg_conn.capabilities["supports_schema_discovery"] is True

    # 2. MongoDB connector
    mongo_conn = MongoDbConnector(
        session=dummy_session,
        organization_id=org_id,
        source_id=src_id,
        database="test_mongo",
    )
    assert mongo_conn.source_family == SourceFamily.STRUCTURED_DATA
    assert mongo_conn.capabilities["native_identifier_field"] == "_id"

    # 3. GitHub connector
    gh_conn = GitHubConnector(
        session=dummy_session,
        organization_id=org_id,
        source_id=src_id,
        repo="org/policies",
    )
    assert gh_conn.source_family == SourceFamily.DOCUMENT
    assert gh_conn.source_intent == SourceIntent.GOVERNANCE_POLICY


@pytest.mark.anyio
async def test_layer1_source_creation_and_scoping_api():
    """Verify Layer 1 API accepts source_family, intent, scope_config, and discovers inventory."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Create a new data source with explicit Layer 1 classification
        payload = {
            "name": "Live HR Postgres Database",
            "source_type": "postgresql",
            "source_family": "structured_data",
            "source_intent": "governance_policy",
            "authority_level": 90,
            "connection_config": {
                "host": "localhost",
                "port": 5432,
                "database": "hr_prod",
                "username": "hr_admin",
                "test_passed": True,
            },
            "scope_config": {
                "schemas": ["public"],
                "selected_entities": ["expense_policies", "leave_guidelines"],
            },
        }
        res = await client.post("/v1/sources", json=payload)
        assert res.status_code in (200, 201)
        data = res.json()
        assert data["source_family"] in ("structured", "structured_data")
        assert data["source_intent"] == "governance_policy"
        assert data["scope_config"]["selected_entities"] == ["expense_policies", "leave_guidelines"]
        source_id = data["id"]

        # Update scope via /scope endpoint
        scope_update = {
            "schemas": ["public", "compliance"],
            "selected_entities": ["expense_policies", "anti_corruption_rules"],
        }
        res_scope = await client.post(f"/v1/sources/{source_id}/scope", json=scope_update)
        assert res_scope.status_code == 200
        updated = res_scope.json()
        assert updated["scope_config"]["schemas"] == ["public", "compliance"]

        # Call Layer 1 inventory endpoint
        res_inv = await client.get(f"/v1/sources/{source_id}/inventory")
        assert res_inv.status_code == 200
        inv_data = res_inv.json()
        assert inv_data["source_type"] == "postgresql"
        assert inv_data["source_family"] in ("structured", "structured_data")
        assert "items" in inv_data

        # Call Layer 2 discover-assets endpoint
        res_assets = await client.get(f"/v1/sources/{source_id}/discover-assets")
        assert res_assets.status_code == 200
        assets_data = res_assets.json()
        assert assets_data["source_type"] == "postgresql"
        assert "assets" in assets_data

        # Call Layer 2 select-assets endpoint
        res_sel = await client.post(
            f"/v1/sources/{source_id}/select-assets",
            json={"selected_asset_ids": ["public.expense_policies", "public.leave_guidelines"]}
        )
        assert res_sel.status_code == 200
        sel_data = res_sel.json()
        assert sel_data["scope_config"]["selected_assets"] == ["public.expense_policies", "public.leave_guidelines"]


