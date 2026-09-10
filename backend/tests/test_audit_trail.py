import pytest
import httpx
from app.main import app

DEMO_ORG_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.anyio
async def test_audit_summary_endpoint():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get(f"/v1/audit/summary?organization_id={DEMO_ORG_ID}")
        assert res.status_code == 200
        data = res.json()
        assert "total_decisions" in data
        assert "allow_rate_pct" in data
        assert "cryptographic_token_verified" in data
        assert data["cryptographic_token_verified"] is True


@pytest.mark.anyio
async def test_evaluate_and_audit_lineage_flow():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Trigger an evaluation via decisions API
        eval_payload = {
            "decision": "Approve $5,000 enterprise SLA credit refund",
            "actor": {"id": "agent-compliance-qa", "role": "billing_agent"},
            "context": [
                {
                    "claim": "Enterprise refund policy max approval by billing agent is $10,000",
                    "source": "handbook.pdf",
                    "authority_level": 90,
                    "scope": "Enterprise"
                }
            ],
            "organization_id": DEMO_ORG_ID
        }
        eval_res = await client.post("/v1/decisions/evaluate", json=eval_payload)
        assert eval_res.status_code == 200
        eval_data = eval_res.json()
        assert "decision" in eval_data
        assert eval_data["decision"] == "ALLOW"
        assert "audit_token" in eval_data
        assert len(eval_data["audit_token"]) == 64  # SHA-256 hash length

        # 2. Query audit logs list to find the logged evaluation
        logs_res = await client.get(f"/v1/audit/logs?organization_id={DEMO_ORG_ID}&limit=10")
        assert logs_res.status_code == 200
        logs_data = logs_res.json()
        assert logs_data["total"] >= 1
        assert len(logs_data["logs"]) >= 1

        target_log = None
        for log in logs_data["logs"]:
            if log["decision_prompt"] == "Approve $5,000 enterprise SLA credit refund":
                target_log = log
                break

        assert target_log is not None
        assert target_log["actor_id"] == "agent-compliance-qa"
        assert target_log["audit_token"] == eval_data["audit_token"]

        # 3. Query decision lineage by audit_id
        audit_id = target_log["audit_id"]
        lineage_res = await client.get(f"/v1/audit/{audit_id}/lineage")
        assert lineage_res.status_code == 200
        lineage_data = lineage_res.json()
        assert lineage_data["audit_id"] == audit_id
        assert lineage_data["stage_1_actor"]["actor_role"] == "billing_agent"
        assert lineage_data["stage_2_evidence"]["total_candidate_claims"] >= 1
        assert "stage_3_contradiction" in lineage_data
        assert lineage_data["stage_4_verdict"]["audit_token"] == eval_data["audit_token"]


@pytest.mark.anyio
async def test_audit_export_json_and_csv():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # JSON export
        res_json = await client.get(f"/v1/audit/export?organization_id={DEMO_ORG_ID}&format=json")
        assert res_json.status_code == 200
        assert res_json.headers["content-type"] == "application/json"
        export_data = res_json.json()
        assert "report_metadata" in export_data
        assert "audit_logs" in export_data
        assert export_data["report_metadata"]["compliance_standards"] == [
            "SOC2 Type II", "ISO/IEC 42001 (AI Management System)", "EU AI Act Article 12"
        ]

        # CSV export
        res_csv = await client.get(f"/v1/audit/export?organization_id={DEMO_ORG_ID}&format=csv")
        assert res_csv.status_code == 200
        assert "text/csv" in res_csv.headers["content-type"]
        assert "Audit ID,Timestamp,Actor ID" in res_csv.text
