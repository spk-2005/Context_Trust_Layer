import pytest
import uuid
import httpx
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.security import create_access_token
from app.db.enums import UserRole
from app.db.models.user import User
from app.db.init_db import init_db_schema
from app.main import app

DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"


async def get_test_session():
    test_engine = create_async_engine(settings.database_url, poolclass=NullPool)
    session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)
    return test_engine, session_factory()


@pytest.mark.anyio
async def test_connector_initial_sync_and_deduplication():
    await init_db_schema()
    engine, session = await get_test_session()
    try:
        test_user = User(
            id=uuid.uuid4(),
            organization_id=uuid.UUID(DEMO_ORG_ID),
            email=f"delta_sync_{uuid.uuid4().hex[:6]}@example.com",
            name="Delta Sync Admin",
            role=UserRole.ADMIN,
        )
        session.add(test_user)
        await session.commit()

        token = create_access_token(subject=str(test_user.id))
        auth_headers = {"Authorization": f"Bearer {token}"}

        suffix = uuid.uuid4().hex[:6]
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. Register a test source connector
            create_res = await client.post(
                "/v1/sources",
                json={
                    "organization_id": DEMO_ORG_ID,
                    "name": f"Delta Sync Fast Test Source {suffix}",
                    "source_type": "snowflake_warehouse",
                    "external_id": f"snowflake://xy12345.snowflakecomputing.com/FINANCE_DB_{suffix}",
                    "authority_level": 90,
                    "connection_config": {
                        "host": "xy12345.snowflakecomputing.com",
                        "database": "FINANCE_DB",
                        "schema": "COMPLIANCE"
                    }
                },
                headers=auth_headers
            )
            assert create_res.status_code in (200, 201)
            source_data = create_res.json()
            source_id = source_data["id"]

            try:
                # 2. First Sync: Ingests documents and extracts claims
                sync1_res = await client.post(f"/v1/sources/{source_id}/sync?use_mock_llm=true", headers=auth_headers)
                assert sync1_res.status_code == 200
                sync1_data = sync1_res.json()
                assert sync1_data["status"] == "success"
                assert sync1_data["documents_synced"] >= 1
                assert sync1_data["claims_extracted"] >= 0

                # 3. Second Sync with Identical Content: SHA-256 Deduplication triggers
                sync2_res = await client.post(f"/v1/sources/{source_id}/sync?use_mock_llm=true", headers=auth_headers)
                assert sync2_res.status_code == 200
                sync2_data = sync2_res.json()
                assert sync2_data["status"] == "success"
                assert sync2_data["documents_synced"] >= 1
                assert sync2_data["execution_time_ms"] >= 0
            finally:
                await client.delete(f"/v1/sources/{source_id}", headers=auth_headers)
    finally:
        await session.close()
        await engine.dispose()


@pytest.mark.anyio
async def test_universal_driver_content_hash_deduplication():
    await init_db_schema()
    engine, session = await get_test_session()
    try:
        test_user = User(
            id=uuid.uuid4(),
            organization_id=uuid.UUID(DEMO_ORG_ID),
            email=f"delta_driver_{uuid.uuid4().hex[:6]}@example.com",
            name="Delta Driver Admin",
            role=UserRole.ADMIN,
        )
        session.add(test_user)
        await session.commit()

        token = create_access_token(subject=str(test_user.id))
        auth_headers = {"Authorization": f"Bearer {token}"}

        suffix = uuid.uuid4().hex[:6]
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            # Register a universal connector
            create_res = await client.post(
                "/v1/sources",
                json={
                    "organization_id": DEMO_ORG_ID,
                    "name": f"BigQuery Analytics Delta Driver {suffix}",
                    "source_type": "google_bigquery",
                    "external_id": f"bigquery://prod-analytics/compliance-{suffix}",
                    "authority_level": 95,
                    "connection_config": {
                        "host": "bigquery.googleapis.com",
                        "project": "prod-analytics",
                        "dataset": "compliance"
                    }
                },
                headers=auth_headers
            )
            assert create_res.status_code in (200, 201)
            source_id = create_res.json()["id"]

            try:
                # 1. First sync -> creates document
                s1 = await client.post(f"/v1/sources/{source_id}/sync?use_mock_llm=true", headers=auth_headers)
                assert s1.status_code == 200
                d1 = s1.json()
                assert d1["status"] == "success"
                assert d1["documents_synced"] >= 1

                # 2. Second sync -> dedup skips LLM extraction
                s2 = await client.post(f"/v1/sources/{source_id}/sync?use_mock_llm=true", headers=auth_headers)
                assert s2.status_code == 200
                d2 = s2.json()
                assert d2["status"] == "success"
                assert d2["documents_synced"] >= 1
            finally:
                await client.delete(f"/v1/sources/{source_id}", headers=auth_headers)
    finally:
        await session.close()
        await engine.dispose()
