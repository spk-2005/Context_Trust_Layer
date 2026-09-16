import asyncio
import decimal
import re
import uuid
from datetime import datetime, timezone
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conflict_engine.detector import (
    ConflictDetector,
    _extract_content_tokens,
    are_claims_topically_related,
    is_illustrative_claim,
)
from app.db.enums import ClaimStatus, ConflictStatus, ReviewDecision
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.human_review import HumanReview
from app.db.repositories.conflict_repository import ConflictRepository
from app.llm.base import BaseLLMProvider


class ConflictService:
    """Service for running conflict detection and recording human resolutions."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.session = session
        self.detector = ConflictDetector(session, llm_provider=llm_provider)
        self.conflict_repo = ConflictRepository(session)

    async def run_conflict_detection_for_version(
        self,
        document_version_id: uuid.UUID,
    ) -> Sequence[ClaimConflict]:
        stmt = select(Claim).where(Claim.document_version_id == document_version_id)
        res = await self.session.execute(stmt)
        claims = res.scalars().all()

        conflicts: list[ClaimConflict] = []
        for claim in claims:
            found = await self.detector.detect_conflicts_for_claim(claim)
            conflicts.extend(found)

        return conflicts

    async def resolve_conflict(
        self,
        conflict_id: uuid.UUID,
        reviewer_id: uuid.UUID,
        decision: ReviewDecision,
        chosen_claim_id: uuid.UUID | None = None,
        reason: str | None = None,
    ) -> ClaimConflict:
        """Resolve a conflict with an audit trail in human_reviews."""
        conflict = await self.session.get(ClaimConflict, conflict_id)
        if not conflict:
            raise ValueError(f"Conflict {conflict_id} not found.")

        claim_a = await self.session.get(Claim, conflict.claim_a_id)
        claim_b = await self.session.get(Claim, conflict.claim_b_id)

        from app.services.trust_service import TrustService

        chosen_uuid = uuid.UUID(str(chosen_claim_id)) if chosen_claim_id else None
        reviewer_uuid = uuid.UUID(str(reviewer_id))

        # Update conflict status
        conflict.resolution_status = ConflictStatus.RESOLVED
        conflict.resolved_claim_id = chosen_uuid
        conflict.resolved_by = reviewer_uuid
        conflict.resolved_at = datetime.now(timezone.utc)

        # Update claim statuses based on decision
        if decision == ReviewDecision.APPROVE and chosen_uuid:
            if claim_a and claim_a.id == chosen_uuid:
                claim_a.status = ClaimStatus.VERIFIED
                if claim_b:
                    claim_b.status = ClaimStatus.OUTDATED
            elif claim_b and claim_b.id == chosen_uuid:
                claim_b.status = ClaimStatus.VERIFIED
                if claim_a:
                    claim_a.status = ClaimStatus.OUTDATED
            else:
                raise ValueError(
                    f"Chosen claim {chosen_uuid} is not part of this conflict (claims: {claim_a.id if claim_a else None}, {claim_b.id if claim_b else None})"
                )
        elif decision == ReviewDecision.REJECT:
            if claim_a:
                claim_a.status = ClaimStatus.REJECTED
            if claim_b:
                claim_b.status = ClaimStatus.REJECTED

        # Record audit log
        org_id = claim_a.organization_id if claim_a else claim_b.organization_id
        review = HumanReview(
            organization_id=org_id,
            reviewer_id=reviewer_uuid,
            target_type="claim_conflict",
            target_id=conflict.id,
            decision=decision,
            reason=reason,
        )
        self.session.add(review)
        await self.session.flush()

        # Recalculate trust scores for both claims
        trust_service = TrustService(self.session)
        if claim_a:
            await trust_service.calculate_for_claim(claim_a.id)
        if claim_b:
            await trust_service.calculate_for_claim(claim_b.id)

        await self.session.flush()
        await self.session.refresh(conflict)
        return conflict

    async def re_evaluate_all_pending(
        self,
        organization_id: uuid.UUID | None = None,
    ) -> dict[str, int]:
        """Re-evaluate all pending conflicts against the current evaluator rules, purging false positives."""
        stmt = (
            select(ClaimConflict)
            .where(ClaimConflict.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED)
            .options(
                selectinload(ClaimConflict.claim_a),
                selectinload(ClaimConflict.claim_b),
            )
        )
        res = await self.session.execute(stmt)
        conflicts = res.scalars().all()

        purged_count = 0
        retained_count = 0
        affected_claim_ids: set[uuid.UUID] = set()

        # Parallel evaluation of all conflicts
        async def _eval_conflict(c):
            if not c.claim_a or not c.claim_b:
                return c, None
            # Pillar 2: Illustrative claims do not form corporate governance contradictions
            if is_illustrative_claim(c.claim_a) or is_illustrative_claim(c.claim_b):
                return c, None
            if not are_claims_topically_related(c.claim_a, c.claim_b):
                return c, None
            eval_res = await self.detector.llm.evaluate_contradiction(
                claim_a_text=c.claim_a.claim_text,
                claim_b_text=c.claim_b.claim_text,
            )
            return c, eval_res

        eval_pairs = await asyncio.gather(*[_eval_conflict(c) for c in conflicts], return_exceptions=False)

        for c, eval_res in eval_pairs:
            is_temporal = bool(eval_res and eval_res.conflict_type == "temporal_outdated")
            text_a = (c.claim_a.claim_text if c.claim_a else "").lower()
            text_b = (c.claim_b.claim_text if c.claim_b else "").lower()
            has_temporal_contrast = ("legacy" in text_a and "current" in text_b) or ("legacy" in text_b and "current" in text_a)

            if not eval_res or not eval_res.is_contradiction or is_temporal or has_temporal_contrast:
                # Purge false-positive / auto-superseded conflict
                affected_claim_ids.add(c.claim_a_id)
                affected_claim_ids.add(c.claim_b_id)
                if is_temporal or has_temporal_contrast:
                    if "legacy" in text_a:
                        c.claim_a.status = ClaimStatus.OUTDATED
                        c.claim_b.status = ClaimStatus.VERIFIED
                    else:
                        c.claim_b.status = ClaimStatus.OUTDATED
                        c.claim_a.status = ClaimStatus.VERIFIED
                await self.session.delete(c)
                purged_count += 1
            else:
                # Update conflict metadata with refreshed reasoning / confidence
                c.conflict_type = eval_res.conflict_type
                c.severity = eval_res.severity
                c.confidence = decimal.Decimal(f"{eval_res.confidence:.4f}")
                retained_count += 1

        await self.session.flush()

        # Check and reset claim statuses if they no longer have any active conflicts
        from app.services.trust_service import TrustService
        trust_service = TrustService(self.session)

        for claim_id in affected_claim_ids:
            remaining_stmt = select(ClaimConflict).where(
                or_(
                    ClaimConflict.claim_a_id == claim_id,
                    ClaimConflict.claim_b_id == claim_id,
                ),
                ClaimConflict.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED,
            )
            rem_res = await self.session.execute(remaining_stmt)
            if not rem_res.scalars().first():
                claim = await self.session.get(Claim, claim_id)
                if claim and claim.status == ClaimStatus.CONFLICTED:
                    claim.status = ClaimStatus.VERIFIED
                    await trust_service.calculate_for_claim(claim_id)

        await self.session.commit()
        return {"purged": purged_count, "retained": retained_count}

    async def get_clustered_conflict_issues(
        self,
        organization_id: uuid.UUID | None = None,
        limit: int = 100,
    ) -> list[dict]:
        """Cluster individual pairwise conflicts into high-level Governance Issues."""
        conflicts = await self.conflict_repo.list_pending_review(
            organization_id=organization_id,
            limit=limit,
        )
        if not conflicts:
            return []

        clusters: dict[str, dict] = {}

        for c in conflicts:
            claim_a = c.claim_a
            claim_b = c.claim_b
            if not claim_a or not claim_b:
                continue

            sec_a = (claim_a.evidence[0].section if claim_a.evidence else None) or claim_a.subject or "Policy"
            sec_b = (claim_b.evidence[0].section if claim_b.evidence else None) or claim_b.subject or "Policy"

            # Consistent orientation: Side B is the authoritative / higher-trust candidate
            score_a = float(claim_a.trust_scores[0].overall_score) if claim_a.trust_scores else 0.50
            score_b = float(claim_b.trust_scores[0].overall_score) if claim_b.trust_scores else 0.50
            side_a, side_b = claim_a, claim_b
            side_sec_a, side_sec_b = sec_a, sec_b
            side_score_a, side_score_b = score_a, score_b

            if score_a > score_b:
                side_a, side_b = claim_b, claim_a
                side_sec_a, side_sec_b = sec_b, sec_a
                side_score_a, side_score_b = score_b, score_a

            # Extract common root intersection tokens to group all related permutations together
            tokens_a = _extract_content_tokens(claim_a.claim_text)
            tokens_b = _extract_content_tokens(claim_b.claim_text)
            common_tokens = tokens_a.intersection(tokens_b)

            # Determine topic name and cluster signature
            doc_topic = "Enterprise Policy"
            for candidate_sec in [side_sec_b, side_sec_a]:
                if candidate_sec and not re.search(r"[\u0900-\u097F]", candidate_sec):
                    clean_sec = re.sub(r"^(CURRENT|LEGACY)\s+EVIDENCE\s*—\s*", "", candidate_sec).strip()
                    if clean_sec and not clean_sec.startswith("effective"):
                        doc_topic = clean_sec
                        break

            if common_tokens:
                sig_tokens = sorted(list(common_tokens))[:2]
                topic_signature = "_".join(sig_tokens)
            else:
                combined_tokens = sorted(list(tokens_a.union(tokens_b)))[:2]
                topic_signature = "_".join(combined_tokens) if combined_tokens else "governance"

            cluster_key = f"{c.conflict_type}_{topic_signature}"

            if cluster_key not in clusters:
                clusters[cluster_key] = {
                    "issue_id": cluster_key,
                    "topic": f"{doc_topic} — {c.conflict_type.replace('_', ' ').title()}",
                    "conflict_type": c.conflict_type,
                    "severity": c.severity,
                    "confidence": float(c.confidence),
                    "cluster_a": {
                        "representative_claim_id": side_a.id,
                        "representative_text": side_a.claim_text,
                        "source_title": side_sec_a,
                        "section": side_sec_a,
                        "trust_score": side_score_a,
                        "claim_count": 0,
                        "claim_ids": set(),
                    },
                    "cluster_b": {
                        "representative_claim_id": side_b.id,
                        "representative_text": side_b.claim_text,
                        "source_title": side_sec_b,
                        "section": side_sec_b,
                        "trust_score": side_score_b,
                        "claim_count": 0,
                        "claim_ids": set(),
                    },
                    "conflict_ids": [],
                    "total_conflicts": 0,
                    "created_at": c.created_at,
                }

            cluster = clusters[cluster_key]
            cluster["conflict_ids"].append(c.id)
            cluster["total_conflicts"] += 1
            cluster["cluster_a"]["claim_ids"].add(side_a.id)
            cluster["cluster_b"]["claim_ids"].add(side_b.id)

            # Favor non-example text for representative display
            if "example" in cluster["cluster_a"]["representative_text"].lower() and "example" not in side_a.claim_text.lower():
                cluster["cluster_a"]["representative_text"] = side_a.claim_text
                cluster["cluster_a"]["representative_claim_id"] = side_a.id
            if "example" in cluster["cluster_b"]["representative_text"].lower() and "example" not in side_b.claim_text.lower():
                cluster["cluster_b"]["representative_text"] = side_b.claim_text
                cluster["cluster_b"]["representative_claim_id"] = side_b.id

        result = []
        for cl in clusters.values():
            cl["cluster_a"]["claim_count"] = len(cl["cluster_a"]["claim_ids"])
            cl["cluster_b"]["claim_count"] = len(cl["cluster_b"]["claim_ids"])
            cl["cluster_a"]["claim_ids"] = list(cl["cluster_a"]["claim_ids"])
            cl["cluster_b"]["claim_ids"] = list(cl["cluster_b"]["claim_ids"])
            result.append(cl)

        return result

    async def resolve_conflict_issue(
        self,
        issue_id: str,
        reviewer_id: uuid.UUID,
        decision: ReviewDecision,
        chosen_side: str,
        reason: str | None = None,
        organization_id: uuid.UUID | None = None,
    ) -> dict:
        """Resolve an entire clustered Governance Issue in a single atomic action."""
        issues = await self.get_clustered_conflict_issues(organization_id=organization_id, limit=200)
        target_issue = next((i for i in issues if i["issue_id"] == issue_id), None)
        if not target_issue:
            raise ValueError(f"Conflict Issue {issue_id} not found.")

        conflict_ids = target_issue["conflict_ids"]
        claims_a = target_issue["cluster_a"]["claim_ids"]
        claims_b = target_issue["cluster_b"]["claim_ids"]

        now = datetime.now(timezone.utc)
        reviewer_uuid = uuid.UUID(str(reviewer_id))

        # 1. Update all underlying pairwise conflicts to RESOLVED
        for conf_id in conflict_ids:
            conf = await self.session.get(ClaimConflict, conf_id)
            if conf:
                conf.resolution_status = ConflictStatus.RESOLVED
                conf.resolved_by = reviewer_uuid
                conf.resolved_at = now

        # 2. Update claim statuses
        winner_ids = claims_b if chosen_side == "B" else claims_a
        loser_ids = claims_a if chosen_side == "B" else claims_b

        for wid in winner_ids:
            claim = await self.session.get(Claim, wid)
            if claim:
                claim.status = ClaimStatus.VERIFIED

        for lid in loser_ids:
            claim = await self.session.get(Claim, lid)
            if claim:
                claim.status = ClaimStatus.OUTDATED

        # 3. Create HumanReview audit records
        from app.services.trust_service import TrustService
        trust_service = TrustService(self.session)

        review = HumanReview(
            organization_id=organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111"),
            reviewer_id=reviewer_uuid,
            target_type="conflict_issue",
            target_id=conflict_ids[0] if conflict_ids else uuid.uuid4(),
            decision=decision,
            reason=f"Batch issue resolution ({issue_id}): Chose Cluster {chosen_side}. {reason or ''}".strip(),
        )
        self.session.add(review)

        for cid in list(winner_ids) + list(loser_ids):
            await trust_service.calculate_for_claim(cid)

        await self.session.commit()
        return {
            "status": "success",
            "issue_id": issue_id,
            "resolved_conflicts_count": len(conflict_ids),
            "updated_claims_count": len(winner_ids) + len(loser_ids),
            "message": f"Successfully resolved Governance Issue {issue_id} ({len(conflict_ids)} underlying conflict pairs resolved).",
        }


