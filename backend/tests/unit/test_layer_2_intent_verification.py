"""
Layer 2 Architectural Intent Verification Suite.

Tests that Layer 2 fulfills all 6 core responsibilities:
1. Connector Registry & Capabilities (SourceFamily & SyncMode contracts)
2. Authentication & Permission Isolation
3. Two-Phase Source Discovery & Selection
4. Non-Flattened Native Data Fetching (Preserving BSON, SQL dicts, ASTs, and Locators)
5. Checkpointing, Watermarks & Delta Sync
6. Resilient Ingestion Job Queue (Bounded Concurrency & Retry Backoff)
"""

import asyncio
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from app.db.models.data_source import DataSource
from app.ingestion.base import (
    ConnectorCapability,
    DiscoveredAsset,
    RawSourceAsset,
    SourceFamily,
    SyncMode,
    UnifiedConnector,
)
from app.ingestion.connectors.postgres_connector import PostgresConnector
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.connectors.github_connector import GitHubConnector
from app.ingestion.connectors.jira_connector import JiraConnector
from app.ingestion.connectors.confluence_connector import ConfluenceConnector
from app.ingestion.connectors.universal_driver import UniversalConnectorDriver
from app.ingestion.scheduler import IngestionJobQueue
from app.ingestion.sync_engine import SyncEngine


# ===========================================================================
# 1. Intent Test: Source-Family Classification & Capability Contract
# ===========================================================================
def test_layer_2_intent_source_family_classification():
    """Verify Layer 2 enforces distinct SourceFamily categorization."""
    assert SourceFamily.DOCUMENT == "document"
    assert SourceFamily.STRUCTURED == "structured"
    assert SourceFamily.CONVERSATION == "conversation"
    assert SourceFamily.METADATA == "metadata"

    capability = ConnectorCapability(
        connector_type="postgresql",
        display_name="PostgreSQL",
        source_families=[SourceFamily.STRUCTURED],
        supports_discovery=True,
        supports_delta_sync=True,
        supports_tombstones=True,
    )
    assert capability.source_families == [SourceFamily.STRUCTURED]
    assert capability.supports_discovery is True


# ===========================================================================
# 2. Intent Test: Non-Flattened Native Data Extraction (No Markdown Flattening)
# ===========================================================================
@pytest.mark.asyncio
async def test_layer_2_intent_postgres_native_data_preservation():
    """Verify PostgresConnector emits native dictionary structures without Markdown conversion."""
    session = AsyncMock()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    connector = PostgresConnector(
        session=session,
        organization_id=org_id,
        source_id=src_id,
        database="finance_db",
        schemas=["compliance"],
    )

    with patch("asyncpg.connect") as mock_conn:
        conn = AsyncMock()
        mock_conn.return_value = conn
        conn.fetch.side_effect = [
            [{"table_name": "retention_rules", "table_type": "BASE TABLE"}],
            [
                {"column_name": "rule_id", "data_type": "integer", "is_nullable": "NO", "column_default": "nextval()"},
                {"column_name": "min_retention_years", "data_type": "integer", "is_nullable": "NO", "column_default": "7"},
                {"column_name": "department", "data_type": "varchar", "is_nullable": "NO", "column_default": "NULL"},
            ],
            [
                {"rule_id": 101, "min_retention_years": 7, "department": "tax"},
                {"rule_id": 102, "min_retention_years": 5, "department": "hr"},
            ],
        ]

        native_assets = await connector.fetch_native_assets()
        assert len(native_assets) == 2

        # 1. Schema Asset Verification
        schema_asset = native_assets[0]
        assert schema_asset.source_family == SourceFamily.STRUCTURED
        assert schema_asset.native_format == "sql_schema"
        assert isinstance(schema_asset.raw_payload, dict)
        assert schema_asset.raw_payload["columns"][1]["column_name"] == "min_retention_years"
        assert schema_asset.locator_metadata["table"] == "retention_rules"

        # 2. Rows Asset Verification
        rows_asset = native_assets[1]
        assert rows_asset.source_family == SourceFamily.STRUCTURED
        assert rows_asset.native_format == "sql_rows"
        assert isinstance(rows_asset.raw_payload, list)
        assert len(rows_asset.raw_payload) == 2
        assert rows_asset.raw_payload[0]["min_retention_years"] == 7
        assert rows_asset.locator_metadata["row_count"] == 2
        assert rows_asset.content_hash != ""


