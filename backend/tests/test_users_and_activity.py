import uuid
import pytest
import httpx
from app.main import app
from app.db.init_db import init_db_schema

DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.anyio
async def test_list_and_seed_users_personas():
    await init_db_schema()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/v1/users?organization_id={DEMO_ORG_ID}")
        assert res.status_code == 200
        users = res.json()
        assert len(users) >= 4

        # Check for persona names
        names = [u["name"] for u in users]
        assert any("Sarah Chen" in n or "Sarah" in n for n in names)
        assert any("Marcus Vance" in n or "Marcus" in n for n in names)
        assert any("Elena" in n or "Elena Rostova" in n for n in names)


@pytest.mark.anyio
async def test_create_and_update_user():
    suffix = uuid.uuid4().hex[:6]
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a new member
        create_res = await client.post(
            "/v1/users",
            json={
                "organization_id": DEMO_ORG_ID,
                "name": f"Marcus Sterling {suffix}",
                "email": f"marcus.{suffix}@demo.local",
                "role": "data_owner",
                "title": "Lead Data Governance Architect",
                "department": "Enterprise Data Office",
            }
        )
        assert create_res.status_code == 201
        user = create_res.json()
        user_id = user["id"]
        assert user["name"] == f"Marcus Sterling {suffix}"
        assert user["role"] == "data_owner"

        # 2. Update role to admin
        patch_res = await client.patch(
            f"/v1/users/{user_id}",
            json={
                "role": "admin",
                "title": "VP of Trust & Governance"
            }
        )
        assert patch_res.status_code == 200
        updated = patch_res.json()
        assert updated["role"] == "admin"
        assert updated["title"] == "VP of Trust & Governance"


@pytest.mark.anyio
async def test_user_activity_stream_and_domains():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch domains
        dom_res = await client.get(f"/v1/users/domains?organization_id={DEMO_ORG_ID}")
        assert dom_res.status_code == 200
        domains = dom_res.json()
        assert len(domains) >= 3
        domain_names = [d["name"] for d in domains]
        assert "Finance & Billing" in domain_names
        assert "Engineering & Platform" in domain_names

        # 2. Fetch activity stream
        act_res = await client.get(f"/v1/users/activity?organization_id={DEMO_ORG_ID}")
        assert act_res.status_code == 200
        act_data = act_res.json()
        assert "activities" in act_data
        assert "total" in act_data
        assert isinstance(act_data["activities"], list)
