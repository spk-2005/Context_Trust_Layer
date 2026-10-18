"""
CLI Tool for Asynchronous Human Adjudication Queue.

Commands:
  python scripts/review_queue.py list [--doc DOC-005]
  python scripts/review_queue.py stats
  python scripts/review_queue.py resolve --id QUEUE-DOC-005-xxxx --disposition GOLD_LABEL_GAP --rationale "..."
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Add project root to path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from research.adjudication_queue.queue_manager import AdjudicationQueueManager


def main():
    parser = argparse.ArgumentParser(description="Human Adjudication Queue Manager")
    subparsers = parser.add_subparsers(dest="command", help="Subcommand")

    # List command
    list_p = subparsers.add_parser("list", help="List pending claims")
    list_p.add_argument("--doc", type=str, default=None, help="Filter by document ID (e.g. DOC-005)")

    # Stats command
    subparsers.add_parser("stats", help="Show queue statistics")

    # Resolve command
    res_p = subparsers.add_parser("resolve", help="Adjudicate a pending claim")
    res_p.add_argument("--id", required=True, help="Queue ID")
    res_p.add_argument("--disposition", required=True, choices=["GOLD_LABEL_GAP", "VALID", "INVALID", "NON_SOURCE_BACKED", "NOISE"], help="Adjudication decision")
    res_p.add_argument("--rationale", required=True, help="Reasoning for disposition")
    res_p.add_argument("--reviewer", default="Compliance Specialist", help="Reviewer identifier")
    res_p.add_argument("--merge", action="store_true", help="Merge into certified adjudications.json")

    args = parser.parse_args()
    qm = AdjudicationQueueManager()

    if args.command == "list":
        pending = qm.list_pending(args.doc)
        print(f"=== Pending Adjudication Queue ({len(pending)} items) ===")
        for item in pending:
            print(f"[{item['queue_id']}] {item['document_id']} | Claim: {item['claim_id'][:8]}...")
            print(f"   Subject: {item['subject']} | Predicate: {item['predicate']}")
            print(f"   Object: {item['object'][:60]}...")
            print(f"   Reason: {item['trigger_reason']} (Trust: {item['composite_trust_score']:.2f})")
            print()

    elif args.command == "stats":
        stats = qm.get_stats()
        print("=== Adjudication Queue Statistics ===")
        print(f"Total Enqueued: {stats['total_items']}")
        print(f"Pending:        {stats['pending_count']}")
        print(f"Adjudicated:    {stats['adjudicated_count']}")
        print("By Document:")
        for doc, count in stats["by_document"].items():
            print(f"  {doc}: {count}")

    elif args.command == "resolve":
        rec = qm.adjudicate_item(
            queue_id=args.id,
            disposition=args.disposition,
            rationale=args.rationale,
            reviewer=args.reviewer,
            merge_to_certified=args.merge,
        )
        if rec:
            print(f"Successfully adjudicated {args.id} -> {args.disposition}")
            if args.merge:
                print("Merged into certified adjudications.json")
        else:
            print(f"Error: Queue ID {args.id} not found in pending queue.")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()