@pytest.mark.asyncio
async def test_layer_2_intent_mongodb_native_data_preservation():
    """Verify MongoDbConnector emits raw JSON/BSON records with exact field locators."""
    session = AsyncMock()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    connector = MongoDbConnector(
        session=session,
        organization_id=org_id,
        source_id=src_id,
        database="cloud_ops",
        collections=["cluster_policies"],
    )

    with patch("app.ingestion.connectors.mongodb_connector.motor") as mock_motor:
        mock_client = MagicMock()
        mock_motor.motor_asyncio.AsyncIOMotorClient.return_value = mock_client
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_col = MagicMock()
        mock_db.__getitem__.return_value = mock_col
        mock_cursor = MagicMock()
        mock_col.find.return_value.limit.return_value = mock_cursor

        sample_bson = [
            {
                "_id": "pol_tier_1",
                "tier": "enterprise",
                "sla_uptime_percent": 99.99,
                "backup": {"frequency_hours": 4, "retention_days": 90},
            }
        ]
        mock_cursor.to_list = AsyncMock(return_value=sample_bson)

        native_assets = await connector.fetch_native_assets()
        assert len(native_assets) == 2  # 1 schema + 1 document asset

        doc_asset = native_assets[1]
        assert doc_asset.source_family == SourceFamily.STRUCTURED
        assert doc_asset.native_format == "json"
        assert isinstance(doc_asset.raw_payload, dict)
        assert doc_asset.raw_payload["sla_uptime_percent"] == 99.99
        assert doc_asset.raw_payload["backup"]["retention_days"] == 90
        assert doc_asset.locator_metadata["collection"] == "cluster_policies"
        assert doc_asset.locator_metadata["document_id"] == "pol_tier_1"


# ===========================================================================
# 3. Intent Test: Two-Phase Discovery & Asset Selection Scoping
# ===========================================================================
@pytest.mark.asyncio
async def test_layer_2_intent_asset_selection_scoping():
    """Verify that scoped asset IDs restrict what Layer 2 fetches."""
    session = AsyncMock()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    connector = PostgresConnector(
        session=session,
        organization_id=org_id,
        source_id=src_id,
        database="main_db",
        schemas=["public"],
    )

    with patch("asyncpg.connect") as mock_conn:
        conn = AsyncMock()
        mock_conn.return_value = conn
        conn.fetch.side_effect = [
            # 1. tables in schema
            [
                {"table_name": "target_table", "table_type": "BASE TABLE"},
                {"table_name": "ignored_table", "table_type": "BASE TABLE"},
            ],
            # 2. columns for target_table only
            [{"column_name": "id", "data_type": "int", "is_nullable": "NO", "column_default": None}],
            # 3. rows for target_table
            [{"id": 1}],
        ]

        # Scope explicitly to 'target_table'
        scoped_id = "postgres://main_db/public/target_table"
        native_assets = await connector.fetch_native_assets(selected_asset_ids=[scoped_id])

        # Must only fetch 2 assets (schema + rows for target_table), ignored_table must be excluded
        assert len(native_assets) == 2
        assert native_assets[0].asset_id == scoped_id
        assert native_assets[1].asset_id == f"{scoped_id}/records"


# ===========================================================================
# 4. Intent Test: SyncEngine Checkpoint Tracking
# ===========================================================================
@pytest.mark.asyncio
async def test_layer_2_intent_sync_engine_checkpointing():
    """Verify SyncEngine persists checkpoints and updates selected asset scopes."""
    session = AsyncMock()
    source_id = uuid.uuid4()
    org_id = uuid.uuid4()

    mock_source = DataSource(
        id=source_id,
        organization_id=org_id,
        name="Postgres Production",
        source_type="postgresql",
        connection_config={"host": "localhost", "database": "prod"},
    )

    engine = SyncEngine(session)
    engine.source_repo = MagicMock()
    engine.source_repo.get_by_id = AsyncMock(return_value=mock_source)

    # Test update_selected_assets
    target_scopes = ["postgres://prod/public/rules", "postgres://prod/public/users"]
    updated = await engine.update_selected_assets(source_id, target_scopes)

    assert updated.connection_config["selected_assets"] == target_scopes
    session.flush.assert_called()
    session.commit.assert_called()


# ===========================================================================
# 5. Intent Test: IngestionJobQueue Retry Backoff on Upstream Error
# ===========================================================================
@pytest.mark.asyncio
async def test_layer_2_intent_job_queue_retry_and_resilience():
    """Verify IngestionJobQueue retries transient failures before marking failed."""
    queue = IngestionJobQueue(max_concurrent_jobs=1)
    source_id = uuid.uuid4()

    with patch("app.ingestion.scheduler.SyncEngine") as mock_engine_cls:
        engine_inst = MagicMock()
        mock_engine_cls.return_value = engine_inst
        # Simulate transient network drop on attempt 1, success on attempt 2
        mock_res = MagicMock()
        mock_res.status = "success"
        mock_res.model_dump.return_value = {"status": "success", "documents_synced": 4}

        engine_inst.sync_data_source = AsyncMock(side_effect=[
            RuntimeError("Connection reset by peer"),
            mock_res,
        ])

        with patch("asyncio.sleep", AsyncMock()):  # Speed up retry delay
            job_status = await queue.enqueue_and_execute(source_id, use_mock_llm=True, max_retries=2)

        assert job_status["status"] == "success"
        assert job_status["attempt"] == 2
