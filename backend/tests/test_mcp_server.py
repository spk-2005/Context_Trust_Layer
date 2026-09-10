import pytest
import httpx
from app.main import app
from app.mcp.server import MCP_PROTOCOL_VERSION, MCP_TOOLS


@pytest.mark.anyio
async def test_mcp_manifest():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/v1/mcp/manifest")
        assert res.status_code == 200
        data = res.json()
        assert data["schema_version"] == MCP_PROTOCOL_VERSION
        assert data["name"] == "context-trust-layer"
        assert "tools" in data["capabilities"]


@pytest.mark.anyio
async def test_mcp_tools_list():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/v1/mcp/tools")
        assert res.status_code == 200
        data = res.json()
        assert "tools" in data
        assert len(data["tools"]) == 4
        tool_names = [t["name"] for t in data["tools"]]
        assert "context_trust_get_trusted_context" in tool_names
        assert "context_trust_evaluate_decision" in tool_names
        assert "context_trust_search_claims" in tool_names
        assert "context_trust_check_conflicts" in tool_names


@pytest.mark.anyio
async def test_mcp_rest_invoke_evaluate_decision():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/mcp/invoke",
            json={
                "tool": "context_trust_evaluate_decision",
                "arguments": {
                    "action_type": "customer_refund",
                    "actor_id": "88888888-8888-8888-8888-888888888888",
                    "actor_role": "billing_agent",
                    "parameters": {"amount": 5000, "customer_tier": "enterprise"}
                }
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert data["tool"] == "context_trust_evaluate_decision"
        assert "decision" in data["result"]


@pytest.mark.anyio
async def test_mcp_rest_invoke_search_claims():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            "/v1/mcp/invoke",
            json={
                "tool": "context_trust_search_claims",
                "arguments": {
                    "search_text": "refund",
                    "status": "all",
                    "limit": 5
                }
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["success"] is True
        assert "claims" in data["result"]


@pytest.mark.anyio
async def test_mcp_jsonrpc_initialize_and_tools():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Initialize
        res_init = await client.post(
            "/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {},
                "id": 1
            }
        )
        assert res_init.status_code == 200
        data_init = res_init.json()
        assert data_init["result"]["protocolVersion"] == MCP_PROTOCOL_VERSION

        # 2. tools/list
        res_list = await client.post(
            "/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 2
            }
        )
        assert res_list.status_code == 200
        data_list = res_list.json()
        assert len(data_list["result"]["tools"]) == 4

        # 3. tools/call
        res_call = await client.post(
            "/v1/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "context_trust_check_conflicts",
                    "arguments": {
                        "claim_text": "Refund window is 90 days."
                    }
                },
                "id": 3
            }
        )
        assert res_call.status_code == 200
        data_call = res_call.json()
        assert data_call["result"]["isError"] is False
        assert len(data_call["result"]["content"]) > 0

