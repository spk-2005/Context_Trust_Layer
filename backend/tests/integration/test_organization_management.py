import pytest
import httpx


BASE_URL = "http://127.0.0.1:8000"


@pytest.mark.asyncio
async def test_list_organizations_with_metadata():
    """Verify listing organizations returns member counts and domain whitelists."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/v1/organizations")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        orgs = resp.json()
        assert len(orgs) >= 1
        first = orgs[0]
        assert "id" in first
        assert "name" in first
        assert "domain_whitelist" in first
        assert "allowed_auth_methods" in first
        assert "member_count" in first


@pytest.mark.asyncio
async def test_tenant_workspace_switching():
    """Verify switching organization updates context and returns new JWT signed with org_id."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # 1. Fetch available orgs
        res_orgs = await client.get("/v1/organizations")
        orgs = res_orgs.json()
        target_org = next((o for o in orgs if "SSFA" in o["name"]), orgs[0])

        # 2. Switch to target organization
        resp = await client.post(f"/v1/organizations/{target_org['id']}/switch", json={})
        assert resp.status_code == 200, f"Switch failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert "active_organization" in data
        assert data["active_organization"]["id"] == target_org["id"]
        assert data["user"]["organization_id"] == target_org["id"]


@pytest.mark.asyncio
async def test_organization_settings_and_domain_whitelist():
    """Verify updating domain whitelist and auth methods on organization."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        res_orgs = await client.get("/v1/organizations")
        orgs = res_orgs.json()
        target_org = next((o for o in orgs if "SSFA" in o["name"]), orgs[0])

        # Update settings
        patch_payload = {
            "domain_whitelist": ["ssfa.com", "ssfacapital.com", "wealth-ssfa.com"],
            "allowed_auth_methods": ["google", "microsoft", "password"]
        }
        res_patch = await client.patch(f"/v1/organizations/{target_org['id']}/settings", json=patch_payload)
        assert res_patch.status_code == 200, f"Patch failed: {res_patch.text}"
        updated = res_patch.json()
        assert "wealth-ssfa.com" in updated["domain_whitelist"]
        assert "okta" not in updated["allowed_auth_methods"]

        # Re-fetch settings
        res_get = await client.get(f"/v1/organizations/{target_org['id']}/settings")
        assert res_get.status_code == 200
        verified = res_get.json()
        assert "wealth-ssfa.com" in verified["domain_whitelist"]


@pytest.mark.asyncio
async def test_team_members_directory_and_role_update():
    """Verify listing organization members and modifying role."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        res_orgs = await client.get("/v1/organizations")
        orgs = res_orgs.json()
        target_org = orgs[0]

        # List members
        res_members = await client.get(f"/v1/organizations/{target_org['id']}/members")
        assert res_members.status_code == 200
        members = res_members.json()
        assert len(members) >= 1

        first_member = members[0]
        # Update role to reviewer
        res_role = await client.patch(
            f"/v1/organizations/{target_org['id']}/members/{first_member['id']}",
            json={"role": "reviewer"}
        )
        assert res_role.status_code == 200
        role_data = res_role.json()
        assert role_data["role"] == "reviewer"


@pytest.mark.asyncio
async def test_enterprise_invite_link_lifecycle():
    """Verify creating an invite, inspecting token, and accepting to onboard user."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        res_orgs = await client.get("/v1/organizations")
        orgs = res_orgs.json()
        target_org = next((o for o in orgs if "SSFA" in o["name"]), orgs[0])

        test_email = f"lead.compliance_{id(client)}@ssfa.com"

        # 1. Generate Invite
        invite_payload = {
            "email": test_email,
            "role": "reviewer"
        }
        res_invite = await client.post(f"/v1/organizations/{target_org['id']}/invites", json=invite_payload)
        assert res_invite.status_code == 201, f"Invite creation failed: {res_invite.text}"
        invite = res_invite.json()
        assert invite["email"] == test_email
        assert invite["role"] == "reviewer"
        token = invite["token"]

        # 2. Inspect Invite (unauthenticated)
        res_inspect = await client.get(f"/v1/organizations/invites/inspect?token={token}")
        assert res_inspect.status_code == 200, f"Inspect failed: {res_inspect.text}"
        inspect_data = res_inspect.json()
        assert inspect_data["email"] == test_email
        assert inspect_data["is_expired"] is False
        assert inspect_data["organization_id"] == target_org["id"]

        # 3. Accept Invite
        accept_payload = {
            "token": token,
            "full_name": "Compliance Lead Test",
            "password": "SecurePassword123!"
        }
        res_accept = await client.post("/v1/organizations/invites/accept", json=accept_payload)
        assert res_accept.status_code == 200, f"Accept failed: {res_accept.text}"
        accept_data = res_accept.json()
        assert "access_token" in accept_data
        assert accept_data["user"]["email"] == test_email
        assert accept_data["user"]["organization_id"] == target_org["id"]
        assert accept_data["user"]["role"] == "reviewer"
