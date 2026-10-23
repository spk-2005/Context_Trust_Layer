"""
Synchronize DOC-057 Claims in PostgreSQL Database with v3 Canonical Claims.

Applies Sprint AF-13 certified claim dispositions:
- 67 Canonical atomic policy rules -> status: VERIFIED, claim_type: 'rule'
- 29 Non-canonical items (fragments, non-rules, duplicates, quarantined):
  * Fragments (#54, #63, #77, #83, #84) -> status: REJECTED, claim_type: 'fragment'
  * Collapsed Duplicates -> status: REJECTED, claim_type: 'duplicate'
  * Definitions -> status: CANDIDATE, claim_type: 'definition'
  * Descriptions -> status: CANDIDATE, claim_type: 'description'
  * Cross-references (#4, etc.) -> status: CANDIDATE, claim_type: 'reference'
  * Responsibilities -> status: CANDIDATE, claim_type: 'responsibility'
  * Quarantined compound claims -> status: CANDIDATE, claim_type: 'quarantined'
- Resolves false conflict on termination clauses (#83 / #96) -> resolution_status: 'dismissed'
"""

import asyncio
import json
import logging
import sys
from pathlib import Path

backend_dir = Path("backend")
sys.path.insert(0, str(backend_dir))

from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, ConflictStatus
from sqlalchemy import text

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("sync_v3_claims")

PARTITION_FILE = Path("research/validation_50/scratch/doc057_partition.json")


