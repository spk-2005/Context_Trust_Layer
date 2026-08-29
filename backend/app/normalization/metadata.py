import uuid
from typing import Any
from pydantic import BaseModel, Field


class DocumentSection(BaseModel):
    section_index: int
    title: str | None = None
    level: int = 1
    content: str
    start_char_offset: int = 0
    end_char_offset: int = 0
    page_number: int | None = None


class NormalizedDocument(BaseModel):
    document_id: uuid.UUID
    document_version_id: uuid.UUID
    title: str
    clean_text: str
    sections: list[DocumentSection] = []
    total_characters: int = 0
    total_words: int = 0
    metadata: dict[str, Any] = Field(default_factory=dict)
