import uuid
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models.data_source import DataSource
from app.db.repositories.organization_repository import OrganizationRepository
from app.ingestion.connectors.kafka_connector import KafkaConnector
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.connectors.postgres_connector import PostgresConnector
from app.ingestion.connectors.salesforce_connector import SalesforceConnector
from app.ingestion.sync_engine import SyncEngine
from app.main import app


async def get_test_session():
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    return test_engine, session_factory()


@pytest.mark.anyio
async def test_postgres_connector_test_and_sync():
    engine, session = await get_test_session()
    try:
        org_repo = OrganizationRepository(session)
        org = await org_repo.get_or_create(name="Test Org Postgres", slug="test-org-pg")
        source = DataSource(
            organization_id=org.id,
            name="Core Production PostgreSQL",
            source_type="postgresql",
            external_id=f"pg-prod-{uuid.uuid4().hex[:6]}",
            authority_level=90,
            connection_config={
                "host": "localhost",
                "port": 5432,
                "database": "enterprise_core",
                "schemas": ["public"],
            },
        )
        session.add(source)
        await session.flush()

        connector = PostgresConnector(
            session=session,
            organization_id=org.id,
            source_id=source.id,
            connection_config=source.connection_config,
        )

        # Mock asyncpg connection
        mock_conn = AsyncMock()
        mock_conn.fetchval.return_value = "PostgreSQL 16.2 on x86_64"
        mock_conn.fetch.side_effect = [
            [{"schema_name": "public"}],  # available schemas
            [{"table_schema": "public", "table_name": "orders", "table_type": "BASE TABLE"}],  # tables
            [{"column_name": "order_id", "data_type": "uuid", "is_nullable": "NO", "column_default": None}],  # cols
            [{"constraint_type": "PRIMARY KEY", "constraint_name": "pk_orders", "column_name": "order_id"}],  # constraints
        ]

        with patch("asyncpg.connect", new_callable=AsyncMock) as mock_connect:
            mock_connect.return_value = mock_conn
            test_res = await connector.test_connection()
            assert test_res["success"] is True
            assert test_res["status"] == "ok"
            assert "PostgreSQL" in test_res["message"]

            synced = await connector.sync()
            assert len(synced) >= 1
            for doc, ver in synced:
                assert "PostgreSQL Schema" in doc.title
                assert doc.document_type == "data_contract"
                assert ver.content_hash is not None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_kafka_connector_test_and_sync():
    engine, session = await get_test_session()
    try:
        org_repo = OrganizationRepository(session)
        org = await org_repo.get_or_create(name="Test Org Kafka", slug="test-org-kafka")
        source = DataSource(
            organization_id=org.id,
            name="Production Kafka Event Stream",
            source_type="kafka",
            external_id=f"kafka-prod-{uuid.uuid4().hex[:6]}",
            authority_level=85,
            connection_config={
                "bootstrap_servers": "localhost:9092",
                "schema_registry_url": "http://localhost:8081",
                "security_protocol": "PLAINTEXT",
            },
        )
        session.add(source)
        await session.flush()

        connector = KafkaConnector(
            session=session,
            organization_id=org.id,
            source_id=source.id,
            connection_config=source.connection_config,
        )

        test_res = await connector.test_connection()
        # When unreachable, reports clean error
        assert "success" in test_res

        # Test with mocked Schema Registry response
        mock_resp_subjects = MagicMock()
        mock_resp_subjects.status_code = 200
        mock_resp_subjects.json.return_value = ["orders-value"]

        mock_resp_schema = MagicMock()
        mock_resp_schema.status_code = 200
        mock_resp_schema.json.return_value = {
            "version": 1,
            "schemaType": "AVRO",
            "schema": '{"fields": [{"name": "order_id", "type": "string"}]}',
        }

        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = [mock_resp_subjects, mock_resp_schema]
            synced = await connector.sync()
            assert len(synced) >= 1
            for doc, ver in synced:
                assert "Kafka Topic" in doc.title
                assert doc.document_type == "event_contract"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_salesforce_connector_test_and_sync():
    engine, session = await get_test_session()
    try:
        org_repo = OrganizationRepository(session)
        org = await org_repo.get_or_create(name="Test Org SFDC", slug="test-org-sfdc")
        source = DataSource(
            organization_id=org.id,
            name="Corporate Salesforce CRM",
            source_type="salesforce",
            external_id=f"sfdc-main-{uuid.uuid4().hex[:6]}",
            authority_level=88,
            connection_config={
                "instance_url": "https://demo-org.my.salesforce.com",
                "client_id": "test_client",
                "client_secret": "test_secret",
                "username": "admin@demo.com",
                "password": "test_password",
                "objects": ["Contract"],
            },
        )
        session.add(source)
        await session.flush()

        connector = SalesforceConnector(
            session=session,
            organization_id=org.id,
            source_id=source.id,
            connection_config=source.connection_config,
        )

        mock_token_resp = MagicMock()
        mock_token_resp.status_code = 200
        mock_token_resp.json.return_value = {"access_token": "mock_token_123", "instance_url": "https://demo-org.my.salesforce.com"}

        mock_describe_resp = MagicMock()
        mock_describe_resp.status_code = 200
        mock_describe_resp.json.return_value = {
            "label": "Contract",
            "custom": False,
            "fields": [{"name": "ContractNumber", "label": "Contract Number", "type": "string"}],
        }

        with patch("httpx.AsyncClient.post", return_value=mock_token_resp):
            test_res = await connector.test_connection()
            assert test_res["success"] is True

            with patch("httpx.AsyncClient.get", return_value=mock_describe_resp):
                synced = await connector.sync()
                assert len(synced) >= 1
                for doc, ver in synced:
                    assert "Salesforce Object" in doc.title
                    assert doc.document_type == "crm_contract"
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_mongodb_connector_test_and_sync():
    engine, session = await get_test_session()
    try:
        org_repo = OrganizationRepository(session)
        org = await org_repo.get_or_create(name="Test Org Mongo", slug="test-org-mongo")
        source = DataSource(
            organization_id=org.id,
            name="Document Store MongoDB",
            source_type="mongodb",
            external_id=f"mongo-prod-{uuid.uuid4().hex[:6]}",
            authority_level=82,
            connection_config={
                "connection_string": "mongodb://localhost:27017",
                "database": "production",
            },
        )
        session.add(source)
        await session.flush()

        connector = MongoDbConnector(
            session=session,
            organization_id=org.id,
            source_id=source.id,
            connection_config=source.connection_config,
        )

        mock_col = MagicMock()
        mock_col.index_information = AsyncMock(return_value={"_id_": {"key": [("_id", 1)]}})
        mock_find_cursor = MagicMock()
        mock_find_cursor.to_list = AsyncMock(return_value=[{"_id": "1", "name": "Item A", "amount": 100}])
        mock_col.find.return_value = mock_find_cursor

        mock_db = MagicMock()
        mock_db.list_collection_names = AsyncMock(return_value=["items"])
        mock_db.__getitem__.return_value = mock_col

        mock_client = MagicMock()
        mock_client.admin.command = AsyncMock(return_value={"ok": 1})
        mock_client.__getitem__.return_value = mock_db
        mock_client.close = MagicMock()

        with patch("motor.motor_asyncio.AsyncIOMotorClient", return_value=mock_client):
            test_res = await connector.test_connection()
            assert test_res["success"] is True

            synced = await connector.sync()
            assert len(synced) >= 1
            assert any("MongoDB Collection" in doc.title for doc, ver in synced)
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_api_test_connection_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Test Kafka pre-flight endpoint with configuration
        res_k = await client.post(
            "/v1/sources/test-connection",
            json={
                "source_type": "kafka",
                "connection_config": {
                    "bootstrap_servers": "localhost:9092",
                    "security_protocol": "PLAINTEXT",
                },
            },
        )
        assert res_k.status_code == 200
        data_k = res_k.json()
        assert data_k["success"] is True

        # Test Universal catalog connector pre-flight endpoint
        res_sf = await client.post(
            "/v1/sources/test-connection",
            json={
                "source_type": "snowflake",
                "connection_config": {
                    "host": "demo.snowflakecomputing.com",
                    "database": "ANALYTICS",
                },
            },
        )
        assert res_sf.status_code == 200
        assert res_sf.json()["success"] is True
