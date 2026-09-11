import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app

DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"
DEMO_SOURCE_ID = "44444444-4444-4444-4444-444444444444"


@pytest.mark.asyncio
async def test_upload_and_extract_document():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Upload a policy markdown file
        file_content = b"# Enterprise Security Policy 2026\n\nAll external API traffic must strictly enforce TLS 1.3 encryption."
        files = {
            "file": ("sec_policy_2026.md", io.BytesIO(file_content), "text/markdown")
        }
        data = {
            "organization_id": DEMO_ORG_ID,
            "source_id": DEMO_SOURCE_ID,
            "title": "Enterprise Security Policy 2026",
            "document_type": "policy",
            "use_mock": "true"
        }
        res = await client.post("/v1/documents/upload-and-extract", files=files, data=data)
        assert res.status_code == 201
        res_json = res.json()
        assert res_json["success"] is True
        assert res_json["document"]["title"] == "Enterprise Security Policy 2026"
        assert "claims_extracted_count" in res_json
        assert "duration_ms" in res_json


@pytest.mark.asyncio
async def test_lineage_graph_and_blast_radius():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Fetch Lineage Graph
        res = await client.get(f"/v1/lineage/graph?organization_id={DEMO_ORG_ID}")
        assert res.status_code == 200
        data = res.json()
        assert "nodes" in data
        assert "edges" in data
        assert "counts" in data
        assert data["counts"]["sources"] >= 0

        # If claims exist, test blast radius
        res_claims = await client.get(f"/v1/claims?organization_id={DEMO_ORG_ID}&limit=1")
        if res_claims.status_code == 200 and len(res_claims.json()) > 0:
            claim_id = res_claims.json()[0]["id"]
            res_br = await client.get(f"/v1/lineage/blast-radius/{claim_id}")
            assert res_br.status_code == 200
            br_data = res_br.json()
            assert "risk_tier" in br_data
            assert "connected_conflicts_count" in br_data


@pytest.mark.asyncio
async def test_steward_audit_and_action():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Run audit scan
        res = await client.get(f"/v1/steward/audit?organization_id={DEMO_ORG_ID}")
        assert res.status_code == 200
        audit_data = res.json()
        assert "health_scorecard" in audit_data
        assert "freshness_index" in audit_data["health_scorecard"]
        assert "contradiction_index" in audit_data["health_scorecard"]
        assert "issues" in audit_data
        assert "recommendations" in audit_data

        # 2. Test applying a mock recommendation action
        res_claims = await client.get(f"/v1/claims?organization_id={DEMO_ORG_ID}&limit=1")
        if res_claims.status_code == 200 and len(res_claims.json()) > 0:
            claim_id = res_claims.json()[0]["id"]
            res_action = await client.post("/v1/steward/actions/apply", json={
                "action_type": "BOOST_EVIDENCE",
                "target_id": claim_id,
                "payload": {}
            })
            assert res_action.status_code == 200
            assert res_action.json()["success"] is True


@pytest.mark.asyncio
async def test_mcp_jsonrpc_expanded_tools():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Test tools/list contains lineage and steward tools
        res = await client.post("/v1/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": "test-tools-1"
        })
        assert res.status_code == 200
        tools = res.json()["result"]["tools"]
        tool_names = [t["name"] for t in tools]
        assert "context_trust_get_lineage" in tool_names
        assert "context_trust_steward_audit" in tool_names

        # Test tools/call on steward audit
        res_call = await client.post("/v1/mcp", json={
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": "context_trust_steward_audit",
                "arguments": {
                    "organization_id": DEMO_ORG_ID
                }
            },
            "id": "test-call-1"
        })
        assert res_call.status_code == 200
        assert res_call.json()["result"]["isError"] is False
