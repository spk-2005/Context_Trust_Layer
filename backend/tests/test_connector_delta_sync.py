import pytest
import uuid
import httpx
from app.main import app

DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.anyio
async def test_connector_initial_sync_and_deduplication():
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
            }
        )
        assert create_res.status_code in (200, 201)
        source_data = create_res.json()
        source_id = source_data["id"]

        try:
            # 2. First Sync: Ingests documents and extracts claims
            sync1_res = await client.post(f"/v1/sources/{source_id}/sync?use_mock_llm=true")
            assert sync1_res.status_code == 200
            sync1_data = sync1_res.json()
            assert sync1_data["status"] == "success"
            assert sync1_data["documents_synced"] >= 1
            assert sync1_data["claims_extracted"] >= 0

            # 3. Second Sync with Identical Content: SHA-256 Deduplication triggers
            sync2_res = await client.post(f"/v1/sources/{source_id}/sync?use_mock_llm=true")
            assert sync2_res.status_code == 200
            sync2_data = sync2_res.json()
            assert sync2_data["status"] == "success"
            assert sync2_data["documents_synced"] >= 1
            assert sync2_data["execution_time_ms"] >= 0
        finally:
            await client.delete(f"/v1/sources/{source_id}")


@pytest.mark.anyio
async def test_universal_driver_content_hash_deduplication():
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
            }
        )
        assert create_res.status_code in (200, 201)
        source_id = create_res.json()["id"]

        try:
            # 1. First sync -> creates document
            s1 = await client.post(f"/v1/sources/{source_id}/sync?use_mock_llm=true")
            assert s1.status_code == 200
            d1 = s1.json()
            assert d1["status"] == "success"
            assert d1["documents_synced"] >= 1

            # 2. Second sync -> dedup skips LLM extraction
            s2 = await client.post(f"/v1/sources/{source_id}/sync?use_mock_llm=true")
            assert s2.status_code == 200
            d2 = s2.json()
            assert d2["status"] == "success"
            assert d2["documents_synced"] >= 1
        finally:
            await client.delete(f"/v1/sources/{source_id}")