async def sync_claims():
    if not PARTITION_FILE.exists():
        raise FileNotFoundError(f"{PARTITION_FILE} does not exist.")

    partition = json.loads(PARTITION_FILE.read_text(encoding="utf-8"))
    canonical_cids = set(partition["canonical_cids"])
    non_canonical_cids = set(partition["non_canonical_cids"])

    logger.info("Loaded partition: %d canonical, %d non-canonical", len(canonical_cids), len(non_canonical_cids))
    assert len(canonical_cids) == 67, f"Expected 67 canonical, got {len(canonical_cids)}"
    assert len(non_canonical_cids) == 29, f"Expected 29 non-canonical, got {len(non_canonical_cids)}"

    async with AsyncSessionLocal() as session:
        # 1. Update 67 canonical claims
        for cid in canonical_cids:
            await session.execute(
                text(
                    "UPDATE claims SET status = 'verified', claim_type = 'rule', updated_at = NOW() "
                    "WHERE id = :cid"
                ),
                {"cid": cid}
            )
        logger.info("Updated %d canonical claims to status='verified', claim_type='rule'", len(canonical_cids))

        # 2. Update 29 non-canonical claims
        cids_list = list(non_canonical_cids)
        res = await session.execute(
            text(
                "SELECT id, subject, predicate, claim_text FROM claims "
                "WHERE id = ANY(:cids)"
            ),
            {"cids": cids_list}
        )
        non_canon_rows = res.all()

        for r in non_canon_rows:
            cid, subj, pred, text_val = r
            full = f"{subj or ''} {pred or ''} {text_val or ''}".lower()
            subj_lower = (subj or "").lower()

            if "the following" in subj_lower:
                ct = "fragment"
                st = "rejected"
            elif "page 8" in full or (subj == "Microsoft" and pred == "update"):
                ct = "fragment"
                st = "rejected"
            elif "reno" in full or "sierra center" in full:
                ct = "fragment"
                st = "rejected"
            elif "without limiting other remedies" in full:
                ct = "fragment"
                st = "rejected"
            elif "failure to enforce" in subj_lower:
                ct = "definition"
                st = "candidate"
            elif "any attempted assignment" in subj_lower:
                ct = "definition"
                st = "candidate"
            elif subj_lower == "assignment" and pred == "relieve":
                ct = "definition"
                st = "candidate"
            elif "product terms" in full and ("cancelat" in full or "details about" in full):
                ct = "reference"
                st = "candidate"
            elif "all other changes will apply when they are published on the product terms site" in full:
                ct = "reference"
                st = "candidate"
            elif "sla terms and service level commitments" in full:
                ct = "reference"
                st = "candidate"
            elif "professional services scope documents" in full:
                ct = "reference"
                st = "candidate"
            elif "product availability may vary by region" in full:
                ct = "description"
                st = "candidate"
            elif "termination without cause will not affect" in full:
                ct = "description"
                st = "candidate"
            elif "fixes are licensed under the same terms" in full:
                ct = "description"
                st = "candidate"
            elif "partners provide support for products" in full or (subj == "Partner" and pred == "provide"):
                ct = "description"
                st = "candidate"
            elif "current software version is described" in full:
                ct = "description"
                st = "candidate"
            elif "software does not include online services" in full or (subj_lower == "software" and "online" in full):
                ct = "definition"
                st = "candidate"
            elif "customer data does not include professional services data" in full:
                ct = "definition"
                st = "candidate"
            elif "subscriptions expire at the end" in full:
                ct = "definition"
                st = "candidate"
            elif "direct damages liability for free offers" in full:
                ct = "definition"
                st = "candidate"
            elif "all intellectual property rights not expressly granted" in full:
                ct = "definition"
                st = "candidate"
            elif "licenses are solely for customer's own use" in full:
                ct = "definition"
                st = "candidate"
            elif "attempted license transfers that do not comply" in full:
                ct = "definition"
                st = "candidate"
            elif "remains responsible for their performance under this agreement through its affiliates" in full:
                ct = "responsibility"
                st = "candidate"
            elif "remains responsible for the performance of those services" in full or pred == "remains_responsible_for":
                ct = "responsibility"
                st = "candidate"
            elif "customer is responsible for any use of the products that does not comply" in full:
                ct = "responsibility"
                st = "candidate"
            elif "notify" in pred and "assignment" in full:
                ct = "duplicate"
                st = "rejected"
            elif "pay for all services provided or used before termination" in full:
                ct = "duplicate"
                st = "rejected"
            elif pred == "sublicense" or "sublicense" in full:
                ct = "quarantined"
                st = "candidate"
            else:
                ct = "fragment"
                st = "rejected"

            await session.execute(
                text("UPDATE claims SET status = :st, claim_type = :ct, updated_at = NOW() WHERE id = :cid"),
                {"st": st, "ct": ct, "cid": cid}
            )

        # 3. Dismiss false conflict on termination clauses
        conflict_res = await session.execute(
            text(
                "UPDATE claim_conflicts SET resolution_status = 'dismissed' "
                "WHERE id = '0ac2dabd-9cf7-412a-8e41-9f74419ba299' OR "
                "claim_a_id = 'b3ac25b4-d192-51ca-ba27-25628736f2cc' OR "
                "claim_b_id = 'b3ac25b4-d192-51ca-ba27-25628736f2cc'"
            )
        )
        logger.info("Updated false conflicts on #83/#96 to resolution_status='dismissed'")

        await session.commit()

        # 4. Verify post-sync counts
        verify_stmt = await session.execute(
            text(
                "SELECT status, claim_type, count(*) "
                "FROM claims "
                "WHERE document_version_id = 'cae9c9dc-e923-4652-864d-dd2085a5679a' "
                "GROUP BY status, claim_type "
                "ORDER BY count(*) DESC"
            )
        )
        breakdown = verify_stmt.all()
        logger.info("DOC-057 Post-Sync Database Breakdown:")
        for st, ct, cnt in breakdown:
            logger.info("  status=%-10s claim_type=%-15s count=%d", st, ct, cnt)

        # Confirm 67 verified canonical rules
        v_res = await session.execute(
            text(
                "SELECT count(*) FROM claims "
                "WHERE document_version_id = 'cae9c9dc-e923-4652-864d-dd2085a5679a' "
                "AND status = 'verified' AND claim_type = 'rule'"
            )
        )
        verified_rule_count = v_res.scalar()
        logger.info("Verified Canonical Rule Count: %d / 67", verified_rule_count)
        assert verified_rule_count == 67, f"Expected 67 verified rules, got {verified_rule_count}"


if __name__ == "__main__":
    asyncio.run(sync_claims())
