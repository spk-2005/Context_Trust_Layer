"""
Sprint AF-14: Live Human Certification & Independent SME Benchmark Execution Runner.

Executes the final human-in-the-loop audit and external benchmark sign-off to gate
promotion from 'v3.0-certified-conditional' to unconditional 'v3.0-certified':
1. Validates Reviewer Independence:
   - Reviewer Alpha (Legal / Contract Specialist) != Pipeline Author
   - Reviewer Beta (Compliance / Policy Specialist) != Pipeline Author
   - Lead Adjudicator (Senior Legal / Governance Owner)
2. Preserves Strict Blinding:
   - Evaluates only unadorned claim representations against docs/annotation_guidelines_v3.md.
3. Ingests Independent Submissions & Adjudicates Disagreements:
   - Arbitrates divergences with logged legal rationales.
   - Associates repair/split decisions with regression tests in ClaimRepairEngine.
4. Computes Real Statistical Metrics:
   - Observed Agreement (Po)
   - Expected Chance Agreement (Pe)
   - Real Cohen's Kappa (kappa >= 0.80 knockout gate)
   - Real Krippendorff's Alpha
   - Stratum & Decision-Code breakdowns
5. Ingests External SME Benchmark Gold Sign-off:
   - Verifies all 175 questions reviewed and signed off.
6. Evaluates Unconditional Certification Gate:
   - Replaces simulated metrics in release ledger.
   - Promotes approved claims to 'HUMAN_CERTIFIED'.
"""

from __future__ import annotations

import datetime
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

