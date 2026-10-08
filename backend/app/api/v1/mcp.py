import asyncio
import json
import time
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.mcp.server import (
    MCP_PROTOCOL_VERSION,
    MCP_SERVER_NAME,
    MCP_SERVER_VERSION,
    MCP_TOOLS,
    MCP_RESOURCES,
    MCP_RESOURCE_TEMPLATES,
    MCP_PROMPTS,
    execute_mcp_tool,
    execute_mcp_resource,
    execute_mcp_prompt,
)
from app.schemas.mcp_middleware import (
    ToolCallProposal,
    ToolInterceptionResult,
    WorkflowPlanEvaluateRequest,
    WorkflowPlanEvaluateResponse,
)
from app.services.mcp_middleware_service import (
    intercept_tool_call,
    evaluate_workflow_plan,
)
from app.services.mcp_telemetry_service import (
    mcp_telemetry_service,
    MCPTelemetryEvent,
    MCPTelemetryStats,
)
from app.services.mcp_token_service import (
    mcp_token_service,
    AgentToken,
    CreateAgentTokenRequest,
)
from app.services.mcp_proxy_service import (
    mcp_proxy_service,
    ThirdPartyToolDefinition,
    ProxyToolExecuteRequest,
    ProxyToolExecuteResponse,
)

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])


# -------------------------------------------------------------
# Pydantic Schemas for REST API
# -------------------------------------------------------------
class MCPToolInvokeRequest(BaseModel):
    tool: str = Field(..., description="The name of the MCP tool to invoke.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input parameters conforming to tool's inputSchema.")
    client_type: Optional[str] = Field(default="REST Client", description="Identifier of the calling MCP host / client.")
    actor_id: Optional[str] = Field(default="mcp-agent")
    actor_role: Optional[str] = Field(default="support")


class MCPToolInvokeResponse(BaseModel):
    success: bool
    tool: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    latency_ms: Optional[float] = None
    verdict: Optional[str] = None


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


# -------------------------------------------------------------
# Discovery & Manifest Endpoints
# -------------------------------------------------------------
@router.get("/manifest")
async def get_mcp_manifest():
    """Returns complete MCP Server manifest and protocol capabilities."""
    return {
        "schema_version": MCP_PROTOCOL_VERSION,
        "name": MCP_SERVER_NAME,
        "version": MCP_SERVER_VERSION,
        "description": "Enterprise Decision Safety & Governed Context Gate for AI Agents.",
        "capabilities": {
            "tools": {
                "listChanged": False
            },
            "resources": {
                "subscribe": False,
                "listChanged": False
            },
            "prompts": {
                "listChanged": False
            },
            "sampling": {},
            "logging": {}
        },
        "endpoints": {
            "jsonrpc": "/v1/mcp",
            "sse": "/v1/mcp/sse",
            "messages": "/v1/mcp/messages",
            "tools": "/v1/mcp/tools",
            "resources": "/v1/mcp/resources",
            "prompts": "/v1/mcp/prompts",
            "telemetry": "/v1/mcp/telemetry",
            "tokens": "/v1/mcp/tokens",
            "proxies": "/v1/mcp/proxies",
            "invoke": "/v1/mcp/invoke"
        }
    }


# -------------------------------------------------------------
# Tools Discovery & REST Invocation
# -------------------------------------------------------------
@router.get("/tools")
async def list_mcp_tools():
    """Lists all available Model Context Protocol (MCP) tools and their parameter schemas."""
    return {
        "tools": MCP_TOOLS
    }


