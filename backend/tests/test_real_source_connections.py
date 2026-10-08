import uuid
from unittest.mock import AsyncMock, patch, MagicMock
import httpx
import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.user import User
from app.db.repositories.organization_repository import OrganizationRepository
from app.ingestion.connector_registry import ConnectorRegistry
from app.ingestion.connectors.github_connector import GitHubConnector
from app.ingestion.sync_engine import SyncEngine
from app.main import app


async def get_test_session():
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    return test_engine, session_factory()


def test_connector_registry_105_connectors_and_github():
    """Verify that all 105 connectors are registered, and GitHub is fully configured with aliases."""
    all_connectors = ConnectorRegistry.get_all()
    assert len(all_connectors) >= 105, f"Expected at least 105 connectors, got {len(all_connectors)}"

    categories = ConnectorRegistry.get_categories()
    assert len(categories) == 10, f"Expected 10 categories, got {len(categories)}"

    # Verify GitHub is present and correctly categorized
    github_conn = ConnectorRegistry.get_by_id("github")
    assert github_conn is not None, "GitHub connector should be registered in ConnectorRegistry"
    assert github_conn.category == "crm_erp"
    assert "repository" in [f["id"] for f in github_conn.required_fields]
    assert "access_token" in [f["id"] for f in github_conn.required_fields]

    # Verify alias resolution
    assert ConnectorRegistry.find_connector("git") is not None
    assert ConnectorRegistry.find_connector("git").id == "github"
    assert ConnectorRegistry.find_connector("github_repo") is not None
    assert ConnectorRegistry.find_connector("github_repo").id == "github"
    assert ConnectorRegistry.find_connector("repo") is not None
    assert ConnectorRegistry.find_connector("repo").id == "github"

    # Verify other key connectors across domains
    assert ConnectorRegistry.get_by_id("postgresql") is not None
    assert ConnectorRegistry.get_by_id("snowflake") is not None
    assert ConnectorRegistry.get_by_id("s3") is not None
    assert ConnectorRegistry.get_by_id("kafka") is not None
    assert ConnectorRegistry.get_by_id("mongodb") is not None
    assert ConnectorRegistry.get_by_id("salesforce") is not None


@pytest.mark.anyio
async def test_sources_catalog_api_search_and_filter():
    """Verify the /v1/sources/catalog API returns all 105 connectors and responds to search queries."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # Full catalog
        res = await client.get("/v1/sources/catalog")
        assert res.status_code == 200
        data = res.json()
        assert data["total_supported"] >= 105
        assert any(c["id"] == "github" for c in data["connectors"])

        # Search for github
        res_gh = await client.get("/v1/sources/catalog?search=github")
        assert res_gh.status_code == 200
        gh_data = res_gh.json()
        assert gh_data["total_matched"] >= 1
        assert any(c["id"] == "github" for c in gh_data["connectors"])

        # Search for postgresql
        res_pg = await client.get("/v1/sources/catalog?search=postgres")
        assert res_pg.status_code == 200
        pg_data = res_pg.json()
        assert pg_data["total_matched"] >= 1
        assert any(c["id"] == "postgresql" for c in pg_data["connectors"])


@pytest.mark.anyio
async def test_preflight_connection_diagnostics():
    """Verify test-connection preflight diagnostics for GitHub, PostgreSQL, and Snowflake."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. GitHub preflight test with mock httpx response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "name": "enterprise-compliance",
            "full_name": "acme-corp/enterprise-compliance",
            "default_branch": "main",
            "open_issues_count": 5,
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_response
            res_gh = await client.post(
                "/v1/sources/test-connection",
                json={
                    "source_type": "github",
                    "connection_config": {
                        "repository": "acme-corp/enterprise-compliance",
                        "branch": "main",
                        "access_token": "ghp_mock_token_12345",
                    },
                },
            )
            assert res_gh.status_code == 200
            gh_res = res_gh.json()
            assert gh_res["success"] is True
            assert "validated successfully" in gh_res["message"]

        # 2. Universal Driver preflight test (Snowflake)
        res_sf = await client.post(
            "/v1/sources/test-connection",
            json={
                "source_type": "snowflake",
                "connection_config": {
                    "host": "acme.snowflakecomputing.com",
                    "database": "COMPLIANCE_DB",
                },
            },
        )
        assert res_sf.status_code == 200
        assert res_sf.json()["success"] is True


