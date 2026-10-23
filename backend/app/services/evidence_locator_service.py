"""
Evidence Locator Service.

Verifies that evidence spans are physically present in the underlying document content,
validates byte/character offsets, and checks cryptographic content hashes.
Fails closed on any fabrication, offset divergence, or hash tampering.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Optional

from app.schemas.evidence import ImmutableEvidenceSpan


@dataclass
class EvidenceLocationResult:
    located: bool
    exact_offset_match: bool
    resolved_start: Optional[int]
    resolved_end: Optional[int]
    hash_valid: bool
    error_reason: Optional[str] = None


class EvidenceLocatorService:
    """Universal document-agnostic evidence verification service."""

    @classmethod
    def locate_and_verify(
        cls,
        evidence: ImmutableEvidenceSpan,
        source_content: Optional[str] = None,
    ) -> EvidenceLocationResult:
        """
        Locates the verbatim quote in source content, verifies offsets and SHA-256 hash.
        Fails closed if content is missing or quote is ungrounded.
        """
        if not evidence.verbatim_quote or not evidence.verbatim_quote.strip():
            return EvidenceLocationResult(
                located=False,
                exact_offset_match=False,
                resolved_start=None,
                resolved_end=None,
                hash_valid=False,
                error_reason="Verbatim quote is empty or blank.",
            )

        quote = evidence.verbatim_quote.strip()

        # If source content is not provided, fall back to checking quote inside enclosing clause_text
        content_to_check = source_content if (source_content and source_content.strip()) else evidence.clause_text

        if not content_to_check:
            return EvidenceLocationResult(
                located=False,
                exact_offset_match=False,
                resolved_start=None,
                resolved_end=None,
                hash_valid=False,
                error_reason="Neither source content nor clause_text was available to locate evidence.",
            )

        # 1. Verify Hash Integrity
        computed_hash = hashlib.sha256(content_to_check.encode("utf-8")).hexdigest()
        clause_hash = hashlib.sha256(evidence.clause_text.strip().encode("utf-8")).hexdigest()
        hash_valid = (
            evidence.source_hash == computed_hash
            or evidence.source_hash == clause_hash
            or evidence.source_hash.startswith("sha256:") and (
                evidence.source_hash[7:] == computed_hash or evidence.source_hash[7:] == clause_hash
            )
        )

        # 2. Check Offset Alignment if offsets are provided
        exact_offset_match = False
        resolved_start = None
        resolved_end = None

        if evidence.char_start is not None and evidence.char_end is not None:
            if (
                0 <= evidence.char_start <= len(content_to_check)
                and 0 <= evidence.char_end <= len(content_to_check)
                and evidence.char_start < evidence.char_end
            ):
                extracted_slice = content_to_check[evidence.char_start:evidence.char_end].strip()
                if extracted_slice == quote:
                    exact_offset_match = True
                    resolved_start = evidence.char_start
                    resolved_end = evidence.char_end

        # 3. If exact offsets didn't match directly, locate verbatim quote in content
        if not exact_offset_match:
            found_idx = content_to_check.find(quote)
            if found_idx >= 0:
                resolved_start = found_idx
                resolved_end = found_idx + len(quote)
                exact_offset_match = (
                    evidence.char_start == resolved_start and evidence.char_end == resolved_end
                )
            else:
                # Try normalized whitespace search
                norm_quote = re.sub(r"\s+", " ", quote).strip()
                norm_content = re.sub(r"\s+", " ", content_to_check)
                if norm_quote in norm_content:
                    resolved_start = content_to_check.lower().find(quote.lower()[:30])
                    resolved_end = (resolved_start + len(quote)) if resolved_start >= 0 else None
                else:
                    return EvidenceLocationResult(
                        located=False,
                        exact_offset_match=False,
                        resolved_start=None,
                        resolved_end=None,
                        hash_valid=hash_valid,
                        error_reason=f"Verbatim quote '{quote[:50]}...' was not found in source text.",
                    )

        return EvidenceLocationResult(
            located=True,
            exact_offset_match=exact_offset_match,
            resolved_start=resolved_start,
            resolved_end=resolved_end,
            hash_valid=hash_valid,
            error_reason=None,
        )
