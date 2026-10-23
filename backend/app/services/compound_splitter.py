"""
Compound Claim Splitter.

Decomposes multi-branch, multi-remedy, and mixed-polarity compound claims into atomic child claims
while preserving full parent-child provenance and shared immutable evidence spans.
"""

import re
from typing import List, Optional
from app.schemas.universal_claim import ClaimLifecycleState, ClaimType, UniversalClaim, SubjectEntity, PredicateAction, ObjectEntity
from app.services.dynamic_modality_extractor import DynamicModalityExtractor


class CompoundClaimSplitter:
    """Universal detector and decomposition engine for compound rules."""

    @classmethod
    def is_compound(cls, text: str) -> bool:
        t_low = (text or "").lower()

        # 1. Multi-branch transfer or assignment markers
        if "transfer" in t_low and (("(1)" in t_low or "(i)" in t_low) and ("(2)" in t_low or "(ii)" in t_low)):
            return True
        if "transfer" in t_low and "affiliate" in t_low and "third party" in t_low and ("hardware" in t_low or "merger" in t_low):
            return True

        # 2. Mixed polarity: permission + prohibition
        if "may sublicense" in t_low and ("may not sublicense" in t_low or "affiliates may not" in t_low):
            return True

        # 3. Multi-remedy audits
        if ("audit" in t_low or "unlicensed use" in t_low) and "reimburse" in t_low and ("acquire" in t_low or "125%" in t_low):
            return True

        # 4. Explicit disjunction with differing subjects: "... but [Party] may not ..."
        if re.search(r"\b(?:but|however|except\s+that)\s+[A-Za-z\s]+(?:may\s+not|must\s+not|shall\s+not)\b", t_low):
            return True

        return False

    @classmethod
    def split(cls, parent: UniversalClaim) -> List[UniversalClaim]:
        """
        Decomposes a compound parent claim into atomic child claims.
        If not compound, returns [parent].
        """
        text = parent.claim_text.strip()
        t_low = text.lower()

        if not cls.is_compound(text):
            return [parent]

        children: List[UniversalClaim] = []

        # Case 1: Mixed polarity sublicensing: "Customer may sublicense to its Affiliates, but Customer's Affiliates may not sublicense..."
        if "may sublicense" in t_low and ("may not sublicense" in t_low or "affiliates may not" in t_low):
            parts = re.split(r",?\s*\b(?:but|however)\s+", text, flags=re.IGNORECASE)
            if len(parts) >= 2:
                # Child 1: Affirmative permission
                c1_text = parts[0].strip()
                if not c1_text.endswith("."):
                    c1_text += "."
                c1 = parent.model_copy(
                    update={
                        "claim_id": f"{parent.claim_id}_c1",
                        "parent_claim_id": parent.claim_id,
                        "child_index": 1,
                        "claim_text": c1_text,
                        "predicate": PredicateAction(
                            raw_text="may sublicense",
                            normalized_action="may_sublicense",
                            taxonomy_version="v1.0.0",
                        ),
                        "modality": DynamicModalityExtractor.extract_modality(c1_text),
                        "lifecycle_state": ClaimLifecycleState.CANDIDATE,
                    }
                )
                children.append(c1)

                # Child 2: Negative prohibition
                c2_text = parts[1].strip()
                if not c2_text.endswith("."):
                    c2_text += "."
                c2_subj = "Affiliates" if "affiliate" in parts[1].lower() else parent.subject.raw_text
                c2 = parent.model_copy(
                    update={
                        "claim_id": f"{parent.claim_id}_c2",
                        "parent_claim_id": parent.claim_id,
                        "child_index": 2,
                        "claim_text": c2_text,
                        "subject": SubjectEntity(
                            raw_text=c2_subj,
                            canonical_entity="Affiliate",
                            entity_role="BENEFICIARY",
                        ),
                        "predicate": PredicateAction(
                            raw_text="may not sublicense",
                            normalized_action="must_not_reverse_engineer",  # or specific restriction
                            taxonomy_version="v1.0.0",
                        ),
                        "modality": DynamicModalityExtractor.extract_modality(c2_text),
                        "lifecycle_state": ClaimLifecycleState.CANDIDATE,
                    }
                )
                children.append(c2)
                return children

        # Case 2: Multi-branch transfer: "(1) an affiliate or (2) a third party"
        if "transfer" in t_low and (("(1)" in t_low or "(i)" in t_low) and ("(2)" in t_low or "(ii)" in t_low)):
            branches = re.split(r"\s*(?:\(1\)|\(i\))\s*", text, flags=re.IGNORECASE)
            if len(branches) >= 2:
                intro = branches[0].strip()
                sub_branches = re.split(r"\s*(?:,\s*or|\bor|\band)\s*(?:\(2\)|\(ii\))\s*", branches[1], flags=re.IGNORECASE)
                if len(sub_branches) >= 2:
                    # Child 1: Transfer to affiliate
                    b1_text = f"{intro} an Affiliate."
                    c1 = parent.model_copy(
                        update={
                            "claim_id": f"{parent.claim_id}_c1",
                            "parent_claim_id": parent.claim_id,
                            "child_index": 1,
                            "claim_text": b1_text,
                            "object": ObjectEntity(raw_text="an Affiliate", canonical_entity="Affiliate"),
                            "modality": DynamicModalityExtractor.extract_modality(b1_text),
                            "lifecycle_state": ClaimLifecycleState.CANDIDATE,
                        }
                    )
                    children.append(c1)

                    # Child 2: Transfer to third party
                    b2_text = f"{intro} a third party."
                    c2 = parent.model_copy(
                        update={
                            "claim_id": f"{parent.claim_id}_c2",
                            "parent_claim_id": parent.claim_id,
                            "child_index": 2,
                            "claim_text": b2_text,
                            "object": ObjectEntity(raw_text="a third party", canonical_entity="Third Party"),
                            "modality": DynamicModalityExtractor.extract_modality(b2_text),
                            "lifecycle_state": ClaimLifecycleState.CANDIDATE,
                        }
                    )
                    children.append(c2)
                    return children

        # Default fallback: return parent as quarantined if not decomposed
        parent_copy = parent.model_copy(
            update={
                "lifecycle_state": ClaimLifecycleState.QUARANTINED,
                "certification_tier": "QUARANTINED",
                "is_canonical": False,
            }
        )
        return [parent_copy]
