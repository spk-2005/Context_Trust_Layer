import asyncio
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import select, delete, or_
from sqlalchemy.orm import selectinload

from app.db.database import AsyncSessionLocal
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.enums import ClaimStatus, ConflictStatus
from app.conflict_engine.detector import are_claims_topically_related
from app.llm.mock_provider import MockLLMProvider
from app.services.trust_service import TrustService


async def clean_database():
    print("Connecting to database...")
    evaluator = MockLLMProvider()

    async with AsyncSessionLocal() as session:
        # Load all unresolved conflicts
        stmt = (
            select(ClaimConflict)
            .where(ClaimConflict.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED)
            .options(
                selectinload(ClaimConflict.claim_a),
                selectinload(ClaimConflict.claim_b),
            )
        )
        res = await session.execute(stmt)
        conflicts = res.scalars().all()
        print(f"Loaded {len(conflicts)} pending conflicts from DB.")

        to_delete_ids = []
        valid_conflicts = 0
        affected_claim_ids = set()

        for c in conflicts:
            if not c.claim_a or not c.claim_b:
                to_delete_ids.append(c.id)
                continue

            # 1. Fast topical filter
            if not are_claims_topically_related(c.claim_a, c.claim_b):
                to_delete_ids.append(c.id)
                affected_claim_ids.add(c.claim_a_id)
                affected_claim_ids.add(c.claim_b_id)
                continue

            # 2. Strict evaluation
            eval_res = await evaluator.evaluate_contradiction(
                c.claim_a.claim_text,
                c.claim_b.claim_text,
            )

            if not eval_res.is_contradiction:
                to_delete_ids.append(c.id)
                affected_claim_ids.add(c.claim_a_id)
                affected_claim_ids.add(c.claim_b_id)
            else:
                valid_conflicts += 1

        print(f"Purging {len(to_delete_ids)} false-positive conflicts; keeping {valid_conflicts} genuine conflicts...")

        # Batch delete in chunks
        chunk_size = 500
        for i in range(0, len(to_delete_ids), chunk_size):
            chunk = to_delete_ids[i:i + chunk_size]
            await session.execute(delete(ClaimConflict).where(ClaimConflict.id.in_(chunk)))

        await session.flush()

        # Reset claims status if no longer conflicted
        trust_service = TrustService(session)
        reset_claims_count = 0
        for claim_id in affected_claim_ids:
            remaining_stmt = select(ClaimConflict).where(
                or_(
                    ClaimConflict.claim_a_id == claim_id,
                    ClaimConflict.claim_b_id == claim_id,
                ),
                ClaimConflict.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED,
            )
            rem_res = await session.execute(remaining_stmt)
            if not rem_res.scalars().first():
                claim = await session.get(Claim, claim_id)
                if claim and claim.status == ClaimStatus.CONFLICTED:
                    claim.status = ClaimStatus.VERIFIED
                    await trust_service.calculate_for_claim(claim_id)
                    reset_claims_count += 1

        await session.commit()
        print(f"Cleanup finished! Purged {len(to_delete_ids)} bogus conflicts. Reset {reset_claims_count} claims to VERIFIED. Genuine conflicts remaining: {valid_conflicts}.")


if __name__ == "__main__":
    asyncio.run(clean_database())
