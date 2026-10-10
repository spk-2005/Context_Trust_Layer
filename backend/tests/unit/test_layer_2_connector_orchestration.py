import asyncio
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

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


@pytest.mark.unit
def test_layer_2_models_and_contracts():
    # 1. RawSourceAsset creation and automatic hash derivation
    payload = {"policy_id": "pol_101", "submission_days": 30, "group": "all"}
    asset = RawSourceAsset(
        asset_id="mongodb://production/policies/pol_101",
        source_family=SourceFamily.STRUCTURED,
        native_format="json",
        source_version="v1",
        raw_payload=payload,
        locator_metadata={"database": "production", "collection": "policies", "doc_id": "pol_101"},
    )
    assert asset.content_hash != ""
    assert asset.source_family == SourceFamily.STRUCTURED
    assert asset.is_deleted is False

    # 2. DiscoveredAsset structure
    discovered = DiscoveredAsset(
        asset_id="postgres://main/public/employees",
        name="public.employees",
        asset_type="table",
        source_family=SourceFamily.STRUCTURED,
        parent_id="postgres://main/public",
        metadata={"row_count_estimate": 5000},
    )
    assert discovered.name == "public.employees"
    assert discovered.source_family == SourceFamily.STRUCTURED


@pytest.mark.asyncio
async def test_postgres_connector_layer_2_discovery():
    session = AsyncMock()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    connector = PostgresConnector(
        session=session,
        organization_id=org_id,
        source_id=src_id,
        host="localhost",
        database="test_db",
        schemas=["public"],
    )

    with patch("asyncpg.connect") as mock_conn:
        conn_instance = AsyncMock()
        mock_conn.return_value = conn_instance
        conn_instance.fetch.return_value = [
            {"table_name": "policies", "table_type": "BASE TABLE"},
            {"table_name": "user_view", "table_type": "VIEW"},
        ]

        assets = await connector.discover_assets()
        assert len(assets) == 2
        assert assets[0].name == "public.policies"
        assert assets[0].asset_type == "table"
        assert assets[0].source_family == SourceFamily.STRUCTURED
        assert assets[1].asset_type == "view"


@pytest.mark.asyncio
async def test_postgres_connector_native_asset_fetching():
    session = AsyncMock()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    connector = PostgresConnector(
        session=session,
        organization_id=org_id,
        source_id=src_id,
        host="localhost",
        database="test_db",
        schemas=["public"],
    )

    with patch("asyncpg.connect") as mock_conn:
        conn_instance = AsyncMock()
        mock_conn.return_value = conn_instance
        # 1. tables query
        # 2. columns query
        # 3. select records query
        conn_instance.fetch.side_effect = [
            [{"table_name": "expense_rules", "table_type": "BASE TABLE"}],
            [
                {"column_name": "id", "data_type": "integer", "is_nullable": "NO", "column_default": "nextval()"},
                {"column_name": "max_amount", "data_type": "numeric", "is_nullable": "NO", "column_default": "500"},
            ],
            [
                {"id": 1, "max_amount": 500, "category": "travel"},
            ],
        ]

        native_assets = await connector.fetch_native_assets()
        assert len(native_assets) == 2
        # Schema asset
        assert native_assets[0].native_format == "sql_schema"
        assert native_assets[0].raw_payload["table_name"] == "expense_rules"
        assert len(native_assets[0].raw_payload["columns"]) == 2
        # Records asset
        assert native_assets[1].native_format == "sql_rows"
        assert len(native_assets[1].raw_payload) == 1
        assert native_assets[1].locator_metadata["table"] == "expense_rules"


@pytest.mark.asyncio
async def test_mongodb_connector_layer_2_discovery_and_fetch():
    session = AsyncMock()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    connector = MongoDbConnector(
        session=session,
        organization_id=org_id,
        source_id=src_id,
        connection_string="mongodb://localhost:27017",
        database="ops_catalog",
        collections=["billing_rules"],
    )

    with patch("app.ingestion.connectors.mongodb_connector.motor") as mock_motor:
        mock_client = MagicMock()
        mock_motor.motor_asyncio.AsyncIOMotorClient.return_value = mock_client
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        mock_db.list_collection_names = AsyncMock(return_value=["billing_rules", "system.views"])

        # Test Discovery
        discovered = await connector.discover_assets()
        assert len(discovered) == 1
        assert discovered[0].name == "ops_catalog.billing_rules"
        assert discovered[0].source_family == SourceFamily.STRUCTURED

        # Test Native Fetch
        mock_col = MagicMock()
        mock_db.__getitem__.return_value = mock_col
        mock_cursor = MagicMock()
        mock_col.find.return_value.limit.return_value = mock_cursor
        mock_cursor.to_list = AsyncMock(return_value=[
            {"_id": "rec_001", "grace_period_days": 14, "auto_renew": True}
        ])

        native_assets = await connector.fetch_native_assets()
        assert len(native_assets) == 2  # 1 schema asset + 1 document asset
        assert native_assets[0].native_format == "json_schema"
        assert native_assets[1].native_format == "json"
        assert native_assets[1].raw_payload["grace_period_days"] == 14
        assert native_assets[1].locator_metadata["document_id"] == "rec_001"


@pytest.mark.asyncio
async def test_github_connector_layer_2_discovery_and_fetch():
    session = AsyncMock()
    org_id = uuid.uuid4()
    src_id = uuid.uuid4()

    connector = GitHubConnector(
        session=session,
        organization_id=org_id,
        source_id=src_id,
        repo="acme-corp/secops-standards",
        branch="main",
    )

    with patch("httpx.AsyncClient.get") as mock_get:
        tree_resp = MagicMock()
        tree_resp.status_code = 200
        tree_resp.json.return_value = {
            "tree": [
                {"path": "policies/expense_policy.md", "type": "blob", "sha": "sha_111", "size": 1200},
                {"path": "config/service_tiers.json", "type": "blob", "sha": "sha_222", "size": 800},
            ]
        }
        raw_resp = MagicMock()
        raw_resp.status_code = 200
        raw_resp.text = "# Expense Policy\n\nAll expenses must be submitted within 30 days."

        mock_get.side_effect = [tree_resp, MagicMock(status_code=200, json=lambda: {"sha": "commit_999"}), tree_resp, raw_resp, raw_resp]

        discovered = await connector.discover_assets()
        assert len(discovered) == 2
        assert discovered[0].source_family == SourceFamily.DOCUMENT
        assert discovered[1].source_family == SourceFamily.STRUCTURED


@pytest.mark.asyncio
async def test_ingestion_job_queue_concurrency():
    queue = IngestionJobQueue(max_concurrent_jobs=2)
    src_1 = uuid.uuid4()
    src_2 = uuid.uuid4()

    with patch("app.ingestion.scheduler.SyncEngine") as mock_engine_cls:
        engine_inst = MagicMock()
        mock_engine_cls.return_value = engine_inst
        mock_result = MagicMock()
        mock_result.status = "success"
        mock_result.model_dump.return_value = {"status": "success", "claims_extracted": 5}
        engine_inst.sync_data_source = AsyncMock(return_value=mock_result)

        res1, res2 = await asyncio.gather(
            queue.enqueue_and_execute(src_1, use_mock_llm=True),
            queue.enqueue_and_execute(src_2, use_mock_llm=True),
        )

        assert res1["status"] == "success"
        assert res2["status"] == "success"
        assert res1["attempt"] == 1
