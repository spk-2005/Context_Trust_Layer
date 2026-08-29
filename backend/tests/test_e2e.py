import asyncio
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[1]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import httpx

from app.db.database import AsyncSessionLocal
from app.db.repositories.data_source_repository import DataSourceRepository
from app.db.repositories.organization_repository import OrganizationRepository
from app.main import app


async def test_end_to_end_flow():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Root & Health
        r = await client.get("/")
        assert r.status_code == 200, f"Root failed: {r.text}"
        assert r.json()["status"] == "running"
        print("[PASS] Root endpoint /")

        r = await client.get("/v1/health")
        assert r.status_code == 200, f"Health failed: {r.text}"
        health_data = r.json()
        assert health_data["status"] == "healthy"
        assert health_data["database"] is True
        assert "pgcrypto" in health_data["extensions"]
        assert "vector" in health_data["extensions"]
        print("[PASS] Health endpoint /v1/health (DB + pgcrypto + vector verified)")

        # 2. Seed Organization & DataSource
        test_suffix = uuid.uuid4().hex[:6]
        async with AsyncSessionLocal() as session:
            org_repo = OrganizationRepository(session)
            ds_repo = DataSourceRepository(session)
            org = await org_repo.get_or_create(
                name=f"Acme Corp {test_suffix}",
                slug=f"acme-corp-{test_suffix}",
            )
            ds = await ds_repo.get_or_create(
                organization_id=org.id,
                name="Confluence HR Space",
                source_type="confluence",
                external_id=f"hr-wiki-{test_suffix}",
                authority_level=90,
            )
            await session.commit()
            org_id = str(org.id)
            ds_id = str(ds.id)
            print(f"[PASS] Organization ({org.name}) and DataSource ({ds.name}) ready")

        # 3. Ingest Version 1 of Document
        ext_doc_id = f"policy-hr-annual-leave-{test_suffix}"
        doc_payload_v1 = {
            "organization_id": org_id,
            "source_id": ds_id,
            "title": "HR Policy 2025",
            "content": (
                "# Annual Leave Policy\n\n"
                "All full-time employees receive 20 days of annual leave per year.\n\n"
                "# Sick Leave Policy\n\n"
                "Employees are granted 10 days of paid sick leave annually."
            ),
            "document_type": "policy",
            "external_id": ext_doc_id,
            "metadata": {"author": "HR Director", "year": 2025},
        }

        r = await client.post("/v1/documents", json=doc_payload_v1)
        assert r.status_code == 201, f"Create v1 failed: {r.text}"
        res_v1 = r.json()
        doc_id = res_v1["document"]["id"]
        v1_version = res_v1["current_version"]
        assert v1_version["version_number"] == 1
        assert v1_version["is_current"] is True
        assert res_v1["normalized"] is True
        print(f"[PASS] Ingested Document Version 1 (ID: {doc_id})")

        # 4. Ingest Version 2 of Document (Update to 25 days)
        doc_payload_v2 = {
            "organization_id": org_id,
            "source_id": ds_id,
            "title": "HR Policy 2026",
            "content": (
                "# Annual Leave Policy\n\n"
                "All full-time employees receive 25 days of annual leave per year.\n\n"
                "# Sick Leave Policy\n\n"
                "Employees are granted 12 days of paid sick leave annually."
            ),
            "document_type": "policy",
            "external_id": ext_doc_id,
            "metadata": {"author": "HR Director", "year": 2026},
        }

        r2 = await client.post("/v1/documents", json=doc_payload_v2)
        assert r2.status_code == 201, f"Create v2 failed: {r2.text}"
        res_v2 = r2.json()
        v2_version = res_v2["current_version"]
        assert v2_version["version_number"] == 2
        assert v2_version["is_current"] is True
        print("[PASS] Ingested Document Version 2 (Incremented version number & current version set)")

        # 5. Fetch Document and Verify Version History
        r_get = await client.get(f"/v1/documents/{doc_id}")
        assert r_get.status_code == 200, f"Get doc failed: {r_get.text}"
        doc_full = r_get.json()
        assert doc_full["title"] == "HR Policy 2026"
        versions = doc_full["versions"]
        assert len(versions) == 2

        # Check is_current statuses
        current_versions = [v for v in versions if v["is_current"]]
        assert len(current_versions) == 1
        assert current_versions[0]["version_number"] == 2
        print(f"[PASS] Verified version history: {len(versions)} versions, only version {current_versions[0]['version_number']} is current")


if __name__ == "__main__":
    asyncio.run(test_end_to_end_flow())
    print("\n==========================================")
    print("ALL TESTS PASSED SUCCESSFULLY!")
    print("==========================================")
