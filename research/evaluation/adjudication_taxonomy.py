"""
Canonical Adjudication Taxonomy for Context Layer AI.

Defines the authoritative 8-state disposition enum governing all candidate evaluations,
human adjudications, benchmark accounting, and certification ledgers.
"""

from enum import Enum


class AdjudicationDisposition(str, Enum):
    """Authoritative disposition taxonomy across review queue, harness, and ledgers."""

    CORRECT_FULL_MATCH = "CORRECT_FULL_MATCH"
    ACCEPTED_PARTIAL_MATCH = "ACCEPTED_PARTIAL_MATCH"
    INCORRECT = "INCORRECT"
    MALFORMED = "MALFORMED"
    DUPLICATE = "DUPLICATE"
    NON_CANONICAL = "NON_CANONICAL"
    GOLD_LABEL_GAP = "GOLD_LABEL_GAP"
    AMBIGUOUS_NEEDS_REVIEW = "AMBIGUOUS_NEEDS_REVIEW"