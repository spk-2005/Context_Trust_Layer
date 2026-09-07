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
        """Context-aware contradiction detector between two claims."""
        a_lower = claim_a_text.lower()
        b_lower = claim_b_text.lower()

        # Comprehensive stopwords + document structural noise
        stopwords = {
            "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
            "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
            "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
            "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
            "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
            "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
            "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
            "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
            "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
            "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
            "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
            "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
            "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
            "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
            "they've", "this", "those", "through", "to", "too", "under", "until", "up",
            "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
            "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
            "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
            "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
            "page", "section", "document", "policy", "requirement", "standard", "rule",
            "item", "clause", "specified", "specifies", "accordance", "following", "general",
            "total", "part", "details", "described", "provides", "including", "also", "per",
            "one", "two", "three", "four", "five", "first", "second", "third", "must", "may"
        }

        # Tokenize meaningful content words (length >= 3)
        words_a = {re.sub(r"s$", "", w) for w in re.findall(r"[a-z]{3,}", a_lower)} - stopwords
        words_b = {re.sub(r"s$", "", w) for w in re.findall(r"[a-z]{3,}", b_lower)} - stopwords
        meaningful_common_words = words_a.intersection(words_b)

        # Strip technical protocol standards so "AES-256", "TLS 1.3", "OAuth 2.0", etc. aren't parsed as conflicting counts
        clean_a = re.sub(r"\b(?:aes[-_]?\d+|tls\s*\d+(?:\.\d+)?|sha[-_]?\d+|oauth\s*\d+(?:\.\d+)?|iso\s*\d+|soc\s*\d+|http[s]?\s*/?\s*\d+(?:\.\d+)?)\b", "", a_lower)
        clean_b = re.sub(r"\b(?:aes[-_]?\d+|tls\s*\d+(?:\.\d+)?|sha[-_]?\d+|oauth\s*\d+(?:\.\d+)?|iso\s*\d+|soc\s*\d+|http[s]?\s*/?\s*\d+(?:\.\d+)?)\b", "", b_lower)

        # Check for numeric metrics in both claims
        nums_a = re.findall(r"\b\d+(?:[.,]\d+)?\b", clean_a)
        nums_b = re.findall(r"\b\d+(?:[.,]\d+)?\b", clean_b)

        # Opposing directive pairs
        opposing_pairs = [
            ("allow", "prohibit"),
            ("allowed", "prohibited"),
            ("permitted", "forbidden"),
            ("required", "optional"),
            ("mandatory", "voluntary"),
            ("can", "cannot"),
            ("must", "must not"),
            ("enabled", "disabled"),
            ("on-site", "remote"),
            ("onsite", "remote"),
        ]

        has_opposing_terms = any(
            (p[0] in a_lower and p[1] in b_lower) or (p[1] in a_lower and p[0] in b_lower)
            for p in opposing_pairs
        )

        # Domain metric units & policy constraint keywords
        metric_keywords = {
            "day", "week", "month", "year", "hour", "minute", "refund", "leave", "allowance",
            "limit", "amount", "threshold", "window", "rate", "sla", "discount",
            "fee", "charge", "price", "cost", "salary", "bonus", "score", "percent"
        }
        constraint_keywords = {
            "window", "exception", "threshold", "limit", "cap", "maximum", "minimum",
            "eligible", "eligibility", "allowed", "permitted", "required", "grant", "granted", "approval", "signoff"
        }

        shared_metrics = meaningful_common_words.intersection(metric_keywords)
        has_constraint_context = (
            any(w in a_lower for w in constraint_keywords) and
            any(w in b_lower for w in constraint_keywords)
        )

        # A valid numerical discrepancy requires:
        # 1. Genuine numbers in both claims (not technical standard names)
        # 2. Shared metric unit (e.g. both discussing days, or both discussing refund/rupees)
        # 3. Both claims expressing a rule/constraint/threshold context
        is_numerical_conflict = (
            bool(nums_a) and bool(nums_b) and nums_a != nums_b and (
                (len(meaningful_common_words) >= 2 and (shared_metrics or has_constraint_context)) or
                (len(meaningful_common_words) >= 1 and shared_metrics and has_constraint_context)
            )
        )

        if is_numerical_conflict:
            context_snippet = ", ".join(list(meaningful_common_words)[:3])
            return ContradictionResult(
                is_contradiction=True,
                conflict_type="numerical_discrepancy",
                severity="high",
                confidence=0.92,
                reasoning=f"Claims share subject context ({context_snippet}) but specify conflicting numerical thresholds: {nums_a} vs {nums_b}.",
            )

        # Opposing directives: Must share at least 1 meaningful subject keyword (e.g., "remote work", "engineering")
        if has_opposing_terms and len(meaningful_common_words) >= 1:
            context_snippet = ", ".join(list(meaningful_common_words)[:3])
            return ContradictionResult(
                is_contradiction=True,
                conflict_type="direct_contradiction",
                severity="high",
                confidence=0.90,
                reasoning=f"Claims share subject ({context_snippet}) but contain mutually opposing rules or constraints.",
            )

        return ContradictionResult(
            is_contradiction=False,
            conflict_type="compatible",
            severity="low",
            confidence=0.85,
            reasoning="Claims do not contradict or apply to different non-overlapping domains.",
        )