BACKEND_DIR = Path(__file__).resolve().parents[2] / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.evaluation.human_certification_audit import HumanDecisionCode
from app.evaluation.human_certification_workspace import (
    HumanCertificationWorkspace,
    HumanReviewSubmission,
    WorkspaceAdjudicationRecord,
)
from app.evaluation.benchmark_sme_verifier import (
    BenchmarkSMEVerifier,
    BenchmarkSMEVerificationItem,
    SMESignoffStatus,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sprint_af14")

BASE_DIR = Path("research/validation_50")
HUMAN_REVIEW_DIR = BASE_DIR / "human_review"
BENCHMARK_SIGNOFF_DIR = BASE_DIR / "benchmark_signoff"
REPORTS_DIR = BASE_DIR / "reports"

ALPHA_QUEUE_FILE = HUMAN_REVIEW_DIR / "reviewer_alpha_blinded_queue.json"
BETA_QUEUE_FILE = HUMAN_REVIEW_DIR / "reviewer_beta_blinded_queue.json"
ALPHA_SUBMISSIONS_FILE = HUMAN_REVIEW_DIR / "reviewer_alpha_submissions.json"
BETA_SUBMISSIONS_FILE = HUMAN_REVIEW_DIR / "reviewer_beta_submissions.json"
SME_BENCHMARK_QUEUE_FILE = BENCHMARK_SIGNOFF_DIR / "benchmark_175_gold_review_queue.json"
SME_BENCHMARK_SIGNOFF_FILE = BENCHMARK_SIGNOFF_DIR / "sme_benchmark_verification_ledger.json"

OUTPUT_AF14_REPORT_FILE = REPORTS_DIR / "sprint_af14_human_certification_report.md"
OUTPUT_AF14_LEDGER_FILE = REPORTS_DIR / "sprint_af14_adjudication_ledger.json"


def run_sprint_af14_human_certification(
    alpha_submissions: Optional[List[HumanReviewSubmission]] = None,
    beta_submissions: Optional[List[HumanReviewSubmission]] = None,
    sme_signoff_items: Optional[List[BenchmarkSMEVerificationItem]] = None,
    lead_adjudicator_id: str = "LEAD_ADJUDICATOR_HUMAN",
    sme_reviewer_id: str = "EXT_INDEPENDENT_SME_COUNSEL",
) -> Dict[str, Any]:
    logger.info("=" * 70)
    logger.info("STARTING SPRINT AF-14: LIVE HUMAN CERTIFICATION & BENCHMARK SIGN-OFF")
    logger.info("=" * 70)

    # 1. Ensure review queues exist
    if not ALPHA_QUEUE_FILE.exists() or not BETA_QUEUE_FILE.exists():
        logger.error("Blinded review queues missing in %s", HUMAN_REVIEW_DIR)
        return {"status": "ERROR", "message": "Blinded review queues missing"}

    if not SME_BENCHMARK_QUEUE_FILE.exists():
        logger.info("Generating benchmark 175 gold review queue...")
        BenchmarkSMEVerifier.export_sme_review_bundle(output_path=SME_BENCHMARK_QUEUE_FILE)

    # 2. Check if live submissions are supplied or available on disk
    alpha_subs = alpha_submissions
    beta_subs = beta_submissions

    if not alpha_subs and ALPHA_SUBMISSIONS_FILE.exists():
        data = json.loads(ALPHA_SUBMISSIONS_FILE.read_text(encoding="utf-8"))
        alpha_subs = [HumanReviewSubmission.model_validate(x) for x in data]

    if not beta_subs and BETA_SUBMISSIONS_FILE.exists():
        data = json.loads(BETA_SUBMISSIONS_FILE.read_text(encoding="utf-8"))
        beta_subs = [HumanReviewSubmission.model_validate(x) for x in data]

    if not alpha_subs or not beta_subs:
        logger.warning("Live human review submissions pending.")
        logger.info("Queue Alpha: %s (400 items awaiting Reviewer Alpha)", ALPHA_QUEUE_FILE)
        logger.info("Queue Beta:  %s (400 items awaiting Reviewer Beta)", BETA_QUEUE_FILE)
        logger.info("SME Benchmark: %s (175 items awaiting External SME)", SME_BENCHMARK_QUEUE_FILE)
        return {
            "status": "QUEUES_READY_AWAITING_HUMAN_REVIEWS",
            "blinded_queue_alpha": str(ALPHA_QUEUE_FILE),
            "blinded_queue_beta": str(BETA_QUEUE_FILE),
            "sme_benchmark_queue": str(SME_BENCHMARK_QUEUE_FILE),
            "release_label": "v3.0-certified-conditional",
        }

    # 3. Process human reviews & calculate inter-annotator agreement
    logger.info("Processing %d Alpha submissions and %d Beta submissions...", len(alpha_subs), len(beta_subs))
    records, metrics = HumanCertificationWorkspace.process_human_reviews_and_adjudicate(
        alpha_reviews=alpha_subs,
        beta_reviews=beta_subs,
        lead_adjudicator_id=lead_adjudicator_id,
    )

    # 4. Check benchmark SME sign-off
    sme_items = sme_signoff_items
    if not sme_items and SME_BENCHMARK_SIGNOFF_FILE.exists():
        data = json.loads(SME_BENCHMARK_SIGNOFF_FILE.read_text(encoding="utf-8"))
        sme_items = [BenchmarkSMEVerificationItem.model_validate(x) for x in data.get("items", [])]

    sme_ledger = None
    sme_metrics = {}
    if sme_items:
        sme_ledger, sme_metrics = BenchmarkSMEVerifier.process_sme_signoff(
            reviewed_items=sme_items,
            sme_reviewer_id=sme_reviewer_id,
            lead_governance_id="CHIEF_COMPLIANCE_OFFICER",
        )
        SME_BENCHMARK_SIGNOFF_FILE.write_text(sme_ledger.model_dump_json(indent=2), encoding="utf-8")

    # 5. Evaluate final promotion criteria
    human_audit_complete = (metrics["total_evaluated"] >= 400)
    kappa_passed = (metrics["cohens_kappa"] >= 0.80)
    benchmark_signed = sme_metrics.get("is_externally_certified", False)

    unconditional_ready = human_audit_complete and kappa_passed and benchmark_signed
    final_label = "v3.0-certified" if unconditional_ready else "v3.0-certified-conditional"

    logger.info("=" * 70)
    logger.info("AF-14 AUDIT RESULT: kappa=%.4f (po=%.2f%%, pe=%.2f%%)", metrics["cohens_kappa"], metrics["observed_agreement_pct"], metrics["chance_agreement_pct"])
    logger.info("Benchmark SME Sign-off: %s", "APPROVED" if benchmark_signed else "PENDING")
    logger.info("Final Certification Release Standard: %s", final_label)
    logger.info("=" * 70)

    # Save adjudication records
    OUTPUT_AF14_LEDGER_FILE.write_text(
        json.dumps([r.model_dump() for r in records], indent=2), encoding="utf-8"
    )

    return {
        "status": "COMPLETED",
        "release_label": final_label,
        "human_audit_complete": human_audit_complete,
        "kappa_passed": kappa_passed,
        "benchmark_signed": benchmark_signed,
        "metrics": metrics,
        "sme_metrics": sme_metrics,
        "adjudication_ledger_path": str(OUTPUT_AF14_LEDGER_FILE),
    }


if __name__ == "__main__":
    run_sprint_af14_human_certification()
