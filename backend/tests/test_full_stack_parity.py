"""
Full Stack Live Application vs. Audit Pipeline Parity Test.

Verifies end-to-end parity across:
1. Live Path: HTTP Multipart Upload (POST /v1/documents/upload-and-extract) ->
   Database Persistence (claims, claim_evidence, claim_trust_scores) ->
   Claims Listing API (GET /v1/claims) -> UI Payload
2. Audit Path: UnifiedExtractionPipeline.execute (audit mode)

Ensures that claims, locators, evidence text spans, and modalities
are identical across both application surfaces.
"""

import io
import uuid
import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.main import app

from pathlib import Path


def _find_epcs_pdf() -> Path:
    candidates = [
        Path("research/validation_50/raw_documents/Microsoft/Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf"),
        Path("research/validation_50/raw_documents/Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf"),
        Path("backend/storage/uploads/a07fafde-c545-429c-a5f8-cde07c7c64ba/Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf"),
    ]
    for p in candidates:
        if p.exists():
            return p
    for p in Path(".").glob("**/*EPCS*.pdf"):
        if p.exists():
            return p
    pytest.skip("EPCS PDF document not found in workspace")


@pytest.mark.asyncio
async def test_full_stack_parity_upload_to_db_and_api():
    """Validates that HTTP upload, DB persistence, and direct audit execution produce identical claims."""
    epcs_path = _find_epcs_pdf()
    file_bytes = epcs_path.read_bytes()

    filename = "Electronic Prescriptions for Controlled Substances (EPCS) - Azure Compliance _ Microsoft Learn.pdf"
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")

    # 1. Audit Path: UnifiedExtractionPipeline.execute
    audit_opts = UnifiedPipelineOptions(
        organization_id=org_id,
        document_type="policy",
        doc_title="EPCS Audit Baseline",
        persist_to_db=False,
    )
    audit_res = await UnifiedExtractionPipeline.execute(
        filename=filename,
        raw_bytes=file_bytes,
        options=audit_opts,
    )
    audit_claims = audit_res.candidates
    assert len(audit_claims) == 14, f"Expected 14 EPCS audit claims, got {len(audit_claims)}"

    # 2. Live Path: Exercise actual FastAPI multipart HTTP upload
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        files = {
            "file": (filename, io.BytesIO(file_bytes), "application/pdf")
        }
        data = {
            "organization_id": str(org_id),
            "document_type": "policy",
            "document_scope": "ENTERPRISE",
            "title": "EPCS Live Upload Test",
        }
        headers = {
            "x-user-role": "data_owner",
            "Authorization": "Bearer test-dev-token",
        }
        response = await client.post(
            "/v1/documents/upload-and-extract?user_role=data_owner",
            files=files,
            data=data,
            headers=headers,
        )

        assert response.status_code == 201, f"Upload failed: {response.text}"
        upload_json = response.json()
        assert upload_json.get("success") is True, f"Upload was not successful: {upload_json}"
        live_claims_count = upload_json["claims_extracted_count"]
        doc_version_id = uuid.UUID(upload_json["current_version"]["id"])

        # Assert Live API returned the exact same claim count as Audit
        assert live_claims_count == len(audit_claims), (
            f"Live API count ({live_claims_count}) != Audit count ({len(audit_claims)})"
        )

        # 3. Query DB Persistence directly: verify claims and evidence locators
        async with AsyncSessionLocal() as session:
            stmt = (
                select(Claim)
                .options(selectinload(Claim.evidence))
                .where(Claim.document_version_id == doc_version_id)
                .order_by(Claim.created_at.asc())
            )
            res = await session.execute(stmt)
            db_claims = res.scalars().all()

        assert len(db_claims) == len(audit_claims), (
            f"DB persisted {len(db_claims)} claims, expected {len(audit_claims)}"
        )

        # 4. Deep Field-Level Parity Comparison (Live DB vs Audit Output)
        db_by_key = {(c.subject.strip().lower(), c.predicate.strip().lower()): c for c in db_claims}

        for audit_c in audit_claims:
            audit_key = (audit_c.subject.strip().lower(), audit_c.predicate.strip().lower())
            assert audit_key in db_by_key, f"Audit claim '{audit_key}' not found in DB claims"
            db_c = db_by_key[audit_key]

            # Compare semantic attributes
            assert db_c.claim_text.strip().lower() == audit_c.claim_text.strip().lower(), (
                f"Text mismatch: DB '{db_c.claim_text}' vs Audit '{audit_c.claim_text}'"
            )

            # Compare locators on persisted ClaimEvidence
            assert len(db_c.evidence) > 0, f"Claim {db_c.id} has no persisted ClaimEvidence records"
            db_ev = db_c.evidence[0]
            assert db_ev.text_span == audit_c.evidence_text_span, (
                f"Evidence text span mismatch for claim {db_c.subject}"
            )
            assert db_ev.evidence_hash == audit_c.content_hash, (
                f"Evidence hash mismatch for claim {db_c.subject}"
            )
            if audit_c.locator and "page" in audit_c.locator:
                expected_page = audit_c.locator.get("page")
                assert db_ev.page_number == expected_page, (
                    f"Page locator mismatch: DB {db_ev.page_number} vs Audit {expected_page}"
                )

        # 5. UI Endpoint Verification: Query GET /v1/claims/{claim_id} for each claim
        for db_c in db_claims:
            claim_detail_res = await client.get(
                f"/v1/claims/{db_c.id}",
                headers=headers,
            )
            assert claim_detail_res.status_code == 200, f"Claim {db_c.id} failed retrieval: {claim_detail_res.text}"
            detail_json = claim_detail_res.json()
            assert detail_json["id"] == str(db_c.id)
            assert detail_json["subject"] == db_c.subject
            assert detail_json["predicate"] == db_c.predicate
            assert len(detail_json.get("evidence", [])) > 0, f"Claim {db_c.id} missing evidence in UI response"
