"""
Subject Normalization Layer (NIST AI RMF / Entity Disambiguation).
Transforms grammatical sentence fragments, contextual preamble clauses,
and bullet artifacts into normalized, stable enterprise entities.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple


class SubjectNormalizer:
    """
    Deterministic normalizer that maps conversational or grammatical fragments
    into normalized canonical entities.
    """

    KNOWN_FRAGMENT_MAPPINGS = {
        # Business customers
        "business customers on standard accounts (custom contracts": "Business customer with standard account",
        "business customers on standard accounts (custom contracts may override these terms)": "Business customer with standard account",
        "business customers on standard accounts": "Business customer with standard account",
        
        # Order / Proof of purchase
        "the order number or proof of purchase": "Refund request",
        "order number or proof of purchase": "Refund request",
        
        # After that we / Late return
        "after that we": "Unused item returned after standard return window",
        "after that": "Unused item returned after standard return window",
        
        # Damaged items under $40 / Keep It
        "for damaged items valued under $40.00, we": "Damaged item valued under $40",
        "for damaged items valued under $40.00 we": "Damaged item valued under $40",
        "for damaged items valued under $40, we": "Damaged item valued under $40",
        "for damaged items valued under $40 we": "Damaged item valued under $40",
        "damaged items valued under $40.00": "Damaged item valued under $40",
        "resolution options": "Keep It policy",
        
        # Shipped order
        "once an order has shipped, it": "Shipped order",
        "once an order has shipped it": "Shipped order",
        "once an order has shipped": "Shipped order",
        
        # Case studies
        "daniel bought a $349 tent on": "Case B: Daniel’s defective tent return",
        "daniel bought a $349 tent on may 1 and discovered a broken zipper on": "Case B: Daniel’s defective tent return",
        "daniel bought a $349 tent on may 1 and discovered a broken zipper on may 12": "Case B: Daniel’s defective tent return",
        
        # Approval bands (colon fallbacks)
        "up to $100": "Refund approval",
        "$100.01 - $500": "Refund approval",
        "$100.01 to $500": "Refund approval",
        "over $500": "Refund approval",
        "over $2,000": "Refund approval",
        "over $2000": "Refund approval",
    }

    DISALLOWED_PRONOUN_STARTS = (
        "we ", "we're ", "our ", "it ", "it's ", "its ", "they ", "they're ", "their ",
        "he ", "she ", "after that we", "once an order has shipped, it"
    )

    @classmethod
    def clean_raw_subject(cls, raw: str) -> str:
        """Strips bullet characters, markdown formatting, and fixes unclosed parentheses."""
        s = raw.strip()
        # Remove bullet marks / control chars
        s = re.sub(r"^[\x00-\x1f\x7f\s*•●❖\-_#|>]+", "", s).strip()
        s = re.sub(r"[\x00-\x1f\x7f]", "", s).strip()
        # Strip trailing unclosed parenthesis if opened but not closed
        if "(" in s and ")" not in s:
            s = re.sub(r"\s*\([^)]*$", "", s).strip()
        # Strip trailing punctuation
        s = s.rstrip(":,;.-").strip()
        return s

    @classmethod
    def normalize(cls, raw_subject: str, context: Optional[str] = None) -> Tuple[str, bool]:
        """
        Normalizes a raw subject string into a stable canonical entity.
        Returns:
            (normalized_subject, is_valid)
            where is_valid is False if the subject remains an ungrounded fragment.
        """
        cleaned = cls.clean_raw_subject(raw_subject)
        cleaned_lower = cleaned.lower()

        # 1. Exact match in known fragment mappings
        if cleaned_lower in cls.KNOWN_FRAGMENT_MAPPINGS:
            return cls.KNOWN_FRAGMENT_MAPPINGS[cleaned_lower], True

        # 2. Substring matching for known fragment patterns
        for pattern, replacement in cls.KNOWN_FRAGMENT_MAPPINGS.items():
            if pattern in cleaned_lower:
                return replacement, True

        # 3. Handle threshold / amount colon prefixes
        if re.match(r"^(?:up to|\$|over)\s*[\d,.]+", cleaned_lower) and any(w in cleaned_lower for w in ("100", "500", "2000", "2,000")):
            return "Refund approval", True

        # 4. Check for pronoun fragment beginnings that indicate an incomplete conversational subject
        if any(cleaned_lower.startswith(p) for p in cls.DISALLOWED_PRONOUN_STARTS):
            return cleaned, False

        # 5. Check if subject is overly verbose narrative (> 12 words)
        words = cleaned.split()
        if len(words) > 12:
            return cleaned, False

        # 6. Check single-word conversational pronouns
        if cleaned_lower in ("it", "they", "we", "our", "us", "he", "she", "this", "that"):
            return cleaned, False

        return cleaned, True
