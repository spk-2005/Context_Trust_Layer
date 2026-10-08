import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.services.mcp_middleware_service import intercept_tool_call
from app.schemas.mcp_middleware import ToolCallProposal, ToolInterceptionResult


class ThirdPartyToolDefinition(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    provider: str  # "Stripe", "PostgreSQL", "GitHub", "Slack", "Jira", "Custom"
    description: str
    icon: str
    category: str
    endpoint_url: Optional[str] = None
    default_role: str = "developer"
    sample_args: Dict[str, Any] = Field(default_factory=dict)
    risk_level: str = "HIGH"  # "LOW", "MEDIUM", "HIGH", "CRITICAL"
    guardrails_active: bool = True


class ProxyToolExecuteRequest(BaseModel):
    tool_id: str
    arguments: Dict[str, Any]
    actor_id: str = "autonomous-agent"
    actor_role: str = "developer"
    justification: Optional[str] = None


class ProxyToolExecuteResponse(BaseModel):
    success: bool
    tool_id: str
    tool_name: str
    provider: str
    guardrail_verdict: str  # "PERMIT", "BLOCK", "REQUIRE_REVIEW"
    permit_token: Optional[str] = None
    reasons: List[str] = Field(default_factory=list)
    risk_score: float = 0.0
    liability_prevented_usd: float = 0.0
    simulated_output: Optional[Dict[str, Any]] = None
    execution_ms: int = 24


class MCPProxyService:
    _instance = None
    _tools: Dict[str, ThirdPartyToolDefinition] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MCPProxyService, cls).__new__(cls)
            cls._instance._init_seed_tools()
        return cls._instance

    def _init_seed_tools(self):
        seed_list = [
            ThirdPartyToolDefinition(
                id="tool-postgres-query",
                name="execute_sql_query",
                provider="PostgreSQL",
                description="Executes arbitrary SQL queries against production reporting read/write replica.",
                icon="🐘",
                category="Database",
                endpoint_url="mcp://postgres.internal:5432/main",
                default_role="developer",
                sample_args={"query": "SELECT user_id, email, status FROM accounts WHERE plan = 'enterprise' LIMIT 20;"},
                risk_level="CRITICAL",
                guardrails_active=True
            ),
            ThirdPartyToolDefinition(
                id="tool-stripe-refund",
                name="issue_customer_refund",
                provider="Stripe",
                description="Issues charge refunds, dispute waivers, or balance credits to enterprise customer cards.",
                icon="💳",
                category="Payments & Billing",
                endpoint_url="https://api.stripe.com/v1/refunds",
                default_role="finance",
                sample_args={"charge_id": "ch_3MtwL24JyNd9", "amount_cents": 450000, "reason": "requested_by_customer"},
                risk_level="HIGH",
                guardrails_active=True
            ),
            ThirdPartyToolDefinition(
                id="tool-github-merge",
                name="merge_pull_request",
                provider="GitHub",
                description="Merges pull requests directly into protected main/production branches.",
                icon="🐙",
                category="DevOps & CI/CD",
                endpoint_url="https://api.github.com/repos/org/repo/pulls/124/merge",
                default_role="developer",
                sample_args={"pull_number": 124, "merge_method": "squash", "commit_title": "Hotfix: bypass auth"},
                risk_level="HIGH",
                guardrails_active=True
            ),
            ThirdPartyToolDefinition(
                id="tool-slack-announce",
                name="post_channel_announcement",
                provider="Slack",
                description="Broadcasts company-wide policy updates or alert notifications to public channels.",
                icon="💬",
                category="Communications",
                endpoint_url="https://slack.com/api/chat.postMessage",
                default_role="support",
                sample_args={"channel": "#all-engineering", "text": "Deploying emergency patch v1.8.2"},
                risk_level="MEDIUM",
                guardrails_active=True
            ),
            ThirdPartyToolDefinition(
                id="tool-aws-firewall",
                name="update_security_group_ingress",
                provider="AWS SecOps",
                description="Modifies VPC Security Group rules to allow external CIDR ingress traffic.",
                icon="☁️",
                category="Cloud Infrastructure",
                endpoint_url="https://ec2.us-east-1.amazonaws.com",
                default_role="secops",
                sample_args={"group_id": "sg-0441a", "protocol": "tcp", "port": 22, "cidr_ip": "0.0.0.0/0"},
                risk_level="CRITICAL",
                guardrails_active=True
            ),
        ]
        for t in seed_list:
            self._tools[t.id] = t

    def list_proxy_tools(self) -> List[ThirdPartyToolDefinition]:
        return list(self._tools.values())

    def register_tool(self, tool: ThirdPartyToolDefinition) -> ThirdPartyToolDefinition:
        self._tools[tool.id] = tool
        return tool

    async def execute_proxy_tool(self, req: ProxyToolExecuteRequest) -> ProxyToolExecuteResponse:
        tool_def = self._tools.get(req.tool_id)
        if not tool_def:
            # Try to match by name
            for t in self._tools.values():
                if t.name == req.tool_id:
                    tool_def = t
                    break
        
        if not tool_def:
            raise ValueError(f"Third-party tool '{req.tool_id}' not found in proxy registry")

        # 1. Run through Zero-Trust Pre-Execution Interception Guardrail
        proposal = ToolCallProposal(
            tool_name=tool_def.name,
            arguments=req.arguments,
            actor_id=req.actor_id,
            actor_role=req.actor_role,
            justification=req.justification or f"Autonomous execution via {tool_def.provider} Proxy Wrapper",
        )

        guardrail_res: ToolInterceptionResult = await intercept_tool_call(proposal)

        # 2. If permitted, execute simulated tool action
        simulated_output = None
        if guardrail_res.verdict == "PERMIT":
            if tool_def.provider == "PostgreSQL":
                simulated_output = {
                    "rows_returned": 3,
                    "columns": ["user_id", "email", "status"],
                    "data": [
                        {"user_id": "u_101", "email": "alice@acme.com", "status": "active"},
                        {"user_id": "u_102", "email": "bob@globex.org", "status": "active"},
                        {"user_id": "u_103", "email": "carol@initech.io", "status": "active"},
                    ],
                    "query_plan": "Seq Scan on accounts (cost=0.00..1.20 rows=3 width=48)"
                }
            elif tool_def.provider == "Stripe":
                simulated_output = {
                    "id": "re_3MtwL24JyNd9_sub",
                    "object": "refund",
                    "amount": req.arguments.get("amount_cents", 450000),
                    "currency": "usd",
                    "status": "succeeded",
                    "receipt_number": "REC-991204"
                }
            elif tool_def.provider == "GitHub":
                simulated_output = {
                    "sha": "6dcb09b5b57875f334f61aebed695e2e4193db5e",
                    "merged": True,
                    "message": "Pull Request successfully merged and verified."
                }
            elif tool_def.provider == "Slack":
                simulated_output = {
                    "ok": True,
                    "channel": req.arguments.get("channel", "#general"),
                    "ts": "1728284912.001900",
                    "message": {"text": req.arguments.get("text", "Announcement broadcasted")}
                }
            else:
                simulated_output = {
                    "status": "executed",
                    "provider": tool_def.provider,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        return ProxyToolExecuteResponse(
            success=guardrail_res.verdict == "PERMIT",
            tool_id=tool_def.id,
            tool_name=tool_def.name,
            provider=tool_def.provider,
            guardrail_verdict=guardrail_res.verdict,
            permit_token=guardrail_res.permit_token,
            reasons=guardrail_res.reasons,
            risk_score=guardrail_res.risk_score,
            liability_prevented_usd=guardrail_res.liability_prevented_usd,
            simulated_output=simulated_output,
            execution_ms=guardrail_res.execution_ms,
        )


mcp_proxy_service = MCPProxyService()
