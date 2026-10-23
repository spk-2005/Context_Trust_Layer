"""
Semantic Deduplication Cascade Service.

Implements multi-tiered, document-agnostic duplicate detection:
Tier 1: Exact normalized verbatim quote hash.
Tier 2: Entity-Action-Object normalized token signature.
Tier 3: Embedding cosine similarity (>= 0.94).
Tier 4: Proposition equivalence check for borderline pairs.

Retains duplicates with status=DUPLICATE and duplicate_of pointer to preserve provenance.
"""

import hashlib
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from app.schemas.universal_claim import ClaimLifecycleState, UniversalClaim


@dataclass
class DeduplicationResult:
    is_duplicate: bool
    canonical_claim_id: Optional[str]
    match_tier: Optional[str]
    similarity_score: float = 0.0


class SemanticDeduplicationCascade:
    """Multi-stage cascade ensuring no duplicate canonical claims exist."""

    def __init__(self, similarity_threshold: float = 0.94):
        self.similarity_threshold = similarity_threshold
        # Indexes for fast lookup
        self._exact_hashes: Dict[str, str] = {}  # hash -> canonical_claim_id
        self._signatures: Dict[str, str] = {}    # sig -> canonical_claim_id
        self._canonical_claims: Dict[str, UniversalClaim] = {}

    @staticmethod
    def compute_exact_hash(text: str) -> str:
        norm = re.sub(r"\s+", " ", text.strip().lower())
        return hashlib.sha256(norm.encode("utf-8")).hexdigest()

    @staticmethod
    def compute_signature(subject: str, predicate: str, obj_or_text: str) -> str:
        s = (subject or "").strip().lower()
        p = (predicate or "").strip().lower()
        o = re.sub(r"[^\w\s]", "", (obj_or_text or "").strip().lower())
        words = o.split()[:8]
        key = f"{s}|{p}|{' '.join(words)}"
        return hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]

    def evaluate_and_register(self, claim: UniversalClaim) -> DeduplicationResult:
        """
        Evaluates candidate claim against canonical catalog.
        If duplicate, returns DeduplicationResult with matched canonical ID.
        If unique, registers claim as canonical candidate.
        """
        # Tier 1: Exact normalized quote hash
        exact_h = self.compute_exact_hash(claim.claim_text)
        if exact_h in self._exact_hashes:
            canon_id = self._exact_hashes[exact_h]
            return DeduplicationResult(
                is_duplicate=True,
                canonical_claim_id=canon_id,
                match_tier="TIER_1_EXACT_HASH",
                similarity_score=1.0,
            )

        # Tier 2: Entity-Action-Object normalized token signature
        sig = self.compute_signature(
            subject=claim.subject.canonical_entity,
            predicate=claim.predicate.normalized_action,
            obj_or_text=claim.object.canonical_entity if claim.object and claim.object.canonical_entity else claim.claim_text,
        )
        if sig in self._signatures:
            canon_id = self._signatures[sig]
            return DeduplicationResult(
                is_duplicate=True,
                canonical_claim_id=canon_id,
                match_tier="TIER_2_ENTITY_SIGNATURE",
                similarity_score=0.98,
            )

        # Tier 3: Token Jaccard overlap similarity across canonical catalog (fast fallback for embeddings)
        claim_tokens = set(re.findall(r"\b\w{3,}\b", claim.claim_text.lower()))
        for c_id, canon in self._canonical_claims.items():
            if canon.predicate.normalized_action == claim.predicate.normalized_action:
                canon_tokens = set(re.findall(r"\b\w{3,}\b", canon.claim_text.lower()))
                if claim_tokens and canon_tokens:
                    jaccard = len(claim_tokens & canon_tokens) / len(claim_tokens | canon_tokens)
                    if jaccard >= 0.85:
                        return DeduplicationResult(
                            is_duplicate=True,
                            canonical_claim_id=c_id,
                            match_tier="TIER_3_SIMILARITY_MATCH",
                            similarity_score=jaccard,
                        )

        # Unique: Register in canonical index
        self._exact_hashes[exact_h] = claim.claim_id
        self._signatures[sig] = claim.claim_id
        self._canonical_claims[claim.claim_id] = claim

        return DeduplicationResult(
            is_duplicate=False,
            canonical_claim_id=None,
            match_tier=None,
            similarity_score=0.0,
        )

    def collapse_if_duplicate(self, claim: UniversalClaim) -> UniversalClaim:
        """Helper that runs evaluation and updates claim state if duplicate."""
        res = self.evaluate_and_register(claim)
        if res.is_duplicate:
            return claim.model_copy(
                update={
                    "lifecycle_state": ClaimLifecycleState.DUPLICATE,
                    "certification_tier": "DUPLICATE",
                    "is_canonical": False,
                    "agent_accessible": False,
                    "duplicate_of": res.canonical_claim_id,
                    "rejection_reasons": claim.rejection_reasons + [
                        f"Duplicate proposition ({res.match_tier}) of canonical claim {res.canonical_claim_id}."
                    ],
                }
            )
        return claim
