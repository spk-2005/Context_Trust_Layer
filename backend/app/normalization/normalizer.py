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
    def strip_statistical_headers_footers(raw_text: str) -> str:
        """
        Stage 2 Generic De-noising: Statistical positional header and footer discovery.
        
        Replaces digits with '#' and calculates recurrence across page boundaries.
        Any pattern appearing in the top 3 or bottom 3 lines on >= 35% of pages is 
        identified as a recurring running banner/footer and stripped without hardcoded client regex.
        """
        if not raw_text:
            return ""

        # Identify page boundaries (e.g. '## Page X' or form-feed '\f')
        page_splits = re.split(r"(?:^|\n)(?=## Page \d+|\f)", raw_text)
        if len(page_splits) < 2:
            return raw_text

        page_headers: dict[str, set[int]] = {}
        page_footers: dict[str, set[int]] = {}

        def _norm_banner_line(line: str) -> str:
            # Replace all number sequences with '#' to match e.g. "Internal, Wingify 1" and "Internal, Wingify 2"
            cleaned = re.sub(r"\d+", "#", line.strip().lower())
            # Collapse multiple spaces and strip punctuation
            return re.sub(r"\s+", " ", cleaned).strip()

        for idx, page in enumerate(page_splits):
            lines = [l.strip() for l in page.split("\n") if l.strip() and not l.strip().startswith("## Page")]
            if len(lines) < 4:
                continue

            limit = min(2, max(1, len(lines) // 3))

            # Top candidate lines (Header Candidates, capped at 80 chars)
            for top_line in lines[:limit]:
                if len(top_line) > 80:
                    continue
                norm_top = _norm_banner_line(top_line)
                if len(norm_top) >= 4:
                    page_headers.setdefault(norm_top, set()).add(idx)

            # Bottom candidate lines (Footer Candidates, capped at 80 chars)
            for bot_line in lines[-limit:]:
                if len(bot_line) > 80:
                    continue
                norm_bot = _norm_banner_line(bot_line)
                if len(norm_bot) >= 4:
                    page_footers.setdefault(norm_bot, set()).add(idx)

        total_pages = len(page_splits)
        threshold = max(2, int(total_pages * 0.35))

        banner_patterns: set[str] = set()
        for norm_text, page_set in {**page_headers, **page_footers}.items():
            if len(page_set) >= threshold:
                banner_patterns.add(norm_text)

        if not banner_patterns:
            return raw_text

        # Strip identified running banner patterns from all pages
        cleaned_pages = []
        for page in page_splits:
            page_lines = page.split("\n")
            filtered_lines = []
            for line in page_lines:
                norm_current = _norm_banner_line(line)
                if norm_current in banner_patterns:
                    continue
                filtered_lines.append(line)
            cleaned_pages.append("\n".join(filtered_lines))

        return "\n".join(cleaned_pages)

    @staticmethod
    def is_table_of_contents_block(text: str, title: str = "") -> bool:
        """
        Stage 2 TOC Detection: Identify Table of Contents blocks or pages.
        
        Flags blocks if title indicates TOC, dot leaders exist, or > 40% of lines 
        end in trailing section/page numbers without complete predicates.
        """
        combined = f"{title}\n{text}".lower()
        if re.search(r"\b(table of contents|contents|outline)\b", combined[:200]):
            return True

        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if len(lines) < 3:
            return False

        toc_indicators = 0
        for line in lines:
            # Dot leaders: e.g. "Policy Summary ............. 3"
            if re.search(r"\.{2,}\s*\d+", line):
                toc_indicators += 1
            # Trailing page numbers or section indices: e.g. "3.2. Points to Remember 5" or "Purpose 4 2."
            elif re.search(r"^[0-9.]*\s*[A-Za-z\s&,/-]+\s+\d+(?:\s+[0-9.]+)?$", line):
                toc_indicators += 1

        return (toc_indicators / len(lines)) >= 0.40

    @staticmethod
    def linearize_table_content(text: str) -> str:
        """
        Stage 3 Table Linearization: Transforms tabular data into canonical declarative sentences.
        
        Ensures dense policy tables (e.g. Level & Grade vs Duration) survive downstream
        linguistic grammar gates with full source grounding.
        """
        lines = text.split("\n")
        table_lines = [l.strip() for l in lines if "|" in l or "\t" in l]
        if len(table_lines) < 2:
            return text

        # Parse markdown pipe table
        pipe_rows = [[c.strip() for c in l.split("|") if c.strip()] for l in lines if "|" in l]
        if len(pipe_rows) >= 2:
            headers = pipe_rows[0]
            # Ignore separator line |---|---|
            data_rows = [r for r in pipe_rows[1:] if not all(re.match(r"^[-:]+$", c) for c in r)]
            linearized = []
            for row in data_rows:
                parts = []
                for h, val in zip(headers, row):
                    if h and val:
                        parts.append(f"{h}: {val}")
                if parts:
                    linearized.append("Policy rule: " + ", ".join(parts) + ".")
            if linearized:
                return "\n".join(linearized)

        return text

    @staticmethod
    def structure_aware_segmentation(text: str) -> list[str]:
        """
        Stage 3 Sentence Segmentation: Protects decimal clause numbering, software versions,
        and abbreviations before sentence tokenization.
        """
        if not text:
            return []

        # Mask decimal numbers, clause hierarchies, versions, and abbreviations to prevent false splits
        # e.g. "99.9%", "3.3.", "v1.5", "e.g.", "i.e."
        def _mask_dots(m):
            return m.group(0).replace(".", "_DOT_")

        protected = text
        protected = re.sub(r"\b\d+\.\d+(?:\.\d+)?\.?", _mask_dots, protected)
        protected = re.sub(r"\bv\d+\.\d+(?:\.\d+)?", _mask_dots, protected)
        protected = re.sub(r"\b[A-Za-z]{1,4}\.\s*(?=[a-z])", _mask_dots, protected)

        # Split on sentence boundaries and bullet points
        raw_splits = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9●❖•-])|\n\s*[-*•●❖]\s*", protected)
        sentences = []
        for s in raw_splits:
            unmasked = s.replace("_DOT_", ".").strip().lstrip("-*•●❖ ")
            if unmasked:
                sentences.append(unmasked)

        return sentences

    @staticmethod
    def scrub_noise(text: str) -> str:
        """Scrub document boilerplate, greetings, table of contents, and structural artifacts before extraction."""
        if not text:
            return ""

        # Apply Stage 2 statistical header/footer stripping
        text = DocumentNormalizer.strip_statistical_headers_footers(text)

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
            # Trailing dot leaders e.g. "Notice Period .......... 4"
            re.compile(r"\.{2,}\s*\d+\s*$"),
            # Trailing page numbers on section headers e.g. "Points to Remember 5 3.3." or "Purpose 4 2."
            re.compile(r"^[0-9.]*\s*[A-Za-z\s&,/-]{3,}\s+\d+(?:\s+[0-9.]+)?$"),
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
                    if DocumentNormalizer.is_table_of_contents_block(p):
                        continue
                    p_linear = DocumentNormalizer.linearize_table_content(p)
                    if current_len + len(p_linear) > 2000 and current_chunk:
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
                    current_chunk.append(p_linear)
                    current_len += len(p_linear)
                if current_chunk:
                    chunk_text = "\n\n".join(current_chunk)
                    if not DocumentNormalizer.is_table_of_contents_block(chunk_text):
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

            # Check if general fallback is TOC
            if DocumentNormalizer.is_table_of_contents_block(raw_text):
                return []

            linearized_general = DocumentNormalizer.linearize_table_content(raw_text)
            return [
                DocumentSection(
                    title="General",
                    content=linearized_general,
                    level=1,
                    start_char_offset=0,
                    end_char_offset=len(linearized_general),
                )
            ]

        offset = 0
        for line in lines:
            stripped = line.strip()
            match = header_pattern.match(stripped)
            if match:
                if current_title is not None:
                    sec_content = "\n".join(current_content_lines).strip()
                    if not DocumentNormalizer.is_table_of_contents_block(sec_content, title=current_title):
                        sec_content = DocumentNormalizer.linearize_table_content(sec_content)
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
            if not DocumentNormalizer.is_table_of_contents_block(sec_content, title=current_title):
                sec_content = DocumentNormalizer.linearize_table_content(sec_content)
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

