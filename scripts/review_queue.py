"""
CLI Tool for Blinded Independent Dual-Human Adjudication Queue.

Commands:
  python scripts/review_queue.py list [--doc DOC-005] [--reviewer reviewer_2]
  python scripts/review_queue.py review --id QUEUE-DOC-005-xxxx --reviewer reviewer_1 --disposition GOLD_LABEL_GAP --rationale "..."
  python scripts/review_queue.py adjudicate --id QUEUE-DOC-005-xxxx --adjudicator lead_compliance --disposition CORRECT_FULL_MATCH --rationale "..."
  python scripts/review_queue.py certify --id QUEUE-DOC-005-xxxx --officer governance_lead
  python scripts/review_queue.py stats
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from research.evaluation.adjudication_taxonomy import AdjudicationDisposition
from research.adjudication_queue.queue_manager import AdjudicationQueueManager


def main():
    parser = argparse.ArgumentParser(description="Blinded Dual-Human Adjudication Queue CLI")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # List command
    list_p = subparsers.add_parser("list", help="List claims in queue")
    list_p.add_argument("--doc", type=str, default=None, help="Filter by document ID (e.g. DOC-005)")
    list_p.add_argument("--reviewer", type=str, default=None, help="Reviewer identity for blinded view")

    # Stats command
    subparsers.add_parser("stats", help="Show queue statistics")

    # Review command (Reviewer A or Reviewer B)
    rev_p = subparsers.add_parser("review", help="Submit independent review (Reviewer A or B)")
    rev_p.add_argument("--id", required=True, help="Queue ID")
    rev_p.add_argument("--reviewer", required=True, help="Independent Human Reviewer ID")
    rev_p.add_argument(
        "--disposition",
        required=True,
        choices=[d.value for d in AdjudicationDisposition],
        help="Canonical 8-state adjudication disposition",
    )
    rev_p.add_argument("--rationale", required=True, help="Detailed grounding rationale")

    # Adjudicate command (Tie-breaker for disagreements)
    adj_p = subparsers.add_parser("adjudicate", help="Adjudicate disputed item (Third specialist)")
    adj_p.add_argument("--id", required=True, help="Queue ID")
    adj_p.add_argument("--adjudicator", required=True, help="Independent Adjudicator ID")
    adj_p.add_argument(
        "--disposition",
        required=True,
        choices=[d.value for d in AdjudicationDisposition],
        help="Canonical 8-state adjudication disposition",
    )
    adj_p.add_argument("--rationale", required=True, help="Binding adjudication reasoning")

    # Certify command (Promote agreed dual-review item into certified ledger)
    cert_p = subparsers.add_parser("certify", help="Promote verified item into certified adjudications")
    cert_p.add_argument("--id", required=True, help="Queue ID")
    cert_p.add_argument("--officer", required=True, help="Certifying Governance Officer ID")
    cert_p.add_argument("--no-merge", action="store_true", help="Do not write to adjudications.json")

    args = parser.parse_args()
    qm = AdjudicationQueueManager()

    if args.command == "list":
        items = qm.list_items(document_id=args.doc, blinded_for_reviewer=args.reviewer)
        print(f"=== Adjudication Queue ({len(items)} items) ===")
        for item in items:
            print(f"[{item['queue_id']}] Document: {item['document_id']} | Status: {item['status']}")
            print(f"   Claim: {item['claim_id'][:12]}... | Subject: {item['subject']} | Predicate: {item['predicate']}")
            print(f"   Object: {item['object'][:60]}...")
            print(f"   Reason: {item['trigger_reason']} (Trust: {item['composite_trust_score']:.2f})")
            if item.get("reviewer_a"):
                print(f"   Reviewer A: {item['reviewer_a']['reviewer_id']} -> {item['reviewer_a']['disposition']}")
            if item.get("reviewer_b"):
                print(f"   Reviewer B: {item['reviewer_b']['reviewer_id']} -> {item['reviewer_b']['disposition']}")
            if item.get("agreement"):
                print(f"   Agreement: {item['agreement']}")
            if item.get("adjudicator"):
                print(f"   Adjudicator: {item['adjudicator']['adjudicator_id']} -> {item['adjudicator']['final_disposition']}")
            print()

    elif args.command == "stats":
        stats = qm.get_stats()
        print("=== Dual-Human Adjudication Queue Statistics ===")
        print(f"Total Enqueued:             {stats['total_items']}")
        print(f"Pending Review A:           {stats['pending_review_a']}")
        print(f"Pending Review B (Blinded): {stats['pending_review_b']}")
        print(f"Ready For Certification:    {stats['ready_for_certification']}")
        print(f"Escalated To Adjudicator:   {stats['escalated_to_adjudicator']}")
        print(f"Certified:                  {stats['certified']}")
        print(f"Rejected:                   {stats['rejected']}")

    elif args.command == "review":
        try:
            item = qm.submit_review(
                queue_id=args.id,
                reviewer_id=args.reviewer,
                disposition=args.disposition,
                rationale=args.rationale,
            )
            print(f"Successfully recorded review by '{args.reviewer}' for {args.id}.")
            print(f"Queue Status: {item.status.value}")
            if item.agreement:
                print(f"Dual-Review Agreement: {item.agreement.value}")
        except Exception as e:
            print(f"[ERROR] Review rejected: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "adjudicate":
        try:
            item = qm.resolve_disagreement(
                queue_id=args.id,
                adjudicator_id=args.adjudicator,
                final_disposition=args.disposition,
                rationale=args.rationale,
            )
            print(f"Disagreement resolved by Adjudicator '{args.adjudicator}' for {args.id}.")
            print(f"Queue Status: {item.status.value} (Final Disposition: {item.adjudicator.final_disposition.value})")
        except Exception as e:
            print(f"[ERROR] Adjudication rejected: {e}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "certify":
        try:
            cert_record = qm.certify_item(
                queue_id=args.id,
                certifying_officer_id=args.officer,
                merge_to_certified=not args.no_merge,
            )
            print(f"SUCCESS: Certified adjudication record created: {cert_record['adjudication_id']}")
            print(f"Disposition: {cert_record['disposition']}")
            if not args.no_merge:
                print("Appended to certified research/evaluation/adjudications.json.")
        except Exception as e:
            print(f"[ERROR] Certification failed: {e}", file=sys.stderr)
            sys.exit(1)

    else:
        parser.print_help()


if __name__ == "__main__":
    main()