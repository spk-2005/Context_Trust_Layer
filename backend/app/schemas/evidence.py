"""
Immutable Evidence Span Schema.

Enforces the foundational invariant:
Evidence is immutable. Claim text derives strictly from verbatim quotes,
never from metadata template interpolation.
"""

import hashlib
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ImmutableEvidenceSpan(BaseModel):
    """
    Immutable, cryptographically verifiable evidence anchor.
    Frozen to prevent post-extraction mutation.
    """
    model_config = ConfigDict(frozen=True, extra="forbid")

    verbatim_quote: str = Field(..., min_length=1, description="Exact verbatim text quoted directly from the source document")
    clause_text: str = Field(..., min_length=1, description="The full enclosing clause or contextual section")
    page: Optional[int] = Field(None, ge=1, description="1-indexed document page number")
    char_start: Optional[int] = Field(None, ge=0, description="0-indexed start character offset in document content")
    char_end: Optional[int] = Field(None, ge=0, description="0-indexed end character offset in document content")
    source_hash: str = Field(..., min_length=8, description="Cryptographic hash (e.g. SHA-256) of document content or clause text")
    document_uri: Optional[str] = Field(None, description="URI or persistent identifier of the source document")
    section_locator: Optional[str] = Field(None, description="Section heading, numbering, or breadcrumb")

    @field_validator("verbatim_quote", "clause_text")
    @classmethod
    def validate_non_blank(cls, v: str) -> str:
        s = v.strip()
        if not s:
            raise ValueError("Evidence text must not be empty or whitespace only")
        return s

    @classmethod
    def from_content(
        cls,
        verbatim_quote: str,
        clause_text: str,
        content: str,
        page: Optional[int] = None,
        document_uri: Optional[str] = None,
        section_locator: Optional[str] = None,
    ) -> "ImmutableEvidenceSpan":
        """Factory that automatically calculates offsets and source hash from full content."""
        q = verbatim_quote.strip()
        c = clause_text.strip()
        start = content.find(q) if content else -1
        end = start + len(q) if start >= 0 else None
        start_val = start if start >= 0 else None

        source_hash = hashlib.sha256(content.encode("utf-8")).hexdigest() if content else hashlib.sha256(c.encode("utf-8")).hexdigest()

        return cls(
            verbatim_quote=q,
            clause_text=c,
            page=page,
            char_start=start_val,
            char_end=end,
            source_hash=source_hash,
            document_uri=document_uri,
            section_locator=section_locator,
        )
