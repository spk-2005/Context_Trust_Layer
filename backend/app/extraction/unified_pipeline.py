"""
Unified Core Extraction Pipeline.

Defines the single authoritative extraction pipeline shared by both:
1. Live Application (FastAPI endpoint /v1/documents/upload-and-extract)
2. Audit & Validation Benchmark (research/validation_50/run_validation.py)

Pipeline steps:
PDF/File raw bytes → structured parsing → candidate discovery → claim extraction
→ validation → deduplication → conflict detection → results
"""

from __future__ import annotations

import logging
import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.db.enums import SourceFamily, SourceIntent
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.models import CandidateClaim, Layer5ExtractionResult
from app.extraction.pipeline import global_extraction_pipeline
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.universal_file_parser import UniversalFileParser
from app.validation_gate.decision_engine import ClaimLifecycleDecisionEngine
from app.validation_gate.models import (
    CandidateGateEvaluation,
    ClaimLifecycleDecision,
    Layer6ValidationResult,
)
from app.validation_gate.persistence import EnterpriseClaimStore

logger = logging.getLogger(__name__)


class UnifiedPipelineOptions(BaseModel):
    """Runtime options for unified extraction execution."""
    organization_id: uuid.UUID = Field(default_factory=lambda: uuid.UUID("11111111-1111-1111-1111-111111111111"))
    source_id: uuid.UUID = Field(default_factory=lambda: uuid.UUID("44444444-4444-4444-4444-444444444444"))
    document_type: str = "policy"
    source_intent: SourceIntent = SourceIntent.GOVERNANCE_POLICY
    source_family: SourceFamily = SourceFamily.DOCUMENT
    doc_title: Optional[str] = None
    external_id: Optional[str] = None
    persist_to_db: bool = False
    document_version_id: Optional[uuid.UUID] = None


@dataclass
class UnifiedPipelineResult:
    """Strongly-typed outcome of the unified extraction pipeline."""
    envelope: CanonicalSourceEnvelope
    evidence_result: ParsedEvidenceResult
    raw_candidates: List[CandidateClaim]
    candidates: List[CandidateClaim]  # Deduplicated canonical claims
    evaluations: List[CandidateGateEvaluation]
    conflicts: List[Dict[str, Any]]
    metrics: Dict[str, Any]
    persisted_claim_ids: List[uuid.UUID] = field(default_factory=list)

    def to_summary_dict(self) -> Dict[str, Any]:
        return {
            "envelope_id": str(self.envelope.envelope_id),
            "asset_id": self.envelope.asset_id,
            "filename": self.envelope.evidence_locator.get("filename") if self.envelope.evidence_locator else "",
            "total_evidence_units": len(self.evidence_result.units),
            "candidates_discovered": len(self.raw_candidates),
            "unique_claims_extracted": len(self.candidates),
            "claims_approved": sum(1 for e in self.evaluations if e.lifecycle_decision == ClaimLifecycleDecision.APPROVE),
            "claims_review": sum(1 for e in self.evaluations if e.lifecycle_decision == ClaimLifecycleDecision.REVIEW),
            "claims_rejected": sum(1 for e in self.evaluations if e.lifecycle_decision == ClaimLifecycleDecision.REJECT),
            "conflicts_detected": len(self.conflicts),
            "persisted_claims_count": len(self.persisted_claim_ids),
        }


