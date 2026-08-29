import re
import unicodedata
import uuid

from app.normalization.metadata import DocumentSection, NormalizedDocument


class DocumentNormalizer:
    """Normalizes raw document text into clean, structured sections ready for claim extraction."""

    @staticmethod
    def clean_text(raw_text: str) -> str:
        if not raw_text:
            return ""

        # 1. Unicode normalization (NFKC)
        text = unicodedata.normalize("NFKC", raw_text)

        # 2. Normalize carriage returns / line feeds
        text = text.replace("\r\n", "\n").replace("\r", "\n")

        # 3. Clean up excessive spaces and trailing whitespaces per line
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.split("\n")]

        # 4. Collapse multiple blank lines into max 2 newlines
        cleaned = "\n".join(lines)
        cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
        return cleaned.strip()

    def parse_sections(self, text: str) -> list[DocumentSection]:
        sections: list[DocumentSection] = []
        if not text:
            return sections

        # Split on headers (e.g. # Header or Section: or ALL CAPS HEADERS)
        header_pattern = re.compile(r"^(#{1,6}\s+.*|[A-Z0-9\s]{4,}:?)$", re.MULTILINE)

        matches = list(header_pattern.finditer(text))
        if not matches:
            # Single section
            sections.append(
                DocumentSection(
                    section_index=1,
                    title="General",
                    level=1,
                    content=text,
                    start_char_offset=0,
                    end_char_offset=len(text),
                )
            )
            return sections

        for i, match in enumerate(matches):
            header_title = match.group(0).strip("# ").rstrip(":")
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[match.end():end].strip()

            sections.append(
                DocumentSection(
                    section_index=i + 1,
                    title=header_title,
                    level=match.group(0).count("#") or 1,
                    content=content,
                    start_char_offset=start,
                    end_char_offset=end,
                )
            )

        return sections

    def normalize(
        self,
        document_id: uuid.UUID,
        document_version_id: uuid.UUID,
        title: str,
        raw_text: str,
        extra_metadata: dict | None = None,
    ) -> NormalizedDocument:
        cleaned = self.clean_text(raw_text)
        sections = self.parse_sections(cleaned)
        words = len(cleaned.split())

        return NormalizedDocument(
            document_id=document_id,
            document_version_id=document_version_id,
            title=title,
            clean_text=cleaned,
            sections=sections,
            total_characters=len(cleaned),
            total_words=words,
            metadata=extra_metadata or {},
        )
