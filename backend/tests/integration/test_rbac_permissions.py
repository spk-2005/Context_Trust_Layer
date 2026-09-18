import pytest
import httpx


BASE_URL = "http://127.0.0.1:8000"


@pytest.mark.asyncio
async def test_rbac_matrix_endpoint():
    """Verify that GET /v1/auth/permissions/matrix exposes complete Atlan-grade RBAC schema."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/v1/auth/permissions/matrix")
        assert resp.status_code == 200, f"Matrix fetch failed: {resp.text}"
        data = resp.json()

        # Validate schema
        assert "roles" in data
        assert "all_permissions" in data
        assert len(data["all_permissions"]) >= 15

        roles = data["roles"]
        assert "admin" in roles
        assert "data_owner" in roles
        assert "reviewer" in roles
        assert "developer" in roles
        assert "viewer" in roles

        # Verify Separation of Duties in matrix definitions:
        # Data Owner has source sync & claim extract, but lacks conflict resolve
        assert "sources:sync" in roles["data_owner"]["permissions"]
        assert "claims:extract" in roles["data_owner"]["permissions"]
        assert "conflicts:resolve" not in roles["data_owner"]["permissions"]

        # Reviewer has conflict resolve, but lacks source sync & source manage
        assert "conflicts:resolve" in roles["reviewer"]["permissions"]
        assert "sources:sync" not in roles["reviewer"]["permissions"]
        assert "sources:manage" not in roles["reviewer"]["permissions"]
        assert "claims:extract" not in roles["reviewer"]["permissions"]

        # ML Operator has read access and runtime decisions evaluate only
        assert "decisions:evaluate" in roles["developer"]["permissions"]
        assert "conflicts:resolve" not in roles["developer"]["permissions"]
        assert "sources:sync" not in roles["developer"]["permissions"]

        print("\n[OK] Atlan RBAC Matrix schema and SoD matrix definitions verified")


@pytest.mark.asyncio
async def test_sod_conflict_resolution_enforcement():
    """Verify Separation of Duties on conflict resolution:
    - Data Stewards (data_owner) and ML Operators (developer) MUST receive 403 Forbidden
    - Risk Auditors (reviewer) and CCO (admin) have clearance
    """
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Data Steward attempt -> MUST BE 403
        resp_steward = await client.post("/v1/conflicts/re-evaluate?user_role=data_owner")
        assert resp_steward.status_code == 403, f"Expected 403 for data_owner, got {resp_steward.status_code}"
        assert "Separation of Duties" in resp_steward.json()["detail"]

        # 2. Developer / Operator attempt -> MUST BE 403
        resp_dev = await client.post("/v1/conflicts/re-evaluate?user_role=developer")
        assert resp_dev.status_code == 403, f"Expected 403 for developer, got {resp_dev.status_code}"
        assert "Separation of Duties" in resp_dev.json()["detail"]

        # 3. Risk Auditor attempt -> Clearance granted (200 OK)
        resp_auditor = await client.post("/v1/conflicts/re-evaluate?user_role=reviewer")
        assert resp_auditor.status_code == 200, "Reviewer must have clearance for conflicts:resolve"
        assert resp_auditor.json()["status"] == "success"

        # 4. Superadmin / CCO attempt -> Clearance granted (200 OK)
        resp_admin = await client.post("/v1/conflicts/re-evaluate?user_role=admin")
        assert resp_admin.status_code == 200, "Admin must have clearance for conflicts:resolve"
        assert resp_admin.json()["status"] == "success"

        print("[OK] Separation of Duties strictly enforced on conflict resolution")


@pytest.mark.asyncio
async def test_sod_source_sync_enforcement():
    """Verify Separation of Duties on source ingestion/sync:
    - Risk Auditors (reviewer) and ML Operators (developer) MUST receive 403 Forbidden
    - Data Stewards (data_owner) and CCO (admin) have clearance
    """
    dummy_source_id = "00000000-0000-0000-0000-000000000001"

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Auditor attempt -> MUST BE 403
        resp_auditor = await client.post(
            f"/v1/sources/{dummy_source_id}/sync?user_role=reviewer"
        )
        assert resp_auditor.status_code == 403, f"Expected 403 for reviewer, got {resp_auditor.status_code}"
        assert "Separation of Duties" in resp_auditor.json()["detail"]

        # 2. Developer / Operator attempt -> MUST BE 403
        resp_dev = await client.post(
            f"/v1/sources/{dummy_source_id}/sync?user_role=developer"
        )
        assert resp_dev.status_code == 403, f"Expected 403 for developer, got {resp_dev.status_code}"

        # 3. Data Steward attempt -> Clearance granted (not 403)
        resp_steward = await client.post(
            f"/v1/sources/{dummy_source_id}/sync?user_role=data_owner"
        )
        assert resp_steward.status_code != 403, "Data Steward must have clearance for sources:sync"

        # 4. Admin attempt -> Clearance granted (not 403)
        resp_admin = await client.post(
            f"/v1/sources/{dummy_source_id}/sync?user_role=admin"
        )
        assert resp_admin.status_code != 403, "Admin must have clearance for sources:sync"

        print("[OK] Separation of Duties strictly enforced on source ingestion sync")


@pytest.mark.asyncio
async def test_jwt_bearer_token_sod_enforcement():
    """Verify that JWT bearer token authenticated sessions enforce RBAC permissions."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Login as Data Steward (Alex Kumar: 33333333-3333-3333-3333-333333333333)
        login_res = await client.post(
            "/v1/auth/persona-login",
            json={"user_id": "33333333-3333-3333-3333-333333333333"}
        )
        assert login_res.status_code == 200
        token_steward = login_res.json()["access_token"]
        assert login_res.json()["user"]["role"] == "data_owner"

        # 2. Attempt conflict resolution with Steward token -> MUST BE 403 Forbidden
        headers = {"Authorization": f"Bearer {token_steward}"}
        resolve_res = await client.post(
            "/v1/conflicts/re-evaluate",
            headers=headers
        )
        assert resolve_res.status_code == 403, f"Expected 403, got {resolve_res.status_code}: {resolve_res.text}"
        detail = resolve_res.json()["detail"]
        assert "Separation of Duties" in detail or "Forbidden" in detail

        # 3. Quick login as Risk Auditor (Elena Rostova: 44444444-4444-4444-4444-444444444444)
        login_auditor = await client.post(
            "/v1/auth/persona-login",
            json={"user_id": "44444444-4444-4444-4444-444444444444"}
        )
        assert login_auditor.status_code == 200
        token_auditor = login_auditor.json()["access_token"]
        assert login_auditor.json()["user"]["role"] == "reviewer"

        # 4. Attempt source sync with Auditor token -> MUST BE 403 Forbidden
        headers_auditor = {"Authorization": f"Bearer {token_auditor}"}
        sync_res = await client.post(
            "/v1/sources/00000000-0000-0000-0000-000000000001/sync",
            headers=headers_auditor
        )
        assert sync_res.status_code == 403, f"Expected 403, got {sync_res.status_code}: {sync_res.text}"
        assert "Separation of Duties" in sync_res.json()["detail"]

        print("[OK] JWT Bearer Token RBAC resolution verified end-to-end")
