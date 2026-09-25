import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.document import Document
from app.schemas.drift import (
    ClaimDecayItem,
    ClaimRemediateRequest,
    ClaimRemediateResponse,
    DriftAnalysisResponse,
)

logger = logging.getLogger(__name__)

# Resilient in-memory fallback store for demo & offline mode
_IN_MEMORY_DRIFT_CLAIMS: Dict[str, Dict[str, Any]] = {}


def _calculate_decay(age_days: int, initial_trust: float) -> Tuple[float, float, str, str]:
    """Computes decayed trust, decay percentage, drift category, and recommended governance action."""
    if age_days <= 30:
        factor = 1.00
        category = "ACTIVE_FRESH"
        action = "None: Knowledge is current and authoritative."
    elif age_days <= 90:
        factor = 0.92
        category = "AGING_WARNING"
        action = "Monitor: Policy approaches 90-day review horizon."
    elif age_days <= 180:
        factor = 0.75
        category = "STALE_TEMPORAL"
        action = "Re-Attest: Request Data Owner verification to renew freshness."
    else:
        factor = 0.50
        category = "SEVERELY_DECAYED"
        action = "Urgent: Retire or replace expired policy claim."

    current_trust = round(initial_trust * factor, 2)
    decay_pct = round((1.0 - factor) * 100.0, 1)
    return current_trust, decay_pct, category, action


def _seed_drift_claims_if_empty(org_id: uuid.UUID):
    org_key = str(org_id)
    existing = [c for c in _IN_MEMORY_DRIFT_CLAIMS.values() if c["organization_id"] == org_key]
    if not existing:
        now = datetime.now(timezone.utc)
        items = [
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555551"),
                "organization_id": org_key,
                "claim_text": "Refund processing window is strictly limited to 30 calendar days from delivery.",
                "document_title": "Customer Returns & Refund Policy 2026",
                "created_at": now - timedelta(days=15),
                "initial_trust": 0.95,
                "status": "ACTIVE",
            },
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555552"),
                "organization_id": org_key,
                "claim_text": "Remote work internet stipends are disbursed automatically on the first pay cycle of employment.",
                "document_title": "Employee Handbook (Global Remote Guidelines)",
                "created_at": now - timedelta(days=48),
                "initial_trust": 0.90,
                "status": "ACTIVE",
            },
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555553"),
                "organization_id": org_key,
                "claim_text": "Purchase orders under $5,000 do not require dual-custody approval or C-level signature.",
                "document_title": "Procurement & Vendor Payment SOP v1.2",
                "created_at": now - timedelta(days=125),
                "initial_trust": 0.88,
                "status": "ACTIVE",
            },
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555554"),
                "organization_id": org_key,
                "claim_text": "Production firewall port 8080 may remain open for external staging ingress without CISO change approval.",
                "document_title": "Legacy Cloud Infrastructure Runbook 2024",
                "created_at": now - timedelta(days=220),
                "initial_trust": 0.85,
                "status": "ACTIVE",
            },
            {
                "claim_id": uuid.UUID("55555555-5555-5555-5555-555555555555"),
                "organization_id": org_key,
                "claim_text": "Data subject access requests (DSAR) must be fulfilled within 45 days under standard processing.",
                "document_title": "Privacy & GDPR Compliance Standard",
                "created_at": now - timedelta(days=98),
                "initial_trust": 0.92,
                "status": "ACTIVE",
            },
        ]
        for it in items:
            _IN_MEMORY_DRIFT_CLAIMS[str(it["claim_id"])] = it


