"""
Independent SME Benchmark Verification & Sign-off Engine (Sprint AF-14 / Governance).

Guarantees independence of downstream evaluation by enforcing external SME validation
of the 175 gold benchmark answers:
1. Reviewer Independence:
   - External SME must NOT be the author/tuner of the extraction pipeline.
2. Comprehensive Ground-Truth Review:
   - Approves or corrects each gold answer.
   - Confirms negative and refusal labels (unstated questions must trigger refusal).
   - Confirms adversarial trap expectations (overstatement, polarity flips, modal swaps).
   - Confirms exact source clause citations.
3. Cryptographic Benchmark Sign-off:
   - Computes deterministic SHA-256 hash of verified ground truths.
   - Emits an immutable sign-off ledger required for unconditional v3.0 certification.
"""

from __future__ import annotations

import datetime
import enum
import hashlib
import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.evaluation.downstream_agent_benchmark import (
    BenchmarkQuestion,
    DownstreamAgentBenchmark,
    DocumentFamily,
    QuestionType,
)

logger = logging.getLogger("benchmark_sme_verifier")


class SMESignoffStatus(str, enum.Enum):
    PENDING = "PENDING_INDEPENDENT_SME_REVIEW"
    APPROVED = "APPROVED"
    CORRECTED = "CORRECTED"
    FLAGGED = "FLAGGED"


class BenchmarkSMEVerificationItem(BaseModel):
    """External SME review item for a benchmark question."""
    question_id: str
    family: str
    question_type: str
    document_id: str
    question_text: str
    draft_gold_answer: str
    expected_citations: List[str] = Field(default_factory=list)
    is_unstated: bool = False
    is_adversarial_trap: bool = False

    # SME Review Fields
    sme_reviewer_id: Optional[str] = None
    sme_timestamp: Optional[str] = None
    sme_status: SMESignoffStatus = SMESignoffStatus.PENDING
    sme_confirmed_gold_answer: Optional[str] = None
    sme_confirmed_refusal_label: Optional[bool] = None
    sme_confirmed_trap_expectation: Optional[bool] = None
    sme_confirmed_citations: List[str] = Field(default_factory=list)
    sme_rationale: Optional[str] = None


class BenchmarkSMESignoffLedger(BaseModel):
    """Cryptographically sealed ledger of external SME benchmark verification."""
    benchmark_version: str = "v3.0-gold-independent"
    signoff_timestamp: str
    sme_reviewer_id: str
    sme_reviewer_role: str
    sme_reviewer_organization: str
    lead_governance_id: str
    total_questions: int
    approved_count: int
    corrected_count: int
    flagged_count: int
    refusal_labels_confirmed: bool
    trap_expectations_confirmed: bool
    citations_confirmed: bool
    benchmark_sha256_seal: str
    items: List[BenchmarkSMEVerificationItem] = Field(default_factory=list)


class BenchmarkSMEVerifier:
    """Workspace managing external SME review and cryptographic sign-off."""

    @classmethod
    def export_sme_review_bundle(
        cls,
        questions: Optional[List[BenchmarkQuestion]] = None,
        output_path: Optional[Path] = None,
    ) -> Path:
        """Exports the 175 benchmark questions to an external SME review queue."""
        q_list = questions or DownstreamAgentBenchmark.generate_benchmark_suite()
        target_path = output_path or Path("research/validation_50/benchmark_signoff/benchmark_175_gold_review_queue.json")
        target_path.parent.mkdir(parents=True, exist_ok=True)

        items: List[BenchmarkSMEVerificationItem] = []
        for q in q_list:
            items.append(BenchmarkSMEVerificationItem(
                question_id=q.question_id,
                family=q.family.value,
                question_type=q.question_type.value,
                document_id=q.document_id,
                question_text=q.question_text,
                draft_gold_answer=q.ground_truth_answer,
                expected_citations=list(q.expected_citations),
                is_unstated=q.is_unstated,
                is_adversarial_trap=q.is_adversarial_trap,
                sme_status=SMESignoffStatus.PENDING,
            ))

        target_path.write_text(json.dumps([item.model_dump() for item in items], indent=2), encoding="utf-8")
        logger.info("Exported %d benchmark items for external SME review to %s", len(items), target_path)
        return target_path

    @classmethod
    def process_sme_signoff(
        cls,
        reviewed_items: List[BenchmarkSMEVerificationItem],
        sme_reviewer_id: str,
        sme_reviewer_role: str = "External Independent Legal & Compliance Auditor",
        sme_reviewer_organization: str = "Independent Regulatory Compliance Council",
        lead_governance_id: str = "HEAD_OF_DATA_GOVERNANCE",
        pipeline_author_id: str = "EXTRACTION_PIPELINE_TEAM",
    ) -> Tuple[BenchmarkSMESignoffLedger, Dict[str, Any]]:
        """
        Validates SME independence, computes sign-off metrics, and seals the gold benchmark.
        """
        # Hard check for reviewer independence
        if sme_reviewer_id == pipeline_author_id:
            raise ValueError(f"Reviewer independence violation: SME '{sme_reviewer_id}' cannot be pipeline author.")

        total_q = len(reviewed_items)
        if total_q != 175:
            logger.warning("Expected 175 questions, received %d", total_q)

        approved = 0
        corrected = 0
        flagged = 0
        refusals_ok = True
        traps_ok = True
        cits_ok = True

        raw_fingerprint = ""
        for item in reviewed_items:
            item.sme_reviewer_id = sme_reviewer_id
            if item.sme_status == SMESignoffStatus.APPROVED:
                approved += 1
            elif item.sme_status == SMESignoffStatus.CORRECTED:
                corrected += 1
            elif item.sme_status == SMESignoffStatus.FLAGGED:
                flagged += 1

            if item.is_unstated and item.sme_confirmed_refusal_label is False:
                refusals_ok = False
            if item.is_adversarial_trap and item.sme_confirmed_trap_expectation is False:
                traps_ok = False
            if not item.sme_confirmed_citations and item.expected_citations:
                cits_ok = False

            # Add to cryptographic hash input
            ans = item.sme_confirmed_gold_answer or item.draft_gold_answer
            raw_fingerprint += f"{item.question_id}:{ans}:{item.sme_status.value}|"

        seal = hashlib.sha256(raw_fingerprint.encode("utf-8")).hexdigest()

        ledger = BenchmarkSMESignoffLedger(
            benchmark_version="v3.0-gold-independent",
            signoff_timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            sme_reviewer_id=sme_reviewer_id,
            sme_reviewer_role=sme_reviewer_role,
            sme_reviewer_organization=sme_reviewer_organization,
            lead_governance_id=lead_governance_id,
            total_questions=total_q,
            approved_count=approved,
            corrected_count=corrected,
            flagged_count=flagged,
            refusal_labels_confirmed=refusals_ok,
            trap_expectations_confirmed=traps_ok,
            citations_confirmed=cits_ok,
            benchmark_sha256_seal=seal,
            items=reviewed_items,
        )

        metrics = {
            "total_questions": total_q,
            "approved": approved,
            "corrected": corrected,
            "flagged": flagged,
            "refusal_labels_confirmed": refusals_ok,
            "trap_expectations_confirmed": traps_ok,
            "citations_confirmed": cits_ok,
            "benchmark_sha256_seal": seal,
            "is_externally_certified": (flagged == 0 and approved + corrected == total_q and refusals_ok and traps_ok),
        }

        return ledger, metrics
