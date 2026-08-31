import hashlib
import re
import unicodedata
import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from app.normalization.metadata import build_metadata
from app.normalization.validators import validate_normalized_document


class DocumentType(str, Enum):
    JIRA_ISSUE = "jira_issue"
    GITHUB_ISSUE = "github_issue"
    GITHUB_PULL_REQUEST = "github_pull_request"
    SLACK_MESSAGE = "slack_message"
    CONFLUENCE_PAGE = "confluence_page"
    DOCUMENT = "document"
    POLICY = "policy"


class NormalizedDocument(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    organization_id: uuid.UUID
    source_id: uuid.UUID
    external_id: str | None = None
    document_type: str
    title: str
    content: str
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DocumentNormalizer:
    """Normalizes heterogeneous raw enterprise documents into canonical NormalizedDocument representation."""

    @staticmethod
    def clean_text(raw_text: str) -> str:
        if not raw_text:
            return ""

        # 1. Unicode normalization (NFKC)
        text = unicodedata.normalize("NFKC", raw_text)

        # 2. Normalize carriage returns / line feeds
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Clean up excessive spaces per line while preserving paragraphs
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

        # 4. Collapse multiple blank lines into max 2 newlines
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    @staticmethod
    def compute_content_hash(content: str) -> str:
        """SHA-256 deterministic hash helper for downstream content_hash matching DB schema."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def normalize(
        self,
        title: str,
        content: str,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        document_type: str | DocumentType = DocumentType.DOCUMENT,
        external_id: str | None = None,
        author: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        id: uuid.UUID | None = None,
    ) -> NormalizedDocument:
        cleaned_title = title.strip() if title else ""
        cleaned_content = self.clean_text(content)

        doc_type_str = (
            document_type.value
            if isinstance(document_type, DocumentType)
            else str(document_type).lower().strip()
        )

        sanitized_metadata = build_metadata(metadata)

        doc = NormalizedDocument(
            id=id or uuid.uuid4(),
            organization_id=organization_id,
            source_id=source_id,
            external_id=external_id.strip() if external_id else None,
            document_type=doc_type_str,
            title=cleaned_title,
            content=cleaned_content,
            author=author.strip() if author else None,
            created_at=created_at,
            updated_at=updated_at,
            metadata=sanitized_metadata,
        )

        validate_normalized_document(doc)
        return doc

