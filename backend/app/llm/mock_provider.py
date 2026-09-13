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

        # Check for structural / document governance headers
        header_patterns = r"\b(?:document\s*id|version\s*:\s*\d+|authority\s*:\s*\d+|classification\s*:|synthetic\s*enterprise\s*dataset|bilingual\s*policy\s*style|section\s*purpose\s*:|page\s*\d+)\b"
        is_header_a = bool(re.search(header_patterns, a_lower)) and not any(w in a_lower for w in ["must not", "prohibited", "forbidden", "cannot"])
        is_header_b = bool(re.search(header_patterns, b_lower)) and not any(w in b_lower for w in ["must not", "prohibited", "forbidden", "cannot"])

        # Strip technical protocol standards, metadata tags, and page numbers from numeric checks
        meta_strip = r"\b(?:aes[-_]?\d+|tls\s*\d+(?:\.\d+)?|sha[-_]?\d+|oauth\s*\d+(?:\.\d+)?|iso\s*\d+|soc\s*\d+|http[s]?\s*/?\s*\d+(?:\.\d+)?|version\s*[:=]?\s*\d+(?:\.\d+)?|authority\s*[:=]?\s*\d+|chapter\s*[:=]?\s*\d+|page\s*[:=]?\s*\d+|rf-\d+-\d+|ssfa-\d+|control\s*rule\s*[:=]?\s*\d+(?:\.\d+)*)\b"
        clean_a = re.sub(meta_strip, "", a_lower)
        clean_b = re.sub(meta_strip, "", b_lower)

        # Check for numeric metrics in both claims
        nums_a = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", clean_a))
        nums_b = set(re.findall(r"\b\d+(?:[.,]\d+)?\b", clean_b))

        # If claims are identical after stripping metadata, they cannot contradict
        if " ".join(clean_a.split()) == " ".join(clean_b.split()):
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="compatible",
                severity="low",
                confidence=0.95,
                reasoning="Claims have identical content and are fully consistent.",
            )

        # Check for complementary segregation-of-duties or self-approval patterns
        is_segregation_a = "own transaction" in a_lower or "segregation of duties" in a_lower or "self-approv" in a_lower
        is_segregation_b = "own transaction" in b_lower or "segregation of duties" in b_lower or "self-approv" in b_lower
        is_complementary_approval = (is_segregation_a or is_segregation_b) and ("approval" in a_lower or "approv" in a_lower) and ("approval" in b_lower or "approv" in b_lower)

        # Opposing directive pairs
        direct_opposing_pairs = [
            ("allow", "prohibit"),
            ("allowed", "prohibited"),
            ("permitted", "forbidden"),
            ("required", "optional"),
            ("mandatory", "voluntary"),
            ("enabled", "disabled"),
            ("on-site", "remote"),
            ("onsite", "remote"),
        ]

        has_direct_opposing = any(
            (p[0] in a_lower and p[1] in b_lower) or (p[1] in a_lower and p[0] in b_lower)
            for p in direct_opposing_pairs
        )

        # Modal verbs (must vs must not, can vs cannot) require matching predicate action verb
        has_modal_opposing = False
        if not is_complementary_approval:
            # Check 'must' vs 'must not'
            if ("must not" in a_lower and re.search(r"\bmust\s+(?!not\b)(\w+)", b_lower)) or \
               ("must not" in b_lower and re.search(r"\bmust\s+(?!not\b)(\w+)", a_lower)):
                verb_must = re.findall(r"\bmust\s+(?!not\b)([a-z]{3,})", a_lower if "must not" in b_lower else b_lower)
                verb_must_not = re.findall(r"\bmust\s+not\s+([a-z]{3,})", b_lower if "must not" in b_lower else a_lower)
                if verb_must and verb_must_not and set(verb_must).intersection(set(verb_must_not)):
                    has_modal_opposing = True

            # Check 'can' vs 'cannot'
            elif ("cannot" in a_lower and re.search(r"\bcan\s+(\w+)", b_lower)) or \
                 ("cannot" in b_lower and re.search(r"\bcan\s+(\w+)", a_lower)):
                verb_can = re.findall(r"\bcan\s+([a-z]{3,})", a_lower if "cannot" in b_lower else b_lower)
                verb_cannot = re.findall(r"\bcannot\s+([a-z]{3,})", b_lower if "cannot" in b_lower else a_lower)
                if verb_can and verb_cannot and set(verb_can).intersection(set(verb_cannot)):
                    has_modal_opposing = True

        has_opposing_terms = has_direct_opposing or has_modal_opposing

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

        # If either claim is pure document structure/metadata, it does not contradict operational rules
        if is_header_a or is_header_b:
            return ContradictionResult(
                is_contradiction=False,
                conflict_type="compatible",
                severity="low",
                confidence=0.88,
                reasoning="Document structure, metadata header, and operational content are compatible.",
            )

        # Domain metric units & policy constraint keywords
        metric_keywords = {
            "day", "week", "month", "year", "hour", "minute", "leave", "allowance",
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

        # Extract semantic units
        curr_a = set(re.findall(r"\$[\d,]+(?:\.\d+)?|\b\d+(?:[.,]\d+)?\s*(?:dollars?|usd|inr|rupees?|eur|euros?)\b", clean_a))
        curr_b = set(re.findall(r"\$[\d,]+(?:\.\d+)?|\b\d+(?:[.,]\d+)?\s*(?:dollars?|usd|inr|rupees?|eur|euros?)\b", clean_b))
        
        dur_a = set(re.findall(r"\b\d+[-\s]*(?:days?|weeks?|months?|years?|hours?|mins?|minutes?)\b", clean_a))
        dur_b = set(re.findall(r"\b\d+[-\s]*(?:days?|weeks?|months?|years?|hours?|mins?|minutes?)\b", clean_b))

        pct_a = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:\%|percent)\b", clean_a))
        pct_b = set(re.findall(r"\b\d+(?:\.\d+)?\s*(?:\%|percent)\b", clean_b))

        # Semantic unit mismatch check
        has_unit_conflict = (
            (bool(curr_a) and bool(curr_b) and curr_a != curr_b) or
            (bool(dur_a) and bool(dur_b) and dur_a != dur_b) or
            (bool(pct_a) and bool(pct_b) and pct_a != pct_b)
        )

        is_numerical_conflict = (
            (has_unit_conflict and len(meaningful_common_words) >= 1) or
            (
                bool(nums_a) and bool(nums_b) and nums_a != nums_b and (
                    (len(meaningful_common_words) >= 2 and (shared_metrics or has_constraint_context)) or
                    (len(meaningful_common_words) >= 1 and shared_metrics and has_constraint_context)
                )
            )
        )

        if is_numerical_conflict:
            context_snippet = ", ".join(list(meaningful_common_words)[:3])
            return ContradictionResult(
                is_contradiction=True,
                conflict_type="numerical_discrepancy",
                severity="high",
                confidence=0.92,
                reasoning=f"Claims share subject context ({context_snippet}) but specify conflicting numerical thresholds: {list(nums_a)[:2]} vs {list(nums_b)[:2]}.",
            )

        return ContradictionResult(
            is_contradiction=False,
            conflict_type="compatible",
            severity="low",
            confidence=0.85,
            reasoning="Claims do not contradict or apply to different non-overlapping domains.",
        )