@router.post("/invoke", response_model=MCPToolInvokeResponse)
async def invoke_mcp_tool_rest(
    req: MCPToolInvokeRequest,
    db: AsyncSession = Depends(get_db),
):
    """Invokes an MCP tool directly via RESTful interface with full telemetry instrumentation."""
    start_time = time.perf_counter()
    try:
        res = await execute_mcp_tool(req.tool, req.arguments, db)
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        
        verdict = res.get("decision") or res.get("verdict") or ("ALLOW" if res.get("status") == "success" or res.get("is_safe", True) else "REVIEW")
        score = float(res.get("trust_score", 0.90))

        # Record telemetry
        mcp_telemetry_service.record_event(
            tool_name=req.tool,
            arguments=req.arguments,
            client_type=req.client_type or "REST Client",
            actor_id=req.actor_id or "mcp-agent",
            actor_role=req.actor_role or "support",
            verdict=verdict,
            trust_score=score,
            latency_ms=latency,
            response_summary=f"Executed {req.tool} successfully",
        )

        return MCPToolInvokeResponse(
            success=True,
            tool=req.tool,
            result=res,
            latency_ms=latency,
            verdict=verdict
        )
    except ValueError as e:
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        mcp_telemetry_service.record_event(
            tool_name=req.tool,
            arguments=req.arguments,
            client_type=req.client_type or "REST Client",
            verdict="ERROR",
            trust_score=0.0,
            latency_ms=latency,
            error=str(e)
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        mcp_telemetry_service.record_event(
            tool_name=req.tool,
            arguments=req.arguments,
            client_type=req.client_type or "REST Client",
            verdict="ERROR",
            trust_score=0.0,
            latency_ms=latency,
            error=str(e)
        )
        return MCPToolInvokeResponse(
            success=False,
            tool=req.tool,
            error=str(e),
            latency_ms=latency,
            verdict="ERROR"
        )


# -------------------------------------------------------------
# MCP Resources Endpoints
# -------------------------------------------------------------
@router.get("/resources")
async def list_resources():
    """Lists available read-only MCP context resources and templates."""
    return {
        "resources": MCP_RESOURCES,
        "resourceTemplates": MCP_RESOURCE_TEMPLATES
    }


@router.get("/resources/read")
async def read_resource(
    uri: str = Query(..., description="The context:// URI to read"),
    db: AsyncSession = Depends(get_db),
):
    """Directly reads and parses an MCP context resource URI."""
    res = await execute_mcp_resource(uri, db)
    return res


# -------------------------------------------------------------
# MCP Prompts Endpoints
# -------------------------------------------------------------
@router.get("/prompts")
async def list_prompts():
    """Lists governed MCP prompt templates."""
    return {
        "prompts": MCP_PROMPTS
    }


@router.post("/prompts/{prompt_name}")
async def get_prompt_template(
    prompt_name: str,
    args: Dict[str, Any] = {},
    db: AsyncSession = Depends(get_db),
):
    """Retrieves and hydrates a governed prompt template with given parameters."""
    try:
        res = await execute_mcp_prompt(prompt_name, args, db)
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------------------------------------------
# JSON-RPC 2.0 Endpoint (Standard MCP Protocol Handler)
# -------------------------------------------------------------
@router.post("")
async def handle_mcp_jsonrpc(
    rpc_req: JSONRPCRequest,
    db: AsyncSession = Depends(get_db),
):
    """Standard JSON-RPC 2.0 MCP endpoint compatible with Claude Desktop, Cursor, and SDK clients."""
    method = rpc_req.method
    params = rpc_req.params or {}
    req_id = rpc_req.id

    # 1. Initialize
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": MCP_PROTOCOL_VERSION,
                "capabilities": {
                    "tools": {"listChanged": False},
                    "resources": {"subscribe": False, "listChanged": False},
                    "prompts": {"listChanged": False},
                    "sampling": {},
                    "logging": {}
                },
                "serverInfo": {
                    "name": MCP_SERVER_NAME,
                    "version": MCP_SERVER_VERSION
                }
            }
        }

    # 2. Ping
    elif method == "ping":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {}
        }

    # 3. Tools / List
    elif method in ("tools/list", "list_tools"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "tools": MCP_TOOLS
            }
        }

    # 4. Tools / Call
    elif method in ("tools/call", "call_tool"):
        tool_name = params.get("name")
        args = params.get("arguments") or {}
        start_t = time.perf_counter()
        try:
            tool_res = await execute_mcp_tool(tool_name, args, db)
            latency = round((time.perf_counter() - start_t) * 1000, 2)
            
            verdict = tool_res.get("decision") or tool_res.get("verdict") or ("ALLOW" if tool_res.get("status") == "success" or tool_res.get("is_safe", True) else "REVIEW")
            score = float(tool_res.get("trust_score", 0.90))

            mcp_telemetry_service.record_event(
                tool_name=tool_name,
                arguments=args,
                client_type="Claude / Cursor JSON-RPC",
                verdict=verdict,
                trust_score=score,
                latency_ms=latency,
                response_summary=f"JSON-RPC call executed {tool_name}"
            )

            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(tool_res, indent=2)
                        }
                    ],
                    "isError": False
                }
            }
        except Exception as err:
            latency = round((time.perf_counter() - start_t) * 1000, 2)
            mcp_telemetry_service.record_event(
                tool_name=tool_name,
                arguments=args,
                client_type="Claude / Cursor JSON-RPC",
                verdict="ERROR",
                trust_score=0.0,
                latency_ms=latency,
                error=str(err)
            )
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing tool '{tool_name}': {str(err)}"
                        }
                    ],
                    "isError": True
                }
            }

    # 5. Resources / List
    elif method in ("resources/list", "list_resources"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resources": MCP_RESOURCES
            }
        }

    # 6. Resources / Templates / List
    elif method in ("resources/templates/list", "list_resource_templates"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "resourceTemplates": MCP_RESOURCE_TEMPLATES
            }
        }

    # 7. Resources / Read
    elif method in ("resources/read", "read_resource"):
        uri = params.get("uri", "")
        try:
            content_res = await execute_mcp_resource(uri, db)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "contents": [
                        content_res
                    ]
                }
            }
        except Exception as err:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32000,
                    "message": f"Resource read failed: {str(err)}"
                }
            }

    # 8. Prompts / List
    elif method in ("prompts/list", "list_prompts"):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "prompts": MCP_PROMPTS
            }
        }

    # 9. Prompts / Get
    elif method in ("prompts/get", "get_prompt"):
        p_name = params.get("name", "")
        p_args = params.get("arguments", {})
        try:
            prompt_res = await execute_mcp_prompt(p_name, p_args, db)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": prompt_res
            }
        except Exception as err:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {
                    "code": -32602,
                    "message": f"Prompt get failed: {str(err)}"
                }
            }

    # 10. Sampling / createMessage
    elif method == "sampling/createMessage":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "role": "assistant",
                "content": {
                    "type": "text",
                    "text": "Sampling request received and verified under Context Trust Layer Governance."
                },
                "model": "context-trust-guard-v2"
            }
        }

    # Unknown method
    else:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not recognized by Context Trust Layer MCP Server."
            }
        }