class UnifiedExtractionPipeline:
    """
    Shared, authoritative extraction entry point used by BOTH:
    1. Live Application (FastAPI endpoint /v1/documents/upload-and-extract)
    2. Research & Audit Benchmark (run_validation.py)
    
    Guarantees parity by executing the exact same parsing, discovery, extraction,
    validation, deduplication, and conflict rules across all workflows.
    """

    @classmethod
    async def execute(
        cls,
        filename: str,
        raw_bytes: bytes,
        options: Optional[UnifiedPipelineOptions] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> UnifiedPipelineResult:
        start_time = time.time()
        opts = options or UnifiedPipelineOptions()

        doc_title = (
            opts.doc_title
            or filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        ).replace("\x00", "").strip()

        # Step 1: Universal Parsing
        content_text = UniversalFileParser.parse_file(
            filename=filename,
            raw_bytes=raw_bytes,
            doc_title=doc_title,
        )

        # Step 2: Canonical Source Envelope (Layer 3)
        canonical_env = EnvelopeFactory.create_from_file_upload(
            filename=filename,
            raw_bytes=raw_bytes,
            parsed_content=content_text,
            organization_id=opts.organization_id,
            source_id=opts.source_id,
            document_type=opts.document_type,
            source_intent=opts.source_intent,
        )

        # Step 3: Structured Parsing (Layer 4)
        fmt_lower = (filename.rsplit(".", 1)[-1] if "." in filename else "txt").lower()
        if fmt_lower in ("csv", "json", "xlsx", "sql"):
            evidence_result = await StructuredDataParser.parse(canonical_env)
        else:
            evidence_result = await DocumentParser.parse(canonical_env)

        # Step 4: Candidate Discovery & Extraction (Layer 5)
        l5_result: Layer5ExtractionResult = await global_extraction_pipeline.process_envelope(
            envelope=canonical_env,
            evidence_result=evidence_result,
        )
        raw_candidates = l5_result.candidates

        # Step 4.5: Universal Claim Quality Normalization
        from app.extraction.claim_quality_normalizer import ClaimQualityNormalizer

        normalized_candidates: List[CandidateClaim] = []
        for c in raw_candidates:
            norm_c = ClaimQualityNormalizer.normalize_candidate_claim(c)
            normalized_candidates.append(norm_c if norm_c is not None else c)

        # Step 5: Deduplication (preserve highest confidence & merge conditions)
        seen_keys: Dict[Tuple[str, str, str, str], CandidateClaim] = {}
        for c in normalized_candidates:
            key = (
                (c.subject or "").strip().lower(),
                (c.predicate or "").strip().lower(),
                str(c.object or "").strip().lower(),
                str(c.modality or "").strip().upper(),
            )
            if key not in seen_keys:
                seen_keys[key] = c
            else:
                existing = seen_keys[key]
                # Merge conditions if any
                if c.conditions and not existing.conditions:
                    existing.conditions = c.conditions

        deduped_candidates = list(seen_keys.values())

        # Step 6: Multi-Dimensional Validation Gate (Layer 6)
        evaluations: List[CandidateGateEvaluation] = []
        candidates_map: Dict[str, CandidateClaim] = {}
        for cand in deduped_candidates:
            candidates_map[cand.candidate_id] = cand
            eval_res = ClaimLifecycleDecisionEngine.evaluate_candidate(
                candidate=cand,
                envelope=canonical_env,
            )
            evaluations.append(eval_res)

        # Step 7: Deterministic In-Memory Conflict Detection
        conflicts: List[Dict[str, Any]] = []
        for i in range(len(deduped_candidates)):
            for j in range(i + 1, len(deduped_candidates)):
                claim_a = deduped_candidates[i]
                claim_b = deduped_candidates[j]
                try:
                    outcome = CompatibilityGate.evaluate_decision_compatibility(claim_a, claim_b)
                    if outcome.is_comparable:
                        conflicts.append({
                            "claim_a_id": claim_a.candidate_id,
                            "claim_b_id": claim_b.candidate_id,
                            "claim_a_subject": claim_a.subject,
                            "claim_b_subject": claim_b.subject,
                            "reason": outcome.reason,
                            "relationship": outcome.relationship,
                        })
                except Exception as exc:
                    logger.debug("Conflict check skipped between %s and %s: %s", claim_a.candidate_id, claim_b.candidate_id, exc)

        # Step 8: Optional DB Persistence
        persisted_ids: List[uuid.UUID] = []
        if opts.persist_to_db and db_session and opts.document_version_id:
            persisted_ids = await EnterpriseClaimStore.persist_evaluations(
                evaluations=evaluations,
                candidates_map=candidates_map,
                envelope=canonical_env,
                session=db_session,
                document_version_id=opts.document_version_id,
            )

        duration = time.time() - start_time
        metrics = {
            "duration_seconds": round(duration, 4),
            "total_units": len(evidence_result.units),
            "candidates_discovered": len(raw_candidates),
            "unique_claims": len(deduped_candidates),
            "approved": sum(1 for e in evaluations if e.lifecycle_decision == ClaimLifecycleDecision.APPROVE),
            "review": sum(1 for e in evaluations if e.lifecycle_decision == ClaimLifecycleDecision.REVIEW),
            "rejected": sum(1 for e in evaluations if e.lifecycle_decision == ClaimLifecycleDecision.REJECT),
        }

        return UnifiedPipelineResult(
            envelope=canonical_env,
            evidence_result=evidence_result,
            raw_candidates=raw_candidates,
            candidates=deduped_candidates,
            evaluations=evaluations,
            conflicts=conflicts,
            metrics=metrics,
            persisted_claim_ids=persisted_ids,
        )
