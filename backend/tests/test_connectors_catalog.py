import uuid
import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.db.models.data_source import DataSource
from app.db.repositories.organization_repository import OrganizationRepository
from app.ingestion.connector_registry import CONNECTOR_CATALOG, ConnectorRegistry
from app.ingestion.connectors.universal_driver import UniversalConnectorDriver
from app.main import app


async def get_test_session():
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    return test_engine, session_factory()


def test_catalog_completeness():
    """Verify that all 104 enterprise connectors are registered in the catalog."""
    all_connectors = ConnectorRegistry.get_all()
    assert len(all_connectors) >= 104
    categories = ConnectorRegistry.get_categories()
    assert len(categories) == 10

    # Verify key representatives from each domain
    assert ConnectorRegistry.get_by_id("snowflake") is not None
    assert ConnectorRegistry.get_by_id("bigquery") is not None
    assert ConnectorRegistry.get_by_id("dbt") is not None
    assert ConnectorRegistry.get_by_id("airflow_openlineage") is not None
    assert ConnectorRegistry.get_by_id("tableau") is not None
    assert ConnectorRegistry.get_by_id("power_bi") is not None
    assert ConnectorRegistry.get_by_id("monte_carlo") is not None
    assert ConnectorRegistry.get_by_id("soda") is not None
    assert ConnectorRegistry.get_by_id("sagemaker") is not None
    assert ConnectorRegistry.get_by_id("sap_s4hana") is not None


@pytest.mark.anyio
async def test_universal_driver_across_families():
    engine, session = await get_test_session()
    try:
        org_repo = OrganizationRepository(session)
        org = await org_repo.get_or_create(name="Catalog Test Org", slug="cat-test-org")

        test_types = [
            "snowflake",  # relational / storage
            "dbt",        # etl
            "airflow_openlineage",  # orchestration
            "tableau",    # bi
            "monte_carlo", # observability
            "sagemaker",  # ml_ai
        ]

        for st in test_types:
            src = DataSource(
                organization_id=org.id,
                name=f"Test {st.title()}",
                source_type=st,
                external_id=f"{st}-{uuid.uuid4().hex[:6]}",
                authority_level=85,
                connection_config={"host": f"{st}.internal", "database": "demo"},
            )
            session.add(src)
            await session.flush()

            driver = UniversalConnectorDriver(
                session=session,
                organization_id=org.id,
                source_id=src.id,
                source_type=st,
                connection_config=src.connection_config,
            )

            test_res = await driver.test_connection()
            assert test_res["success"] is True
            assert test_res["status"] == "ok"

            synced = await driver.sync()
            assert len(synced) >= 1
            for doc, ver in synced:
                assert doc.document_type is not None
                assert ver.content_hash is not None
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_catalog_api_endpoints():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch full catalog
        res = await client.get("/v1/sources/catalog")
        assert res.status_code == 200
        data = res.json()
        assert data["total_supported"] >= 104
        assert len(data["connectors"]) >= 104
        assert len(data["categories"]) == 10

        # 2. Search filter for 'Snowflake'
        res_search = await client.get("/v1/sources/catalog?search=snowflake")
        assert res_search.status_code == 200
        search_data = res_search.json()
        assert search_data["total_matched"] >= 1
        assert any(c["id"] == "snowflake" for c in search_data["connectors"])

        # 3. Category filter for 'bi'
        res_cat = await client.get("/v1/sources/catalog?category=bi")
        assert res_cat.status_code == 200
        cat_data = res_cat.json()
        assert cat_data["total_matched"] >= 19

        # 4. Test pre-flight connection for Snowflake
        res_test_sf = await client.post(
            "/v1/sources/test-connection",
            json={"source_type": "snowflake", "connection_config": {"host": "xy12345.snowflakecomputing.com"}},
        )
        assert res_test_sf.status_code == 200
        assert res_test_sf.json()["success"] is True

        # 5. Test pre-flight connection for Tableau host parameter
        res_test_tab = await client.post(
            "/v1/sources/test-connection",
            json={"source_type": "tableau", "connection_config": {"host": "tableau.corp.internal"}},
        )
        assert res_test_tab.status_code == 200
        assert res_test_tab.json()["success"] is True
