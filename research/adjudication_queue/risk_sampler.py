"""
Risk-Based Claim Sampler for Sprint AD-7 Certification.
Partitions provisional claims into risk strata to allocate human review capacity
where errors are most consequential, per enterprise governance requirements.
"""

from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any, Dict, List, Tuple


class RiskTier:
    CRITICAL_100 = "CRITICAL_100"  # 100% review: rescued, normalized/long subject, low trust, conflict
    HIGH_50 = "HIGH_50"            # 50% review: conditional/exceptions, regulatory documents
    STANDARD_20 = "STANDARD_20"    # 20% review: high-confidence simple commercial S-P-O claims


class RiskBasedSampler:
    """Classifies claims into risk profiles and samples according to policy requirements."""

    REGULATORY_DOCS = {
        "DOC-051", "DOC-052", "DOC-053", "DOC-054", "DOC-055",
        "DOC-056", "DOC-069", "DOC-070", "DOC-071"
    }

    @classmethod
    def classify_claim_risk(cls, claim: Dict[str, Any], is_rescued: bool = False) -> Tuple[str, str]:
        """Returns (risk_tier, risk_rationale)."""
        doc_id = claim.get("document_id", "")
        subj = (claim.get("subject") or "").strip()
        obj = str(claim.get("object") or "").strip()
        trust = claim.get("trust_score", 1.0)
        
        # 1. Rescued claims or repaired extractor claims -> 100% review
        if is_rescued or "rescued" in claim.get("claim_id", ""):
            return RiskTier.CRITICAL_100, "Repaired / rescued regulatory entity clause (100% review mandatory)"

        # 2. Long or normalized subjects -> 100% review
        if len(subj.split()) > 4 or any(actor in subj.lower() for actor in ("covered entities", "business associates", "healthcare", "either party", "each party")):
            return RiskTier.CRITICAL_100, "Complex / normalized legal actor subject (100% review mandatory)"

        # 3. Trust score below high confidence threshold (< 0.95) -> 100% review
        if trust < 0.95:
            return RiskTier.CRITICAL_100, f"Borderline trust score ({trust:.1%}) below 95% threshold (100% review mandatory)"

        # 4. Conditions or exceptions -> 50% review
        cond_terms = ("if ", "unless ", "except ", "subject to", "provided that", "in the event", "where ")
        if any(term in obj.lower() for term in cond_terms) or claim.get("conditions"):
            return RiskTier.HIGH_50, "Conditional or exception-bearing normative rule (50% sample required)"

        # 5. Regulatory documents -> 50% review
        if doc_id in cls.REGULATORY_DOCS:
            return RiskTier.HIGH_50, "Regulatory compliance document (50% sample required)"

        # 6. High-confidence standard S-P-O -> 20% review
        return RiskTier.STANDARD_20, "High-confidence standard commercial S-P-O claim (20% stratified sample)"

    @classmethod
    def build_risk_stratified_queue(
        cls,
        staged_claims_path: Path,
        rescued_claims_path: Path,
        seed: int = 42,
    ) -> Dict[str, Any]:
        random.seed(seed)
        staged_claims = json.loads(staged_claims_path.read_text(encoding="utf-8"))
        rescued_claims = json.loads(rescued_claims_path.read_text(encoding="utf-8")) if rescued_claims_path.exists() else []

        critical_pool: List[Dict[str, Any]] = []
        high_pool: List[Dict[str, Any]] = []
        standard_pool: List[Dict[str, Any]] = []

        # Process rescued claims (always critical)
        for r in rescued_claims:
            r_copy = dict(r)
            r_copy["risk_tier"] = RiskTier.CRITICAL_100
            r_copy["risk_rationale"] = "Repaired / rescued regulatory entity clause (100% review mandatory)"
            critical_pool.append(r_copy)

        # Process staged provisional claims
        for c in staged_claims:
            c_copy = dict(c)
            tier, rationale = cls.classify_claim_risk(c_copy)
            c_copy["risk_tier"] = tier
            c_copy["risk_rationale"] = rationale
            if tier == RiskTier.CRITICAL_100:
                critical_pool.append(c_copy)
            elif tier == RiskTier.HIGH_50:
                high_pool.append(c_copy)
            else:
                standard_pool.append(c_copy)

        # Apply sampling rates
        # 100% of Critical
        sampled_critical = list(critical_pool)
        
        # 50% of High
        high_sample_size = max(1, int(len(high_pool) * 0.50))
        sampled_high = random.sample(high_pool, high_sample_size) if high_pool else []

        # 20% of Standard
        standard_sample_size = max(1, int(len(standard_pool) * 0.20))
        sampled_standard = random.sample(standard_pool, standard_sample_size) if standard_pool else []

        total_sampled = sampled_critical + sampled_high + sampled_standard

        return {
            "version": "AD-7_v1",
            "total_provisional_pool": len(staged_claims) + len(rescued_claims),
            "pool_distribution": {
                "critical_100_count": len(critical_pool),
                "high_50_count": len(high_pool),
                "standard_20_count": len(standard_pool),
            },
            "sample_counts": {
                "critical_sampled": len(sampled_critical),
                "high_sampled": len(sampled_high),
                "standard_sampled": len(sampled_standard),
                "total_queue_size": len(total_sampled),
            },
            "sampling_coverage_rate": round(len(total_sampled) / max(len(staged_claims) + len(rescued_claims), 1), 4),
            "sampled_claims": total_sampled,
        }
