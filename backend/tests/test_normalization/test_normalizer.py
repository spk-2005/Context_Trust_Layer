import uuid
from datetime import datetime, timezone
import pytest

from app.normalization.normalizer import DocumentNormalizer, DocumentType, NormalizedDocument


def test_normalizer_uuid_generation():
    normalizer = DocumentNormalizer()
    org_id = uuid.uuid4()
    source_id = uuid.uuid4()

    doc = normalizer.normalize(
        title="Test Document",
        content="This is sample content.",
        organization_id=org_id,
        source_id=source_id,
    )

    assert isinstance(doc.id, uuid.UUID)
    assert doc.organization_id == org_id
    assert doc.source_id == source_id


def test_normalizer_custom_uuid():
    normalizer = DocumentNormalizer()
    custom_id = uuid.uuid4()
    org_id = uuid.uuid4()
    source_id = uuid.uuid4()

    doc = normalizer.normalize(
        title="Custom ID Doc",
        content="Sample content",
        organization_id=org_id,
        source_id=source_id,
        id=custom_id,
    )

    assert doc.id == custom_id


def test_normalizer_whitespace_and_paragraph_trimming():
    normalizer = DocumentNormalizer()
    org_id = uuid.uuid4()
    source_id = uuid.uuid4()

    raw_title = "   Whitespace Title   "
    raw_content = "   Line 1 with trailing spaces.   \r\n\r\n\r\nLine 2 after multiple blank lines.   \n\n\nLine 3.   "

    doc = normalizer.normalize(
        title=raw_title,
        content=raw_content,
        organization_id=org_id,
        source_id=source_id,
    )

    assert doc.title == "Whitespace Title"
    assert "Line 1 with trailing spaces." in doc.content
    assert "Line 2 after multiple blank lines." in doc.content
    assert "Line 3." in doc.content


def test_normalizer_metadata_and_author_preservation():
    normalizer = DocumentNormalizer()
    org_id = uuid.uuid4()
    source_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    doc = normalizer.normalize(
        title="Authored Document",
        content="Document content",
        organization_id=org_id,
        source_id=source_id,
        author="  Jane Doe  ",
        external_id="  EXT-123  ",
        created_at=now,
        updated_at=now,
        metadata={"priority": "High", "labels": ["security", "audit"]},
    )

    assert doc.author == "Jane Doe"
    assert doc.external_id == "EXT-123"
    assert doc.created_at == now
    assert doc.updated_at == now
    assert doc.metadata["priority"] == "High"
    assert doc.metadata["labels"] == ["security", "audit"]


def test_multi_source_canonicalization():
    normalizer = DocumentNormalizer()
    org_id = uuid.uuid4()
    source_id = uuid.uuid4()

    # 1. Jira Issue
    jira_doc = normalizer.normalize(
        title="PROJ-101: Fix authentication bypass",
        content="Detailed vulnerability analysis and resolution steps.",
        organization_id=org_id,
        source_id=source_id,
        document_type=DocumentType.JIRA_ISSUE,
        external_id="PROJ-101",
        author="alex@enterprise.com",
        metadata={"priority": "P1", "status": "In Progress"},
    )

    # 2. GitHub Issue
    github_doc = normalizer.normalize(
        title="Fix authentication bypass",
        content="Detailed vulnerability analysis and resolution steps.",
        organization_id=org_id,
        source_id=source_id,
        document_type=DocumentType.GITHUB_ISSUE,
        external_id="issue-42",
        author="alex-dev",
        metadata={"repo": "security-service", "labels": ["bug", "critical"]},
    )

    # 3. Slack Message
    slack_doc = normalizer.normalize(
        title="Security alert regarding auth bypass",
        content="Detailed vulnerability analysis and resolution steps.",
        organization_id=org_id,
        source_id=source_id,
        document_type=DocumentType.SLACK_MESSAGE,
        external_id="msg-9988",
        author="slack-bot",
        metadata={"channel_id": "C0123456"},
    )

    # All produce canonical NormalizedDocument instances with standardized attributes
    for doc in [jira_doc, github_doc, slack_doc]:
        assert isinstance(doc, NormalizedDocument)
        assert doc.organization_id == org_id
        assert doc.source_id == source_id
        assert doc.content == "Detailed vulnerability analysis and resolution steps."


def test_compute_content_hash():
    normalizer = DocumentNormalizer()
    content = "Deterministic content string"
    hash1 = normalizer.compute_content_hash(content)
    hash2 = normalizer.compute_content_hash(content)

    assert hash1 == hash2
    assert len(hash1) == 64  # SHA-256 hex string length
