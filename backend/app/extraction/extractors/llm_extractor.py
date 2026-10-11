"""
Layer 5: LLM Semantic Extractor.
Extracts nuanced claims from complex unstructured narrative prose and multi-layered policies using LLMs.
Includes automatic fallback to DomainRuleExtractor for resilience.
"""

from __future__ import annotations

import logging
from typing import List

from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider

logger = logging.getLogger(__name__)


class LLMSemanticExtractor:
    """Semantic LLM extractor with graceful fallback to domain rules."""

    def __init__(self, provider: BaseLLMProvider | None = None):
        try:
            self.provider = provider or get_llm_provider()
        except Exception:
            self.provider = None

    async def extract_from_unit(self, unit: ParsedEvidenceUnit) -> List[CandidateClaim]:
        claims: List[CandidateClaim] = []
        text = (unit.content_text or "").strip()
        hier = unit.hierarchical_context or []
        doc_title = hier[0] if hier else "Policy"
        section_title = " > ".join(hier[1:]) if len(hier) > 1 else "Clause"

        if not text:
            return claims

        # Try LLM extraction if provider available
        if self.provider is not None:
            try:
                extraction_result = await self.provider.extract_claims(
                    document_title=doc_title,
                    section_title=section_title,
                    section_content=text,
                )
                if extraction_result and extraction_result.claims:
                    for idx, c in enumerate(extraction_result.claims):
                        evidence_span = c.evidence.exact_quote if c.evidence else text
                        cand = CandidateClaim.create(
                            envelope_id=unit.envelope_id,
                            unit_id=unit.unit_id,
                            asset_id=unit.asset_id,
                            claim_text=c.claim_text,
                            subject=c.subject or doc_title,
                            predicate=c.predicate or "specifies",
                            object_=c.object or c.claim_text,
                            evidence_text_span=evidence_span,
                            modal_operator="requires",
                            claim_type=c.claim_type or "policy",
                            extraction_strategy=ExtractionStrategyType.LLM_SEMANTIC,
                            locator=unit.locator,
                            structured_values={"llm_extracted": True, "model": extraction_result.extraction_model},
                            confidence=0.94,
                        )
                        claims.append(cand)
                    return claims
            except Exception as e:
                logger.warning("LLM extraction failed, engaging DomainRuleExtractor fallback: %s", str(e))

        # Fallback to deterministic domain rule extraction
        fallback_claims = DomainRuleExtractor.extract_from_unit(unit)
        for fc in fallback_claims:
            fc.extraction_strategy = ExtractionStrategyType.LLM_SEMANTIC
        return fallback_claims
