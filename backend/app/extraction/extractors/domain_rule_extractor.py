"""
Layer 5: Domain Rules Extractor.
Extracts structured claims from normative policy clauses, compliance rules, and conversational decisions
using deterministic grammar patterns, modal logic parsing, and domain heuristics.
"""

from __future__ import annotations

import re
from typing import List, Optional

from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit


class DomainRuleExtractor:
    """Grammar and modal pattern extractor for policy clauses and standard requirements."""

    MODAL_SPLIT_REGEX = re.compile(
        r"^(?P<subject>.*?)\s+\b(?P<modal>must|shall|is required to|are required to|prohibited from|cannot|can not|should|will|is mandatory for|are mandatory for)\s+(?P<predicate_object>.*)$",
        re.IGNORECASE,
    )

    @classmethod
    def extract_from_unit(cls, unit: ParsedEvidenceUnit) -> List[CandidateClaim]:
        claims: List[CandidateClaim] = []
        text = (unit.content_text or "").strip()
        hier = unit.hierarchical_context or []
        context_prefix = " > ".join(hier) if hier else ""
        loc = unit.locator or {}

        # 1. Conversational decisions (e.g. "[Bob] Yes, co-signing the exemption rule SEC-902 under emergency mandate v2.0.")
        if unit.block_type == "chat_message":
            speaker = unit.structured_data.get("speaker") or "Authorized User"
            claim = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text=f"Decision by {speaker}: {text}",
                subject=f"Decision ({speaker})",
                predicate="authorizes",
                object_=text,
                evidence_text_span=text,
                modal_operator="authorized",
                claim_type="decision",
                extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                locator=loc,
                structured_values=unit.structured_data,
                confidence=0.92,
            )
            claims.append(claim)
            return claims

        # 2. Split into sentences if multi-sentence clause
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            sentences = [text]

        for s_idx, sentence in enumerate(sentences):
            match = cls.MODAL_SPLIT_REGEX.match(sentence)
            if match:
                raw_subject = match.group("subject").strip() or (hier[-1] if hier else "System")
                raw_modal = match.group("modal").strip().lower()
                raw_pred_obj = match.group("predicate_object").strip().rstrip(".")

                # Refine predicate and object
                pred_words = raw_pred_obj.split(" ", 2)
                if len(pred_words) >= 2:
                    predicate = f"{raw_modal}_{pred_words[0]}_{pred_words[1]}"
                    object_val = pred_words[2] if len(pred_words) > 2 else raw_pred_obj
                else:
                    predicate = f"{raw_modal}_satisfy"
                    object_val = raw_pred_obj

                qualified_subject = f"{context_prefix}: {raw_subject}" if context_prefix else raw_subject

                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=sentence,
                    subject=qualified_subject,
                    predicate=predicate,
                    object_=object_val,
                    evidence_text_span=sentence,
                    modal_operator=raw_modal,
                    claim_type="policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence, "hierarchical_context": hier},
                    confidence=0.95,
                )
                claims.append(c)
            elif len(sentence.split()) > 3:
                # Direct assertion fallback
                subject = hier[-1] if hier else "Governance Policy"
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=sentence,
                    subject=subject,
                    predicate="specifies",
                    object_=sentence,
                    evidence_text_span=sentence,
                    modal_operator="mandates",
                    claim_type="policy",
                    extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
                    locator={**loc, "sentence_index": s_idx},
                    structured_values={"raw_sentence": sentence},
                    confidence=0.88,
                )
                claims.append(c)

        return claims
