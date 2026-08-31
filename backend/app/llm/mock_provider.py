import hashlib
import math
import re
from typing import Sequence

from app.llm.base import BaseLLMProvider
from app.llm.schemas import (
    ClaimExtractionResult,
    ContradictionResult,
    ExtractedClaim,
)


class MockLLMProvider(BaseLLMProvider):
    """Deterministic Mock LLM Provider for offline development and testing with zero API keys/costs."""

    def __init__(self, embedding_dim: int = 1536):
        self.embedding_dim = embedding_dim

    async def extract_claims(
        self,
        document_title: str,
        section_title: str,
        section_content: str,
    ) -> ClaimExtractionResult:
        claims: list[ExtractedClaim] = []
        if not section_content or not section_content.strip():
            return ClaimExtractionResult(
                claims=[],
                extraction_model="mock-v1",
                extraction_method="mock_rule_extractor",
            )

        # Split into individual sentences or clauses
        raw_sentences = re.split(r"(?<=[.!?])\s+", section_content.strip())

        for sentence in raw_sentences:
            s = sentence.strip()
            if not s or len(s) < 10:
                continue

            # Heuristic S-P-O breakdown
            subject = section_title if section_title and section_title != "General" else document_title
            predicate = "specifies"
            obj = s

            # Pattern matches for common policy / statement structures
            if " receive " in s:
                parts = s.split(" receive ", 1)
                subject, predicate, obj = parts[0].strip(), "receive", parts[1].strip()
            elif " receives " in s:
                parts = s.split(" receives ", 1)
                subject, predicate, obj = parts[0].strip(), "receives", parts[1].strip()
            elif " are granted " in s:
                parts = s.split(" are granted ", 1)
                subject, predicate, obj = parts[0].strip(), "are granted", parts[1].strip()
            elif " is granted " in s:
                parts = s.split(" is granted ", 1)
                subject, predicate, obj = parts[0].strip(), "is granted", parts[1].strip()
            elif " can " in s:
                parts = s.split(" can ", 1)
                subject, predicate, obj = parts[0].strip(), "can", parts[1].strip()
            elif " must " in s:
                parts = s.split(" must ", 1)
                subject, predicate, obj = parts[0].strip(), "must", parts[1].strip()
            elif " is " in s:
                parts = s.split(" is ", 1)
                subject, predicate, obj = parts[0].strip(), "is", parts[1].strip()

            claim = ExtractedClaim(
                claim_text=s,
                subject=subject[:250],
                predicate=predicate[:250],
                object=obj,
                claim_type="policy" if ("policy" in document_title.lower() or "leave" in s.lower() or "allowance" in s.lower()) else "statement",
                confidence=0.95,
                evidence_text_span=s,
            )
            claims.append(claim)

        return ClaimExtractionResult(
            claims=claims,
            extraction_model="mock-rule-extractor-v1",
            extraction_method="mock_rule_extractor",
        )

    async def get_embedding(self, text: str) -> list[float]:
        """Generate a deterministic 1536-dim unit vector based on text token hashing."""
        vector = [0.0] * self.embedding_dim
        words = re.findall(r"\w+", text.lower())
        if not words:
            vector[0] = 1.0
            return vector

        for word in words:
            # Map word hash into dimension indices
            h = int(hashlib.md5(word.encode("utf-8")).hexdigest(), 16)
            idx = h % self.embedding_dim
            vector[idx] += 1.0

        # Normalize to unit length (L2 norm)
        norm = math.sqrt(sum(v * v for v in vector))
        if norm > 0:
            vector = [v / norm for v in vector]

        return vector

    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        return [await self.get_embedding(t) for t in texts]

    async def evaluate_contradiction(
        self,
        claim_a_text: str,
        claim_b_text: str,
    ) -> ContradictionResult:
        """Heuristic contradiction detector between two claims."""
        a_lower = claim_a_text.lower()
        b_lower = claim_b_text.lower()

        # Check for numbers in both claims (e.g. 30 days vs 60 days, $500 vs $600)
        nums_a = re.findall(r"\b\d+(?:\.\d+)?\b", a_lower)
        nums_b = re.findall(r"\b\d+(?:\.\d+)?\b", b_lower)

        # Tokenize words (length >= 3) and strip trailing plural 's'
        words_a = {re.sub(r"s$", "", w) for w in re.findall(r"[a-z]{3,}", a_lower)}
        words_b = {re.sub(r"s$", "", w) for w in re.findall(r"[a-z]{3,}", b_lower)}
        stopwords = {"employee", "all", "the", "and", "for", "with", "have", "are", "per", "can", "may", "will", "this", "that"}
        meaningful_common_words = (words_a.intersection(words_b)) - stopwords
        has_exception_keyword = "exception" in a_lower or "exception" in b_lower

        # Contradiction: Shared context (meaningful keywords) but different numbers or opposing terms
        opposing_pairs = [
            ("allow", "prohibit"),
            ("allowed", "prohibited"),
            ("permitted", "forbidden"),
            ("required", "optional"),
            ("mandatory", "voluntary"),
            ("can", "cannot"),
            ("must", "must not"),
            ("true", "false"),
            ("enabled", "disabled"),
        ]

        has_opposing_terms = any(
            (p[0] in a_lower and p[1] in b_lower) or (p[1] in a_lower and p[0] in b_lower)
            for p in opposing_pairs
        )

        has_number_discrepancy = (
            (len(meaningful_common_words) >= 1 or has_exception_keyword)
            and nums_a and nums_b and nums_a != nums_b
        )

        if has_number_discrepancy:
            context_snippet = ", ".join(list(meaningful_common_words)[:3]) if meaningful_common_words else "numerical context"
            return ContradictionResult(
                is_contradiction=True,
                conflict_type="numerical_discrepancy",
                severity="high",
                confidence=0.92,
                reasoning=f"Claims share context ({context_snippet}) but contain conflicting numerical values: {nums_a} vs {nums_b}.",
            )

        if has_opposing_terms:
            return ContradictionResult(
                is_contradiction=True,
                conflict_type="direct_contradiction",
                severity="high",
                confidence=0.90,
                reasoning="Claims contain mutually opposing directives or constraints.",
            )

        return ContradictionResult(
            is_contradiction=False,
            conflict_type="compatible",
            severity="low",
            confidence=0.85,
            reasoning="No direct contradiction detected.",
        )
