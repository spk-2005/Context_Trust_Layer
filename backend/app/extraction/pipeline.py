"""
Layer 5: Candidate Extraction & Source-Aware Verification Pipeline.
Orchestrates Layer 4 Evidence -> Candidate Discovery -> Strategy Routing -> Plugin Verification -> Completeness Ledger.
"""

from __future__ import annotations

import logging
from typing import Any, List

from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.completeness_ledger import CompletenessLedger
from app.extraction.models import CandidateClaim, Layer5ExtractionResult
from app.extraction.plugins import VerificationPluginManager
from app.extraction.strategy_router import StrategyRouter
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult

logger = logging.getLogger(__name__)


class Layer5ExtractionPipeline:
    """End-to-end orchestrator for Layer 5."""

    def __init__(
        self,
        strategy_router: StrategyRouter | None = None,
        plugin_manager: VerificationPluginManager | None = None,
    ):
        self.router = strategy_router or StrategyRouter()
        self.plugin_manager = plugin_manager or VerificationPluginManager()

    async def process_envelope(
        self,
        envelope: CanonicalSourceEnvelope,
        evidence_result: ParsedEvidenceResult,
    ) -> Layer5ExtractionResult:
        """Processes an evidence result through Layer 5 extraction and verification."""
        ledger = CompletenessLedger(envelope.envelope_id, envelope.asset_id)
        all_candidates: List[CandidateClaim] = []

        total_units = len(evidence_result.units)
        candidates_found = 0
        claims_extracted_count = 0
        claims_verified_count = 0
        claims_rejected_count = 0

        for unit in evidence_result.units:
            is_eligible, strategy, reason = CandidateDiscoveryEngine.is_candidate(unit)

            if not is_eligible:
                ledger.record_entry(
                    unit_id=unit.unit_id,
                    block_type=unit.block_type,
                    candidate_status="skipped",
                    extractor_used="none",
                    failure_reason=reason,
                )
                continue

            candidates_found += 1

            # 2. Extract Claims using selected strategy
            try:
                extracted_claims = await self.router.extract(unit, strategy)
            except Exception as e:
                logger.error("Extraction failed for unit %s: %s", unit.unit_id, str(e))
                ledger.record_entry(
                    unit_id=unit.unit_id,
                    block_type=unit.block_type,
                    candidate_status="failed",
                    extractor_used=strategy.value,
                    failure_reason=str(e),
                )
                continue

            claims_extracted_count += len(extracted_claims)
            unit_verified_all = True
            unit_failure_reason = None

            # 3. Source-Aware Plugin Verification
            for claim in extracted_claims:
                is_valid, plugin_name, v_reason, details = self.plugin_manager.verify_candidate(
                    candidate=claim,
                    unit=unit,
                    raw_payload=envelope.raw_payload,
                )

                claim.verification_plugin = plugin_name
                claim.verification_details = details

                if is_valid:
                    claim.status = "verified"
                    claims_verified_count += 1
                else:
                    claim.status = "rejected"
                    claim.confidence = round(claim.confidence * 0.5, 2)
                    claims_rejected_count += 1
                    unit_verified_all = False
                    unit_failure_reason = v_reason

                all_candidates.append(claim)

            # Record in Completeness Ledger
            ledger.record_entry(
                unit_id=unit.unit_id,
                block_type=unit.block_type,
                candidate_status="verified" if unit_verified_all and extracted_claims else ("extracted" if extracted_claims else "no_claims"),
                extractor_used=strategy.value,
                verification_plugin=extracted_claims[0].verification_plugin if extracted_claims else None,
                verification_passed=unit_verified_all and bool(extracted_claims),
                claims_count=len(extracted_claims),
                failure_reason=unit_failure_reason,
            )

        summary = ledger.get_summary()

        return Layer5ExtractionResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            total_evidence_units_received=total_units,
            candidates_discovered=candidates_found,
            claims_extracted=claims_extracted_count,
            claims_verified=claims_verified_count,
            claims_rejected=claims_rejected_count,
            completeness_score=summary["completeness_score"],
            candidates=all_candidates,
            ledger_summary=summary,
        )


# Global singleton instance
global_extraction_pipeline = Layer5ExtractionPipeline()
