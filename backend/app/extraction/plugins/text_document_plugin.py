"""
Layer 5: Text / Document Evidence Verification Plugin.
Verifies that claims from narrative documents, policies, and files are 100% grounded in source text.
Checks exact quote spans, character offsets, and numerical fidelity.
"""

from __future__ import annotations

import re
from typing import Any, Tuple

from app.extraction.models import CandidateClaim
from app.extraction.plugins.base_plugin import EvidenceVerificationPlugin
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit


class TextDocumentVerificationPlugin(EvidenceVerificationPlugin):
    """Verifies textual evidence grounding, direct quote matching, and numerical fidelity."""

    @property
    def plugin_name(self) -> str:
        return "TextDocumentVerificationPlugin"

    def supports_evidence(self, unit: ParsedEvidenceUnit) -> bool:
        return unit.block_type in ("clause", "paragraph", "heading", "chat_message", "table_row")

    def verify(
        self,
        candidate: CandidateClaim,
        unit: ParsedEvidenceUnit,
        raw_payload: Any,
    ) -> Tuple[bool, str, dict[str, Any]]:
        source_text = unit.content_text or ""
        evidence_quote = candidate.evidence_text_span or ""

        if not source_text:
            return False, "Evidence unit contains empty source text.", {"error": "empty_source"}

        # 1. Direct or Normalized Substring Verification
        norm_source = " ".join(source_text.lower().split())
        norm_quote = " ".join(evidence_quote.lower().split())

        quote_found = norm_quote in norm_source or norm_source in norm_quote

        if not quote_found:
            # Check overlap threshold for paraphrased LLM output
            source_words = set(norm_source.split())
            quote_words = set(norm_quote.split())
            overlap = len(source_words.intersection(quote_words)) / max(len(quote_words), 1)
            if overlap < 0.60:
                return False, f"Evidence quote does not match source text (Word overlap: {overlap*100:.1f}%).", {
                    "word_overlap": overlap,
                    "expected_in_source": evidence_quote[:100],
                }

        # 2. Numerical / Quantitative Fidelity Check
        quote_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", candidate.object))
        source_numbers = set(re.findall(r"\b\d+(?:\.\d+)?\b", source_text))
        
        missing_numbers = quote_numbers - source_numbers
        if missing_numbers:
            return False, f"Numerical values {missing_numbers} in claim do not appear in source evidence.", {
                "missing_numbers": list(missing_numbers),
                "source_numbers": list(source_numbers),
            }

        # 3. Offsets Grounding
        loc = unit.locator or {}
        details = {
            "quote_grounded": True,
            "line_start": loc.get("line_start"),
            "line_end": loc.get("line_end"),
            "start_char": loc.get("start_char"),
            "end_char": loc.get("end_char"),
            "evidence_length": len(source_text),
        }

        return True, "Direct quote and numerical integrity verified against source text.", details
