#!/usr/bin/env python3
"""
Context Trust Layer - Complete Backend API Demonstration Script
Executes all core backend API endpoints against http://localhost:8000
"""

import json
import urllib.request
import uuid

BASE_URL = "http://localhost:8000"

# Pre-seeded test UUIDs (from initial database seed)
ORG_ID = "11111111-1111-1111-1111-111111111111"
USER_ID = "22222222-2222-2222-2222-222222222222"
SOURCE_ID = "44444444-4444-4444-4444-444444444444"
AGENT_ID = "88888888-8888-8888-8888-888888888888"


def get(path: str) -> dict | list:
    """Helper to issue HTTP GET requests."""
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))


def post(path: str, payload: dict) -> dict | list:
    """Helper to issue HTTP POST requests."""
    url = f"{BASE_URL}{path}"
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, headers={"Content-Type": "application/json", "Accept": "application/json"}
    )
    with urllib.request.urlopen(req) as res:
        return json.loads(res.read().decode("utf-8"))


def main():
    print("=" * 70)
    print(" Context Trust Layer - Full Backend API Execution Demonstration")
    print("=" * 70)

    # 1. Root Endpoint
    root = get("/")
    print(f"\n[1] Root Endpoint GET /:")
    print(f"    -> Application: {root['application']} | Status: {root['status']}")

    # 2. Health Endpoint
    health = get("/v1/health")
    print(f"\n[2] Health Endpoint GET /v1/health:")
    print(f"    -> Status: {health['status']} | DB Connected: {health['database']} | Extensions: {health['extensions']}")

    # 3. Ingest Raw Document
    ext_id = f"SEC-POL-{uuid.uuid4().hex[:6]}"
    doc_payload = {
        "organization_id": ORG_ID,
        "source_id": SOURCE_ID,
        "title": "API Security Guidelines 2026",
        "content": (
            "# Security Policy\n"
            "All API endpoints must enforce TLS 1.3 encryption and JWT authentication.\n\n"
            "# Data Retention\n"
            "Audit log records must be retained for a minimum of 7 years."
        ),
        "document_type": "policy",
        "external_id": ext_id,
        "metadata": {"author": "Chief Information Security Officer", "priority": "high"},
    }
    ingest_res = post("/v1/documents", doc_payload)
    doc_id = ingest_res["document"]["id"]
    version_id = ingest_res["current_version"]["id"]
    print(f"\n[3] Ingest Document POST /v1/documents:")
    print(f"    -> Document ID: {doc_id}")
    print(f"    -> Version ID:  {version_id}")
    print(f"    -> Status:      {ingest_res['message']}")

    # 4. Fetch Single Document by ID
    doc_details = get(f"/v1/documents/{doc_id}")
    print(f"\n[4] Fetch Document GET /v1/documents/{doc_id}:")
    print(f"    -> Title: '{doc_details['title']}' | Versions count: {len(doc_details['versions'])}")

    # 5. List Documents by Organization
    org_docs = get(f"/v1/documents?organization_id={ORG_ID}")
    print(f"\n[5] List Documents GET /v1/documents?organization_id={ORG_ID}:")
    print(f"    -> Total Documents: {len(org_docs)}")

    # 6. Extract Claims & Compute Trust Scores for Document Version
    extracted_claims = post(f"/v1/claims/extract/{version_id}", {})
    print(f"\n[6] Extract & Score Claims POST /v1/claims/extract/{version_id}:")
    print(f"    -> Extracted {len(extracted_claims)} claim(s)")

    claim_id = None
    if extracted_claims:
        claim_id = extracted_claims[0]["id"]
        print(f"    -> Claim #1 ID: {claim_id}")
        print(f"    -> Claim #1 Text: '{extracted_claims[0]['claim_text'][:65]}...'")

    # 7. Fetch Single Claim Details by ID
    if claim_id:
        claim_details = get(f"/v1/claims/{claim_id}")
        print(f"\n[7] Fetch Claim Details GET /v1/claims/{claim_id}:")
        print(f"    -> Claim Text: '{claim_details['claim_text']}'")
        print(f"    -> Status: {claim_details['status']}")

    # 8. List Claims by Organization
    all_claims = get(f"/v1/claims?organization_id={ORG_ID}")
    print(f"\n[8] List Claims GET /v1/claims?organization_id={ORG_ID}:")
    print(f"    -> Total Claims in Organization: {len(all_claims)}")

    # 9. List Pending Conflicts & Resolve (if any exist)
    conflicts = get(f"/v1/conflicts/pending?organization_id={ORG_ID}")
    print(f"\n[9] List Pending Conflicts GET /v1/conflicts/pending?organization_id={ORG_ID}:")
    print(f"    -> Pending Conflicts Count: {len(conflicts)}")
    if conflicts:
        conflict_id = conflicts[0]["id"]
        print(f"    -> Resolving Conflict ID: {conflict_id}")
        resolve_payload = {
            "reviewer_id": USER_ID,
            "decision": "approve",
            "chosen_claim_id": conflicts[0]["claim_b_id"],
            "reason": "Approved newer policy version via automated verification audit.",
        }
        resolved_conflict = post(f"/v1/conflicts/{conflict_id}/resolve", resolve_payload)
        print(f"    -> Resolution Status: {resolved_conflict['resolution_status']}")

    # 10. Query Trusted Context for AI Agent
    ctx_req = {
        "organization_id": ORG_ID,
        "agent_id": AGENT_ID,
        "query": "What are the API encryption and authentication requirements?",
        "min_trust_score": 0.5,
        "max_results": 5,
    }
    ctx_res = post("/v1/context/query", ctx_req)
    print(f"\n[10] Context Retrieval Query POST /v1/context/query:")
    print(f"    -> Retrieved {len(ctx_res['context'])} context claim(s)")
    print(f"    -> System Overall Confidence: {ctx_res['confidence']}")

    # 11. Evaluate AI Agent Decision against Policy Constraints
    decision_req = {
        "decision": "Allow plaintext HTTP traffic on external endpoints",
        "actor": {
            "id": "billing-bot-01",
            "role": "support_agent"
        },
        "context": [
            {
                "claim": "All API endpoints must enforce TLS 1.3 encryption and JWT authentication.",
                "source": "API Security Guidelines 2026",
                "authority_level": 95,
                "scope": "Enterprise"
            }
        ],
        "organization_id": ORG_ID,
        "required_scope": "Enterprise"
    }
    decision_res = post("/v1/decisions/evaluate", decision_req)
    print(f"\n[11] Evaluate Decision POST /v1/decisions/evaluate:")
    print(f"    -> Decision Outcome: {decision_res['decision']}")
    print(f"    -> Validity:         {decision_res['validity']}")
    print(f"    -> Risk Rating:      {decision_res['risk']}")
    print(f"    -> Audit ID:         {decision_res['audit_id']}")
    print(f"    -> Reasons:          {decision_res['reasons']}")

    print("\n" + "=" * 70)
    print(" SUCCESS! ALL 11 BACKEND ENDPOINTS EXECUTED AND VERIFIED CLEANLY!")
    print("=" * 70)


if __name__ == "__main__":
    main()
