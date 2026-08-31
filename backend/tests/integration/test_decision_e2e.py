import asyncio
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
backend_dir = Path(__file__).resolve().parents[2]
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

import httpx

from app.db.database import AsyncSessionLocal
from app.db.repositories.data_source_repository import DataSourceRepository
from app.db.repositories.organization_repository import OrganizationRepository
from app.ingestion.connectors.confluence_connector import ConfluenceConnector
from app.ingestion.connectors.file_connector import FileConnector
from app.main import app


async def run_decision_e2e_test():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("\n========================================================")
        print("STARTING OUTDATED POLICY TRAP & DECISION GATE TEST")
        print("========================================================")

        # 1. Test the "Outdated Policy Trap" Decision Evaluation (PDF Demo)
        trap_payload = {
            "decision": "Determine whether customer is eligible for refund",
            "actor": {"id": "agent-42", "role": "support"},
            "context": [
                {
                    "claim": "Refund window is 30 days",
                    "source": "handbook.pdf",
                    "updated_at": "2025-11-04",
                    "authority_level": 50,
                },
                {
                    "claim": "Enterprise customers have a 60-day exception",
                    "source": "policy-service",
                    "updated_at": "2026-08-25",
                    "authority_level": 90,
                },
            ],
        }

        r_trap = await client.post("/v1/decisions/evaluate", json=trap_payload)
        assert r_trap.status_code == 200, f"Decision evaluate failed: {r_trap.text}"
        data_trap = r_trap.json()

        assert data_trap["decision"] == "REVIEW"
        assert data_trap["validity"] == "INSUFFICIENT"
        assert data_trap["risk"] == "HIGH"
        assert data_trap["preferred_source"] == "policy-service"
        assert len(data_trap["reasons"]) >= 2
        print(f"[PASS] 1. Outdated Policy Trap caught:")
        print(f"       - Decision: {data_trap['decision']} | Risk: {data_trap['risk']}")
        print(f"       - Preferred Source: {data_trap['preferred_source']}")
        print(f"       - Reasons: {data_trap['reasons']}")

        # 2. Test Authorized, Non-Conflicting Single Policy Evaluation
        allowed_payload = {
            "decision": "Determine whether customer is eligible for refund",
            "actor": {"id": "agent-42", "role": "support"},
            "context": [
                {
                    "claim": "Enterprise customers have a 60-day exception",
                    "source": "policy-service",
                    "updated_at": "2026-08-25",
                    "authority_level": 90,
                }
            ],
        }

        r_allow = await client.post("/v1/decisions/evaluate", json=allowed_payload)
        assert r_allow.status_code == 200
        data_allow = r_allow.json()
        assert data_allow["decision"] == "ALLOW"
        assert data_allow["validity"] == "VALID"
        assert data_allow["risk"] == "LOW"
        print(f"[PASS] 2. Clean Authoritative Policy Approved:")
        print(f"       - Decision: {data_allow['decision']} | Validity: {data_allow['validity']}")

        # 3. Test Unauthorized Role Block
        blocked_payload = {
            "decision": "Deploy infrastructure configuration change",
            "actor": {"id": "guest-bot", "role": "viewer"},
            "context": [
                {
                    "claim": "Production deploys require devops approval",
                    "source": "devops-runbook.md",
                    "updated_at": "2026-05-01",
                }
            ],
        }

        r_block = await client.post("/v1/decisions/evaluate", json=blocked_payload)
        assert r_block.status_code == 200
        data_block = r_block.json()
        assert data_block["decision"] == "BLOCK"
        assert data_block["risk"] == "HIGH"
        print(f"[PASS] 3. Unauthorized Agent Action Blocked:")
        print(f"       - Decision: {data_block['decision']} | Reason: {data_block['reasons'][0]}")

        # 4. Test Ingestion Connectors (FileConnector & ConfluenceConnector)
        test_id = uuid.uuid4().hex[:6]
        async with AsyncSessionLocal() as session:
            org_repo = OrganizationRepository(session)
            ds_repo = DataSourceRepository(session)

            org = await org_repo.get_or_create(
                name=f"Connector Corp {test_id}",
                slug=f"connector-corp-{test_id}",
            )
            ds_confluence = await ds_repo.get_or_create(
                organization_id=org.id,
                name="Official Confluence Wiki",
                source_type="confluence",
                external_id=f"conf-{test_id}",
                authority_level=90,
            )
            ds_file = await ds_repo.get_or_create(
                organization_id=org.id,
                name="Local Policy Files",
                source_type="file_storage",
                external_id=f"files-{test_id}",
                authority_level=60,
            )
            await session.commit()

            # Test Confluence Connector
            conf_connector = ConfluenceConnector(
                session=session,
                organization_id=org.id,
                source_id=ds_confluence.id,
                space_key="POLICIES",
            )
            synced_pages = await conf_connector.sync()
            assert len(synced_pages) >= 2
            await session.commit()
            print(f"[PASS] 4. Confluence Connector synced {len(synced_pages)} policy pages into PostgreSQL")

            # Test File Connector
            file_connector = FileConnector(
                session=session,
                organization_id=org.id,
                source_id=ds_file.id,
            )
            doc_file, ver_file = await file_connector.ingest_single_file(
                title="Employee Onboarding Rules",
                content="# Onboarding\n\nAll new hires must complete security training within 14 days.",
                external_id=f"file-onboarding-{test_id}",
            )
            assert ver_file.version_number == 1
            await session.commit()
            print(f"[PASS] 5. File Connector ingested local document: \"{doc_file.title}\" (Version {ver_file.version_number})")

        print("\n========================================================")
        print("ALL DECISION & CONNECTOR TESTS PASSED PERFECTLY!")
        print("========================================================\n")


if __name__ == "__main__":
    asyncio.run(run_decision_e2e_test())