async def analyze_context_drift(
    organization_id: uuid.UUID,
    session: Optional[AsyncSession] = None,
) -> DriftAnalysisResponse:
    """Calculates temporal decay, stale claims, and context freshness index."""
    now = datetime.now(timezone.utc)
    decay_items: List[ClaimDecayItem] = []

    # Attempt to load from database if available
    db_claims = []
    if session:
        try:
            stmt = (
                select(Claim)
                .where(Claim.organization_id == organization_id)
                .options(
                    selectinload(Claim.trust_scores),
                    selectinload(Claim.evidence),
                )
            )
            res = await session.execute(stmt)
            db_claims = res.scalars().all()
        except Exception as e:
            logger.debug(f"DB load failed for drift analysis, using fallback: {e}")

    if db_claims:
        for c in db_claims:
            created = c.created_at or now
            age_days = max(0, (now - created).days)
            init_trust = 0.90
            if c.trust_scores:
                init_trust = float(c.trust_scores[0].confidence_score or 0.90)

            cur_trust, dec_pct, cat, rec_act = _calculate_decay(age_days, init_trust)
            doc_title = "Internal Knowledge Base"
            if c.evidence and len(c.evidence) > 0 and c.evidence[0].document:
                doc_title = c.evidence[0].document.title

            decay_items.append(
                ClaimDecayItem(
                    claim_id=c.id,
                    claim_text=c.claim_text,
                    document_title=doc_title,
                    created_at=created,
                    age_days=age_days,
                    initial_trust=init_trust,
                    current_decayed_trust=cur_trust,
                    decay_pct=dec_pct,
                    drift_category=cat,
                    recommended_action=rec_act,
                )
            )
    else:
        # Fallback in-memory
        _seed_drift_claims_if_empty(organization_id)
        org_key = str(organization_id)
        raw_items = [c for c in _IN_MEMORY_DRIFT_CLAIMS.values() if c["organization_id"] == org_key]

        for r in raw_items:
            age_days = max(0, (now - r["created_at"]).days)
            cur_trust, dec_pct, cat, rec_act = _calculate_decay(age_days, r["initial_trust"])
            decay_items.append(
                ClaimDecayItem(
                    claim_id=r["claim_id"],
                    claim_text=r["claim_text"],
                    document_title=r["document_title"],
                    created_at=r["created_at"],
                    age_days=age_days,
                    initial_trust=r["initial_trust"],
                    current_decayed_trust=cur_trust,
                    decay_pct=dec_pct,
                    drift_category=cat,
                    recommended_action=rec_act,
                )
            )

    total_claims = len(decay_items)
    fresh_count = sum(1 for d in decay_items if d.drift_category == "ACTIVE_FRESH")
    decayed_count = total_claims - fresh_count
    avg_age = int(sum(d.age_days for d in decay_items) / max(1, total_claims))

    # Freshness index
    freshness_index = round(
        (sum(d.current_decayed_trust for d in decay_items) / max(1, sum(d.initial_trust for d in decay_items))) * 100.0,
        1
    ) if decay_items else 100.0

    # Radar breakdown
    radar = {
        "<30d (Fresh)": sum(1 for d in decay_items if d.age_days <= 30),
        "30-90d (Aging)": sum(1 for d in decay_items if 30 < d.age_days <= 90),
        "90-180d (Stale)": sum(1 for d in decay_items if 90 < d.age_days <= 180),
        ">180d (Severely Decayed)": sum(1 for d in decay_items if d.age_days > 180),
    }

    stale_docs = len({d.document_title for d in decay_items if d.age_days > 90})

    return DriftAnalysisResponse(
        organization_id=organization_id,
        analyzed_at=now,
        total_claims=total_claims,
        fresh_claims_count=fresh_count,
        decayed_claims_count=decayed_count,
        stale_documents_count=stale_docs,
        average_age_days=avg_age,
        freshness_index_pct=freshness_index,
        decay_radar=radar,
        decayed_claims=sorted(decay_items, key=lambda x: x.age_days, reverse=True),
    )


async def remediate_claim_decay(
    req: ClaimRemediateRequest,
    session: Optional[AsyncSession] = None,
) -> ClaimRemediateResponse:
    """Remediates a decayed claim via Data Owner Re-Attestation or Retirement."""
    now = datetime.now(timezone.utc)
    cid_str = str(req.claim_id)

    action_clean = req.action.upper()
    if action_clean not in ("RE_ATTEST", "RETIRE"):
        action_clean = "RE_ATTEST"

    if action_clean == "RE_ATTEST":
        new_status = "ACTIVE"
        new_trust = 0.95
        msg = "Claim re-attested by Data Owner: Freshness clock reset to 0 days."
    else:
        new_status = "SUPERSEDED"
        new_trust = 0.00
        msg = "Claim retired and deprecated: Excluded from future agent RAG retrieval."

    # Update in-memory fallback
    if cid_str in _IN_MEMORY_DRIFT_CLAIMS:
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["created_at"] = now
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["status"] = new_status
        _IN_MEMORY_DRIFT_CLAIMS[cid_str]["initial_trust"] = new_trust

    # Update DB if available
    if session:
        try:
            stmt = select(Claim).where(Claim.id == req.claim_id)
            res = await session.execute(stmt)
            claim = res.scalar_one_or_none()
            if claim:
                if action_clean == "RE_ATTEST":
                    claim.status = ClaimStatus.VERIFIED
                    claim.created_at = now
                else:
                    claim.status = ClaimStatus.SUPERSEDED
                await session.commit()
        except Exception as e:
            logger.debug(f"DB update failed during claim remediation: {e}")

    return ClaimRemediateResponse(
        claim_id=req.claim_id,
        action_taken=action_clean,
        new_status=new_status,
        new_trust_score=new_trust,
        message=msg,
        timestamp=now,
    )