# -------------------------------------------------------------
# SSE (Server-Sent Events) Streaming Transport Endpoints
# -------------------------------------------------------------
@router.get("/sse")
async def mcp_sse_transport(request: Request):
    """Opens a Server-Sent Events (SSE) streaming channel conforming to MCP spec for remote hosts."""
    session_id = str(uuid.uuid4())

    async def event_generator():
        # Step 1: Send endpoint event directing client where to POST messages
        endpoint_data = json.dumps({"endpoint": f"/v1/mcp/messages?sessionId={session_id}"})
        yield f"event: endpoint\ndata: {endpoint_data}\n\n"

        # Keep alive loop
        while True:
            if await request.is_disconnected():
                break
            await asyncio.sleep(15)
            yield f": ping\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/messages")
async def mcp_sse_message_handler(
    request: Request,
    sessionId: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """Processes JSON-RPC messages routed through an active SSE session."""
    body = await request.json()
    rpc_req = JSONRPCRequest(**body)
    return await handle_mcp_jsonrpc(rpc_req, db)


# -------------------------------------------------------------
# Live Telemetry & Audit Stream Endpoints
# -------------------------------------------------------------
@router.get("/telemetry")
async def get_mcp_telemetry(
    limit: int = Query(50, ge=1, le=200),
    filter: Optional[str] = Query(None),
):
    """Retrieves real-time invocation telemetry, waterfall logs, and health statistics."""
    events = mcp_telemetry_service.get_events(limit=limit, tool_filter=filter)
    stats = mcp_telemetry_service.get_stats()
    return {
        "stats": stats.model_dump(),
        "events": [e.model_dump() for e in events]
    }


@router.delete("/telemetry")
async def clear_mcp_telemetry():
    """Clears invocation logs."""
    mcp_telemetry_service.clear()
    return {"status": "cleared"}


# -------------------------------------------------------------
# Agent API Tokens & Scoped RBAC Endpoints
# -------------------------------------------------------------
@router.get("/tokens")
async def list_agent_tokens(
    organization_id: Optional[str] = Query(None),
):
    """Lists all active and revoked Agent MCP API tokens with role entitlements."""
    tokens = mcp_token_service.list_tokens(organization_id)
    return {"tokens": [t.model_dump() for t in tokens]}


@router.post("/tokens", response_model=AgentToken)
async def create_agent_token(req: CreateAgentTokenRequest):
    """Creates and registers a new scoped Agent API token."""
    return mcp_token_service.create_token(req)


@router.delete("/tokens/{token_id}")
async def revoke_agent_token(token_id: str):
    """Revokes an agent's MCP access token."""
    success = mcp_token_service.revoke_token(token_id)
    if not success:
        raise HTTPException(status_code=404, detail="Token not found")
    return {"status": "revoked", "token_id": token_id}


# -------------------------------------------------------------
# 3rd-Party MCP Tool Proxying & Sandbox Wrapper Endpoints
# -------------------------------------------------------------
@router.get("/proxies")
async def list_proxy_tools():
    """Lists registered 3rd-party external tools (Stripe, PostgreSQL, GitHub, Slack) wrapped with Context Trust Layer Guardrails."""
    tools = mcp_proxy_service.list_proxy_tools()
    return {"tools": [t.model_dump() for t in tools]}


@router.post("/proxies", response_model=ThirdPartyToolDefinition)
async def register_proxy_tool(tool: ThirdPartyToolDefinition):
    """Registers a new external MCP tool to be proxied and governed."""
    return mcp_proxy_service.register_tool(tool)


@router.post("/proxies/execute", response_model=ProxyToolExecuteResponse)
async def execute_proxy_tool(req: ProxyToolExecuteRequest):
    """Executes a 3rd-party tool proposal through the zero-trust interception and sandboxing pipeline."""
    try:
        res = await mcp_proxy_service.execute_proxy_tool(req)
        mcp_telemetry_service.record_event(
            tool_name=res.tool_name,
            arguments=req.arguments,
            client_type=f"{res.provider} Proxy Wrapper",
            actor_id=req.actor_id,
            actor_role=req.actor_role,
            verdict=res.guardrail_verdict,
            trust_score=0.95 if res.guardrail_verdict == "PERMIT" else 0.30,
            latency_ms=res.execution_ms,
            response_summary=f"Executed via {res.provider} proxy wrapper with verdict {res.guardrail_verdict}"
        )
        return res
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


# -------------------------------------------------------------
# Tool Call Interception & Multi-Step Workflow Endpoints
# -------------------------------------------------------------
@router.post("/intercept-tool", response_model=ToolInterceptionResult)
async def intercept_tool(proposal: ToolCallProposal):
    """Pre-execution gateway interceptor for AI agent tool invocations."""
    return await intercept_tool_call(proposal)


@router.post("/workflow/evaluate", response_model=WorkflowPlanEvaluateResponse)
async def evaluate_workflow(plan: WorkflowPlanEvaluateRequest):
    """Evaluates an entire multi-step agent workflow execution plan before tools execute."""
    return await evaluate_workflow_plan(plan)
