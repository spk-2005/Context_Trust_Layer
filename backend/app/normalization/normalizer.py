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


class DocumentSection(BaseModel):
    title: str
    content: str
    level: int = 1
    page_number: int | None = 1
    start_char_offset: int = 0
    end_char_offset: int = 0


class NormalizedDocument(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    organization_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    source_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    external_id: str | None = None
    document_type: str = "document"
    title: str
    content: str
    author: str | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    sections: list[DocumentSection] = Field(default_factory=list)
    total_characters: int = 0
    total_words: int = 0


class DocumentNormalizer:
    """Normalizes heterogeneous raw enterprise documents into canonical NormalizedDocument representation."""

    @staticmethod
    def clean_text(raw_text: str) -> str:
        if not raw_text:
            return ""

        # 0. Strip null bytes (PostgreSQL UTF-8 restriction)
        text = raw_text.replace("\x00", "")

        # 1. Unicode normalization (NFKC)
        text = unicodedata.normalize("NFKC", text)

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
        sanitized = content.replace("\x00", "") if content else ""
        return hashlib.sha256(sanitized.encode("utf-8")).hexdigest()

    @staticmethod
    def scrub_noise(text: str) -> str:
        """Scrub document boilerplate, greetings, table of contents, and structural artifacts before extraction."""
        if not text:
            return ""
        lines = text.split("\n")
        cleaned_lines = []
        boilerplate_patterns = [
            re.compile(r"^table of contents", re.IGNORECASE),
            re.compile(r"^page\s+\d+(\s+of\s+\d+)?", re.IGNORECASE),
            re.compile(r"^copyright\s+(©|\(c\))?\s*\d{4}", re.IGNORECASE),
            re.compile(r"^all rights reserved", re.IGNORECASE),
            re.compile(r"^(hi|hello|dear)\s+(team|all|everyone|colleagues)[\s,!:]*$", re.IGNORECASE),
            re.compile(r"^please (note|find|refer to) (the following|below|attached)[\s,!:]*$", re.IGNORECASE),
            re.compile(r"^[-=_]{3,}$"),
        ]
        for line in lines:
            stripped = line.strip()
            if not stripped:
                cleaned_lines.append("")
                continue
            if any(p.search(stripped) for p in boilerplate_patterns):
                continue
            cleaned_lines.append(line)
        result = "\n".join(cleaned_lines)
        return re.sub(r"\n{3,}", "\n\n", result).strip()

    @staticmethod
    def parse_sections(raw_text: str) -> list[DocumentSection]:
        if not raw_text:
            return []

        # 1. Structured JSON dataset parser (extracts clean document claims instead of raw code)
        stripped_raw = raw_text.strip()
        if (stripped_raw.startswith("{") and stripped_raw.endswith("}")) or (stripped_raw.startswith("[") and stripped_raw.endswith("]")):
            try:
                import json
                data = json.loads(stripped_raw)
                if isinstance(data, dict) and "documents" in data:
                    json_sections = []
                    sec_offset = 0
                    for doc in data.get("documents", []):
                        title = doc.get("title", "Policy Section")
                        doc_claims = [c.get("claim") for c in doc.get("claims", []) if c.get("claim")]
                        if doc_claims:
                            body = "\n".join(f"- {c}" for c in doc_claims)
                        else:
                            body = doc.get("version_2_current_text") or doc.get("version_1_legacy_text") or ""

                        if body.strip():
                            json_sections.append(
                                DocumentSection(
                                    title=title,
                                    content=body.strip(),
                                    level=1,
                                    start_char_offset=sec_offset,
                                    end_char_offset=sec_offset + len(body.strip()),
                                )
                            )
                            sec_offset += len(body.strip()) + 1
                    if json_sections:
                        return json_sections
            except Exception:
                pass

        lines = raw_text.split("\n")
        header_pattern = re.compile(r"^(#{1,6})\s+(.*)$")

        sections: list[DocumentSection] = []
        current_title: str | None = None
        current_level: int = 1
        current_content_lines: list[str] = []
        current_start: int = 0

        has_headers = any(header_pattern.match(line.strip()) for line in lines)

        if not has_headers:
            paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
            if len(raw_text) > 2500 and len(paragraphs) > 1:
                chunk_sections: list[DocumentSection] = []
                current_chunk: list[str] = []
                current_len = 0
                chunk_idx = 1
                offset = 0
                for p in paragraphs:
                    if current_len + len(p) > 2000 and current_chunk:
                        chunk_text = "\n\n".join(current_chunk)
                        chunk_sections.append(
                            DocumentSection(
                                title=f"Section {chunk_idx}",
                                content=chunk_text,
                                level=2,
                                start_char_offset=offset,
                                end_char_offset=offset + len(chunk_text),
                            )
                        )
                        offset += len(chunk_text) + 2
                        chunk_idx += 1
                        current_chunk = []
                        current_len = 0
                    current_chunk.append(p)
                    current_len += len(p)
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    chunk_sections.append(
                        DocumentSection(
                            title=f"Section {chunk_idx}",
                            content=chunk_text,
                            level=2,
                            start_char_offset=offset,
                            end_char_offset=offset + len(chunk_text),
                        )
                    )
                return chunk_sections
            return [
                DocumentSection(
                    title="General",
                    content=raw_text,
                    level=1,
                    start_char_offset=0,
                    end_char_offset=len(raw_text),
                )
            ]

        offset = 0
        for line in lines:
            stripped = line.strip()
            match = header_pattern.match(stripped)
            if match:
                if current_title is not None:
                    sec_content = "\n".join(current_content_lines).strip()
                    sections.append(
                        DocumentSection(
                            title=current_title,
                            content=sec_content,
                            level=current_level,
                            start_char_offset=current_start,
                            end_char_offset=max(0, offset - 1),
                        )
                    )
                current_title = match.group(2).strip()
                current_level = len(match.group(1))
                current_content_lines = []
                current_start = offset
            else:
                if current_title is not None:
                    current_content_lines.append(line)
            offset += len(line) + 1

        if current_title is not None:
            sec_content = "\n".join(current_content_lines).strip()
            sections.append(
                DocumentSection(
                    title=current_title,
                    content=sec_content,
                    level=current_level,
                    start_char_offset=current_start,
                    end_char_offset=len(raw_text),
                )
            )

        return sections

    def normalize(
        self,
        title: str,
        content: str | None = None,
        organization_id: uuid.UUID | None = None,
        source_id: uuid.UUID | None = None,
        document_type: str | DocumentType = DocumentType.DOCUMENT,
        external_id: str | None = None,
        author: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        metadata: dict[str, Any] | None = None,
        id: uuid.UUID | None = None,
        raw_text: str | None = None,
        document_id: uuid.UUID | None = None,
        document_version_id: uuid.UUID | None = None,
        extra_metadata: dict[str, Any] | None = None,
    ) -> NormalizedDocument:
        actual_content = content if content is not None else (raw_text or "")
        actual_id = id or document_id or uuid.uuid4()
        actual_org_id = organization_id or uuid.uuid4()
        actual_source_id = source_id or uuid.uuid4()

        merged_metadata = {}
        if metadata:
            merged_metadata.update(metadata)
        if extra_metadata:
            merged_metadata.update(extra_metadata)

        sanitized_metadata = build_metadata(extra_metadata=merged_metadata)

        cleaned_title = title.replace("\x00", "").strip() if title else ""
        cleaned_content = self.clean_text(actual_content)

        sections = self.parse_sections(cleaned_content)
        total_chars = len(cleaned_content)
        total_words = len(cleaned_content.split()) if cleaned_content else 0

        doc_type_str = (
            document_type.value
            if isinstance(document_type, DocumentType)
            else str(document_type).lower().strip()
        ).replace("\x00", "")

        cleaned_external_id = external_id.replace("\x00", "").strip() if external_id else None
        cleaned_author = author.replace("\x00", "").strip() if author else None

        doc = NormalizedDocument(
            id=actual_id,
            organization_id=actual_org_id,
            source_id=actual_source_id,
            external_id=cleaned_external_id,
            document_type=doc_type_str,
            title=cleaned_title,
            content=cleaned_content,
            author=cleaned_author,
            created_at=created_at,
            updated_at=updated_at,
            metadata=sanitized_metadata,
            sections=sections,
            total_characters=total_chars,
            total_words=total_words,
        )

        validate_normalized_document(doc)
        return doc

