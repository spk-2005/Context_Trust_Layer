import json
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.mcp.server import (
    MCP_PROTOCOL_VERSION,
    MCP_SERVER_NAME,
    MCP_SERVER_VERSION,
    MCP_TOOLS,
    execute_mcp_tool,
)

router = APIRouter(prefix="/mcp", tags=["Model Context Protocol (MCP)"])


# -------------------------------------------------------------
# Pydantic Schemas for REST API
# -------------------------------------------------------------
class MCPToolInvokeRequest(BaseModel):
    tool: str = Field(..., description="The name of the MCP tool to invoke.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Input parameters conforming to tool's inputSchema.")


class MCPToolInvokeResponse(BaseModel):
    success: bool
    tool: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


# -------------------------------------------------------------
# Discovery & Tool List Endpoints
# -------------------------------------------------------------
@router.get("/manifest")
async def get_mcp_manifest():
    """Returns MCP Server manifest and protocol capabilities."""
    return {
        "schema_version": MCP_PROTOCOL_VERSION,
        "name": MCP_SERVER_NAME,
        "version": MCP_SERVER_VERSION,
        "description": "Enterprise Decision Safety & Governed Context Gate for AI Agents.",
        "capabilities": {
            "tools": {
                "listChanged": False
            },
            "resources": {},
            "prompts": {},
            "logging": {}
        },
        "endpoints": {
            "jsonrpc": "/v1/mcp",
            "tools": "/v1/mcp/tools",
            "invoke": "/v1/mcp/invoke"
        }
    }


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
    """Invokes an MCP tool directly via RESTful interface."""
    try:
        res = await execute_mcp_tool(req.tool, req.arguments, db)
        return MCPToolInvokeResponse(
            success=True,
            tool=req.tool,
            result=res
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception as e:
        return MCPToolInvokeResponse(
            success=False,
            tool=req.tool,
            error=str(e)
        )


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
                    "tools": {"listChanged": False}
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
        try:
            tool_res = await execute_mcp_tool(tool_name, args, db)
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