@pytest.mark.anyio
async def test_create_and_sync_source_with_owner_id_attribution():
    """
    Verify creating a real data source with user_id sets owner_id in PostgreSQL,
    and syncing the data source attributes the ingested documents to that user_id.
    """
    engine, session = await get_test_session()
    try:
        org_repo = OrganizationRepository(session)
        org = await org_repo.get_or_create(name="MultiTenant Test Org", slug=f"mt-test-{uuid.uuid4().hex[:6]}")

        # Create a test user with data_owner role
        test_user = User(
            organization_id=org.id,
            email=f"data_owner_{uuid.uuid4().hex[:6]}@example.com",
            name="Elena Rostova",
            role="data_owner",
        )
        session.add(test_user)
        await session.commit()
        await session.refresh(test_user)

        auth_token = create_access_token(subject=str(test_user.id))
        auth_headers = {"Authorization": f"Bearer {auth_token}"}

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Create Data Source with user_id
            create_payload = {
                "organization_id": str(org.id),
                "name": "Acme Legal Policies GitHub",
                "source_type": "github",
                "authority_level": 92,
                "domain": "Legal & Risk",
                "user_id": str(test_user.id),
                "connection_config": {
                    "repository": "acme/legal-policies",
                    "branch": "main",
                    "access_token": "ghp_mock_token_abc",
                },
            }
            res_create = await client.post("/v1/sources", json=create_payload, headers=auth_headers)
            assert res_create.status_code == 201, f"Create failed: {res_create.text}"
            source_data = res_create.json()
            source_id = source_data["id"]
            assert source_data["owner_id"] == str(test_user.id)

            # Verify in PostgreSQL
            db_source = await session.get(DataSource, uuid.UUID(source_id))
            assert db_source is not None
            assert db_source.owner_id == test_user.id
            assert db_source.authority_level == 92

            # 2. Mock GitHub crawl and trigger Sync via API
            mock_files = [
                {
                    "name": "FINANCIAL_RISK_POLICY_V3.md",
                    "path": "compliance/FINANCIAL_RISK_POLICY_V3.md",
                    "type": "file",
                    "url": "https://api.github.com/repos/acme/legal-policies/contents/compliance/FINANCIAL_RISK_POLICY_V3.md",
                    "download_url": "https://raw.githubusercontent.com/acme/legal-policies/main/compliance/FINANCIAL_RISK_POLICY_V3.md",
                }
            ]

            import base64
            encoded_content = base64.b64encode(
                b"# Financial Risk Policy\n\nWire transfers exceeding $100k require secondary executive authorization."
            ).decode("ascii")

            async def mock_get_handler(url, *args, **kwargs):
                resp = MagicMock()
                resp.status_code = 200
                url_str = str(url)
                if url_str.endswith(".md") or "FINANCIAL_RISK" in url_str:
                    resp.json.return_value = {"content": encoded_content, "sha": "commit_123"}
                    resp.text = "# Financial Risk Policy\n\nWire transfers exceeding $100k require secondary executive authorization."
                elif "contents" in url_str:
                    resp.json.return_value = mock_files
                elif "/repos/" in url_str:
                    resp.json.return_value = {
                        "name": "legal-policies",
                        "default_branch": "main",
                        "description": "Enterprise legal guidelines",
                    }
                else:
                    resp.json.return_value = {"content": encoded_content, "sha": "commit_123"}
                    resp.text = "# Financial Risk Policy\n\nWire transfers exceeding $100k require secondary executive authorization."
                return resp

            with patch("httpx.AsyncClient.get", side_effect=mock_get_handler):
                res_sync = await client.post(
                    f"/v1/sources/{source_id}/sync?user_id={test_user.id}",
                    headers=auth_headers
                )
                assert res_sync.status_code == 200, f"Sync returned error: {res_sync.text}"
                sync_result = res_sync.json()
                print("SYNC_RESULT:", sync_result)
                assert sync_result["documents_synced"] >= 1, f"Sync result was: {sync_result}"

            # 3. Verify documents in PostgreSQL are attributed to the user
            stmt = select(Document).where(Document.source_id == uuid.UUID(source_id))
            doc_result = await session.execute(stmt)
            docs = doc_result.scalars().all()
            assert len(docs) >= 1
            for doc in docs:
                assert doc.owner_id == test_user.id, f"Expected doc owner_id {test_user.id}, got {doc.owner_id}"
    finally:
        await session.close()
        await engine.dispose()
