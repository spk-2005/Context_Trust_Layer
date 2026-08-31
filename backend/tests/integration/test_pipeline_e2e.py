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
from app.db.enums import UserRole
from app.db.models.agent import Agent
from app.db.models.user import User
from app.db.repositories.data_source_repository import DataSourceRepository
from app.db.repositories.organization_repository import OrganizationRepository
from app.main import app


async def run_full_pipeline_test():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        print("\n========================================================")
        print("STARTING CONTEXT TRUST LAYER FULL PIPELINE TEST")
        print("========================================================")

        # 1. Health Verification
        r = await client.get("/v1/health")
        assert r.status_code == 200, f"Health failed: {r.text}"
        print("[PASS] 1. Health check verified (Postgres + pgvector active)")

        # 2. Seed Organization, DataSource, Agent, Reviewer
        test_id = uuid.uuid4().hex[:6]
        async with AsyncSessionLocal() as session:
            org_repo = OrganizationRepository(session)
            ds_repo = DataSourceRepository(session)

            org = await org_repo.get_or_create(
                name=f"Trust Corp {test_id}",
                slug=f"trust-corp-{test_id}",
            )
            ds = await ds_repo.get_or_create(
                organization_id=org.id,
                name="Company Wiki",
                source_type="confluence",
                external_id=f"wiki-{test_id}",
                authority_level=90,
            )

            reviewer = User(
                organization_id=org.id,
                name=f"Alice Reviewer {test_id}",
                email=f"alice.{test_id}@example.com",
                role=UserRole.REVIEWER,
            )
            session.add(reviewer)

            agent = Agent(
                organization_id=org.id,
                name="HR Assistant Agent",
                agent_type="rag_assistant",
            )
            session.add(agent)

            await session.commit()
            await session.refresh(reviewer)
            await session.refresh(agent)

            org_id = str(org.id)
            ds_id = str(ds.id)
            reviewer_id = str(reviewer.id)
            agent_id = str(agent.id)

        print(f"[PASS] 2. Seeded Org, DataSource (Authority: 90), Reviewer, and Agent")

        # 3. Ingest Policy 2025 (2 days remote)
        doc_2025_payload = {
            "organization_id": org_id,
            "source_id": ds_id,
            "title": "Remote Work Policy 2025",
            "content": (
                "# Remote Work Rules\n\n"
                "Employees can work remotely up to 2 days per week.\n\n"
                "# Stipend\n\n"
                "Employees receive $300 home office equipment stipend."
            ),
            "document_type": "policy",
            "external_id": f"remote-policy-2025-{test_id}",
        }
        r_doc1 = await client.post("/v1/documents", json=doc_2025_payload)
        assert r_doc1.status_code == 201, f"Doc 1 failed: {r_doc1.text}"
        doc1_data = r_doc1.json()
        doc1_version_id = doc1_data["current_version"]["id"]
        print(f"[PASS] 3. Ingested Document 1 (2025 Policy, Version ID: {doc1_version_id})")

        # 4. Extract Claims & Score Trust for Doc 1
        r_extract1 = await client.post(f"/v1/claims/extract/{doc1_version_id}")
        assert r_extract1.status_code == 201, f"Extract 1 failed: {r_extract1.text}"
        claims1 = r_extract1.json()
        assert len(claims1) >= 2
        claim_2025_remote = next(c for c in claims1 if "2 days" in c["claim_text"])
        assert len(claim_2025_remote["evidence"]) > 0
        assert len(claim_2025_remote["trust_scores"]) > 0
        score_2025 = float(claim_2025_remote["trust_scores"][0]["overall_score"])
        assert score_2025 >= 0.80
        print(f"[PASS] 4. Extracted {len(claims1)} claims from Doc 1. Trust score: {score_2025:.4f}")

        # 5. Ingest Policy 2026 (4 days remote) - Conflicting with 2025!
        doc_2026_payload = {
            "organization_id": org_id,
            "source_id": ds_id,
            "title": "Remote Work Policy 2026",
            "content": (
                "# Remote Work Rules\n\n"
                "Employees can work remotely up to 4 days per week.\n\n"
                "# Stipend\n\n"
                "Employees receive $500 home office equipment stipend."
            ),
            "document_type": "policy",
            "external_id": f"remote-policy-2026-{test_id}",
        }
        r_doc2 = await client.post("/v1/documents", json=doc_2026_payload)
        assert r_doc2.status_code == 201
        doc2_data = r_doc2.json()
        doc2_version_id = doc2_data["current_version"]["id"]
        print(f"[PASS] 5. Ingested Document 2 (2026 Policy, Version ID: {doc2_version_id})")

        # 6. Extract Claims & Run Conflict Detection for Doc 2
        r_extract2 = await client.post(f"/v1/claims/extract/{doc2_version_id}")
        assert r_extract2.status_code == 201
        claims2 = r_extract2.json()
        print(f"[PASS] 6. Extracted {len(claims2)} claims from Doc 2 & Ran Conflict Detection")

        # 7. Check Detected Pending Conflicts
        r_conflicts = await client.get("/v1/conflicts/pending")
        assert r_conflicts.status_code == 200
        conflicts = r_conflicts.json()
        assert len(conflicts) > 0
        claim_2026_remote = next(c for c in claims2 if "4 days" in c["claim_text"])
        target_conflict = next(
            c for c in conflicts
            if c["claim_a_id"] in (claim_2025_remote["id"], claim_2026_remote["id"])
            or c["claim_b_id"] in (claim_2025_remote["id"], claim_2026_remote["id"])
        )
        conflict_id = target_conflict["id"]
        print(f"[PASS] 7. Conflict Detected: {target_conflict['conflict_type']} (Confidence: {target_conflict['confidence']})")

        # 8. Query Context as AI Agent During Conflict State
        query_payload = {
            "organization_id": org_id,
            "agent_id": agent_id,
            "query": "work remotely",
            "min_trust_score": 0.75,
            "max_results": 5,
        }
        r_ctx_before = await client.post("/v1/context/query", json=query_payload)
        assert r_ctx_before.status_code == 200
        ctx_before = r_ctx_before.json()
        # Conflicted claims should be filtered out to protect the agent from bad answers
        returned_texts = [item["claim"] for item in ctx_before["context"]]
        assert not any("2 days" in t for t in returned_texts)
        print("[PASS] 8. Agent Context Query during conflict: Conflicted statements safely excluded")

        # 9. Human Review / Resolve Conflict (Choose 2026 Claim)
        resolve_payload = {
            "reviewer_id": reviewer_id,
            "decision": "approve",
            "chosen_claim_id": claim_2026_remote["id"],
            "reason": "2026 Policy supersedes previous 2025 guidelines.",
        }
        r_resolve = await client.post(f"/v1/conflicts/{conflict_id}/resolve", json=resolve_payload)
        assert r_resolve.status_code == 200
        resolved_data = r_resolve.json()
        assert resolved_data["resolution_status"] == "resolved"
        print(f"[PASS] 9. Human Reviewer resolved conflict -> Approved 2026 policy, marked 2025 outdated")

        # 10. Query Context as AI Agent After Resolution
        r_ctx_after = await client.post("/v1/context/query", json=query_payload)
        assert r_ctx_after.status_code == 200
        ctx_after = r_ctx_after.json()
        assert len(ctx_after["context"]) > 0
        resolved_context_item = next((item for item in ctx_after["context"] if "4 days" in item["claim"]), None)
        assert resolved_context_item is not None
        assert float(resolved_context_item["trust_score"]) >= 0.80
        assert resolved_context_item["source"]["document"] == "Remote Work Policy 2026"
        print(f"[PASS] 10. Agent Context Query after resolution: Verified 2026 policy served with full citations:")
        print(f"       - Claim: \"{resolved_context_item['claim']}\"")
        print(f"       - Trust Score: {resolved_context_item['trust_score']}")
        print(f"       - Provenance: {resolved_context_item['source']['document']} (Section: {resolved_context_item['source']['section']})")
        print(f"       - Evidence Quote: \"{resolved_context_item['evidence'][0]}\"")

        print("\n========================================================")
        print("ALL 10 PIPELINE STEPS PASSED PERFECTLY!")
        print("========================================================\n")


if __name__ == "__main__":
    asyncio.run(run_full_pipeline_test())
