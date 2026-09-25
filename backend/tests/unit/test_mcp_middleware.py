import pytest

from app.schemas.mcp_middleware import (
    ToolCallProposal,
    ToolRiskTier,
    WorkflowPlanEvaluateRequest,
    WorkflowPlanStep,
)
from app.services.mcp_middleware_service import (
    classify_tool_tier,
    intercept_tool_call,
    evaluate_workflow_plan,
)


def test_classify_tool_tier():
    assert classify_tool_tier("fetch_user_profile") == ToolRiskTier.TIER_1_READ_ONLY
    assert classify_tool_tier("add_comment") == ToolRiskTier.TIER_2_MUTATING_LOW
    assert classify_tool_tier("execute_sql") == ToolRiskTier.TIER_3_MUTATING_HIGH
    assert classify_tool_tier("shell_exec") == ToolRiskTier.TIER_4_DANGEROUS
    assert classify_tool_tier("wire_transfer") == ToolRiskTier.TIER_4_DANGEROUS


@pytest.mark.asyncio
async def test_intercept_safe_read_tool():
    proposal = ToolCallProposal(
        tool_name="get_customer_history",
        arguments={"customer_id": "cust_123"},
        actor_id="support-agent-1",
        actor_role="support",
    )
    result = await intercept_tool_call(proposal)
    assert result.verdict == "PERMIT"
    assert result.risk_tier == ToolRiskTier.TIER_1_READ_ONLY
    assert result.permit_token is not None
    assert result.permit_token.startswith("permit_")


@pytest.mark.asyncio
async def test_intercept_sql_injection_arguments():
    proposal = ToolCallProposal(
        tool_name="query_database",
        arguments={"query": "SELECT * FROM orders; DROP TABLE users; --"},
        actor_id="analyst-bot",
        actor_role="developer",
    )
    result = await intercept_tool_call(proposal)
    assert result.verdict == "BLOCK"
    assert result.risk_tier == ToolRiskTier.TIER_4_DANGEROUS
    assert any("SQL Injection" in r for r in result.reasons)
    assert result.liability_prevented_usd > 0


@pytest.mark.asyncio
async def test_intercept_dangerous_tool_unauthorized_role():
    proposal = ToolCallProposal(
        tool_name="shell_command_runner",
        arguments={"cluster": "prod-cluster-01"},
        actor_id="junior-bot",
        actor_role="support",
    )
    result = await intercept_tool_call(proposal)
    assert result.verdict == "BLOCK"
    assert result.risk_tier == ToolRiskTier.TIER_4_DANGEROUS
    assert any("Separation of Duties" in r for r in result.reasons)


@pytest.mark.asyncio
async def test_intercept_financial_ceiling():
    proposal = ToolCallProposal(
        tool_name="process_refund",
        arguments={"amount": 4500.0, "invoice_id": "inv_998"},
        actor_id="refund-bot",
        actor_role="support",
    )
    result = await intercept_tool_call(proposal)
    assert result.verdict == "REQUIRE_REVIEW"
    assert result.liability_prevented_usd == 4500.0


@pytest.mark.asyncio
async def test_evaluate_multi_step_workflow():
    safe_plan = WorkflowPlanEvaluateRequest(
        workflow_id="wf-test-safe",
        goal="Assist customer with billing inquiry",
        actor_id="agent-01",
        actor_role="support",
        steps=[
            WorkflowPlanStep(step_id=1, tool_name="get_ticket", arguments={"id": "tk1"}),
            WorkflowPlanStep(step_id=2, tool_name="search_knowledge", arguments={"query": "refund policy"}),
            WorkflowPlanStep(step_id=3, tool_name="add_comment", arguments={"note": "Reviewed policy"}),
        ]
    )
    resp = await evaluate_workflow_plan(safe_plan)
    assert resp.verdict == "PERMIT"
    assert len(resp.step_evaluations) == 3

    malicious_plan = WorkflowPlanEvaluateRequest(
        workflow_id="wf-test-breach",
        goal="Automated system maintenance",
        actor_id="agent-02",
        actor_role="support",
        steps=[
            WorkflowPlanStep(step_id=1, tool_name="get_ticket", arguments={"id": "tk2"}),
            WorkflowPlanStep(step_id=2, tool_name="execute_sql", arguments={"query": "TRUNCATE audit_logs"}),
        ]
    )
    resp_mal = await evaluate_workflow_plan(malicious_plan)
    assert resp_mal.verdict == "BLOCK"
