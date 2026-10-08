import pytest
import httpx


BASE_URL = "http://127.0.0.1:8000"


@pytest.mark.asyncio
async def test_sso_providers_list():
    """Verify that all enterprise identity providers are exposed with protocol info."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        resp = await client.get("/v1/auth/sso/providers")
        assert resp.status_code == 200, f"Failed: {resp.text}"
        providers = resp.json()
        assert len(providers) >= 3
        provider_ids = [p["id"] for p in providers]
        assert "google" in provider_ids
        assert "microsoft" in provider_ids
        assert "okta" in provider_ids
        print("\n✓ SSO Providers List verified:", [p["name"] for p in providers])


@pytest.mark.asyncio
async def test_sso_authorize_urls():
    """Verify authorization URL generation for Google and Microsoft Entra ID."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        # Google
        res_g = await client.get("/v1/auth/sso/authorize/google")
        assert res_g.status_code == 200
        data_g = res_g.json()
        assert "authorization_url" in data_g
        assert data_g["provider"] == "google"
        assert len(data_g["state"]) > 10

        # Microsoft
        res_m = await client.get("/v1/auth/sso/authorize/microsoft")
        assert res_m.status_code == 200
        data_m = res_m.json()
        assert "authorization_url" in data_m
        assert data_m["provider"] == "microsoft"
        print("✓ SSO Authorize URLs generated successfully for Google and Microsoft")


@pytest.mark.asyncio
async def test_sso_callback_and_provisioning():
    """Verify OIDC callback creates/provisions user and returns signed JWT."""
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        payload = {
            "provider": "google",
            "mock_email": "google_test_sso@google.com",
            "mock_name": "Google Workspace Test User"
        }
        resp = await client.post("/v1/auth/sso/callback", json=payload)
        assert resp.status_code == 200, f"Callback failed: {resp.text}"
        data = resp.json()
        assert "access_token" in data
        assert "user" in data
        user = data["user"]
        assert user["email"] == "google_test_sso@google.com"
        assert user["organization_name"] in ("Trulin Trust Workspace", "Google Workspace Trust", "Trulin Enterprise Trust")
        print(f"✓ SSO Callback auto-provisioned user: {user['name']} in tenant '{user['organization_name']}'")


@pytest.mark.asyncio
async def test_corporate_domain_auto_routing():
    """Verify corporate email domains map to isolated enterprise tenant workspaces."""
    domains_to_test = [
        ("auditor@audit.internal", "Audit & Compliance Gateway"),
        ("governance@enterprise.org", "Enterprise AI Governance"),
    ]
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        for email, expected_org in domains_to_test:
            payload = {
                "provider": "sso",
                "corporate_email": email,
                "role": "reviewer"
            }
            resp = await client.post("/v1/auth/sso/sandbox-login", json=payload)
            assert resp.status_code == 200, f"Domain login failed for {email}: {resp.text}"
            data = resp.json()
            user = data["user"]
            assert user["email"] == email
            assert user["organization_name"] == expected_org
            print(f"✓ Corporate domain {email} mapped correctly to tenant workspace: '{user['organization_name']}'")


if __name__ == "__main__":
    import asyncio
    async def run_all():
        await test_sso_providers_list()
        await test_sso_authorize_urls()
        await test_sso_callback_and_provisioning()
        await test_corporate_domain_auto_routing()
        print("\n🎉 ALL SSO INTEGRATION TESTS PASSED!")
    asyncio.run(run_all())
