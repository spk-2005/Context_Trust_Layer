import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx

from app.main import app
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.enums import RecordStatus
from app.normalization.normalizer import NormalizedDocument


@pytest.mark.asyncio
async def test_api_create_document_normalization():
    transport = httpx.ASGITransport(app=app)
    doc_id = uuid.uuid4()
    version_id = uuid.uuid4()
    org_id = uuid.uuid4()
    source_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    mock_doc = Document(
        id=doc_id,
        organization_id=org_id,
        source_id=source_id,
        external_id="JIRA-104",
        title="JIRA-104: Secure Token Handling",
        document_type="jira_issue",
        content_uri="All access tokens must be stored in secrets vault.",
        content_hash="mockhash",
        status=RecordStatus.ACTIVE,
        created_at=now,
        updated_at=now,
    )
    mock_version = DocumentVersion(
        id=version_id,
        document_id=doc_id,
        version_number=1,
        content_uri="All access tokens must be stored in secrets vault.",
        content_hash="mockhash",
        is_current=True,
        created_at=now,
        modified_at=now,
    )
    mock_normalized = NormalizedDocument(
        id=doc_id,
        organization_id=org_id,
        source_id=source_id,
        external_id="JIRA-104",
        document_type="jira_issue",
        title="JIRA-104: Secure Token Handling",
        content="All access tokens must be stored in secrets vault.",
        created_at=now,
        updated_at=now,
    )

    with patch(
        "app.api.v1.documents.DocumentIngestionService.ingest_document",
        new_callable=AsyncMock,
        return_value=(mock_doc, mock_version, mock_normalized),
    ):
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            payload = {
                "organization_id": str(org_id),
                "source_id": str(source_id),
                "title": "  JIRA-104: Secure Token Handling  ",
                "content": "All access tokens must be stored in secrets vault.",
                "document_type": "jira_issue",
                "external_id": "JIRA-104",
                "metadata": {"priority": "High"},
            }

            res = await client.post("/v1/documents", json=payload)
            assert res.status_code == 201, f"Failed POST /v1/documents: {res.text}"
            data = res.json()

            assert data["normalized"] is True
            assert "jira_issue" in data["message"]
            doc = data["document"]
            assert doc["title"] == "JIRA-104: Secure Token Handling"


@pytest.mark.asyncio
async def test_api_create_document_validation_error():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = {
            "organization_id": str(uuid.uuid4()),
            "source_id": str(uuid.uuid4()),
            "title": "   ",
            "content": "Sample content",
            "document_type": "policy",
        }

        res = await client.post("/v1/documents", json=payload)
        assert res.status_code == 422
        assert "title cannot be empty" in res.text
