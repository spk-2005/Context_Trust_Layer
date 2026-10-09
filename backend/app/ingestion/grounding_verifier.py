import hashlib
import re
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from app.llm.schemas import ExtractedClaim


class VerificationStatus(str, Enum):
    VERIFIED = "VERIFIED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    NEEDS_REVIEW = "NEEDS_REVIEW"


CLAIM_SIGNALS = [
    "must", "shall", "required", "may", "cannot", "must not", "prohibited",
    "within", "days", "hours", "weeks", "months", "years", "%", "$", "eur", "usd", "inr",
    "retain", "encrypt", "approve", "access", "delete", "limit", "maximum",
    "minimum", "at least", "policy", "mandate", "bar", "forbid", "sla", "tier",
    "exception", "window", "penalty", "dispute", "entitled", "standard",
    "is defined", "means", "refers to", "consists of", "responsible", "compliance"
]


class ClaimVerificationResult(BaseModel):
    is_valid: bool = True
    status: VerificationStatus = VerificationStatus.VERIFIED
    rejection_reason: Optional[str] = None
    start_offset: int = 0
    end_offset: int = 0
    evidence_hash: str = ""
    verified_evidence_text: str = ""
    verified_modality: str = "MUST"
    verified_confidence: float = 0.95
    numeric_grounded: bool = True
    condition_grounded: bool = True
    warnings: List[str] = Field(default_factory=list)


class GroundingVerifier:
    """Deterministic Grounding & Evidence Verification Service.
    
    1. The source document is always the ground-truth authority.
    2. Candidate claims from LLM are validated against verbatim source blocks.
    3. Offsets, hashes, negation, and numerical bounds are computed deterministically.
    """

    @classmethod
    def needs_claim_extraction(cls, text: str) -> bool:
        """Deterministic prefilter to skip empty or non-assertive noise sections without LLM calls."""
        if not text or len(text.strip()) < 15:
            return False
        lower = text.lower()
        return any(signal in lower for signal in CLAIM_SIGNALS) or bool(re.search(r"\d+", text))

    @classmethod
    def verify_and_ground_claim(
        cls,
        claim: ExtractedClaim,
        source_text: str,
        section_start_offset: int = 0,
        require_numeric_grounding: bool = True,
    ) -> ClaimVerificationResult:
        evidence = (claim.evidence_text_span or claim.claim_text or "").strip()
        warnings: List[str] = []

        if not evidence:
            return ClaimVerificationResult(
                is_valid=False,
                status=VerificationStatus.UNSUPPORTED,
                rejection_reason="Claim has no supporting evidence text.",
                warnings=["Missing evidence text"],
            )

        # 1. Exact Verbatim Substring Matching
        matched_span = ""
        start_idx = source_text.find(evidence)
        if start_idx != -1:
            matched_span = evidence
            abs_start = section_start_offset + start_idx
            abs_end = abs_start + len(evidence)
        else:
            # 1b. Normalized Whitespace Substring Search
            norm_source = " ".join(source_text.split())
            norm_evidence = " ".join(evidence.split())
            norm_idx = norm_source.find(norm_evidence)

            if norm_idx != -1:
                tokens = evidence.split()
                if tokens:
                    first_tok = tokens[0]
                    last_tok = tokens[-1]
                    first_pos = source_text.find(first_tok)
                    last_pos = source_text.find(last_tok, first_pos if first_pos != -1 else 0)
                    if first_pos != -1 and last_pos != -1 and last_pos >= first_pos:
                        matched_span = source_text[first_pos : last_pos + len(last_tok)]
                        abs_start = section_start_offset + first_pos
                        abs_end = section_start_offset + first_pos + len(matched_span)
                    else:
                        matched_span = evidence
                        abs_start = section_start_offset
                        abs_end = section_start_offset + len(evidence)
                else:
                    matched_span = evidence
                    abs_start = section_start_offset
                    abs_end = section_start_offset + len(evidence)
            else:
                # 1c. Clause Token Fallback check
                words = [w.lower() for w in re.findall(r"\w+", evidence) if len(w) > 3]
                source_words = set(re.findall(r"\w+", source_text.lower()))
                overlap = sum(1 for w in words if w in source_words) / max(1, len(words))

                if overlap < 0.65:
                    return ClaimVerificationResult(
                        is_valid=False,
                        status=VerificationStatus.UNSUPPORTED,
                        rejection_reason=f"Evidence text '{evidence[:60]}...' was not found in source section.",
                        warnings=["Low token overlap with source document"],
                    )
                else:
                    matched_span = evidence
                    abs_start = section_start_offset
                    abs_end = section_start_offset + len(evidence)
                    warnings.append("Evidence verified via fuzzy clause matching; exact substring not found.")

        # 2. SHA-256 Cryptographic Evidence Hash
        evidence_hash = hashlib.sha256(matched_span.encode("utf-8")).hexdigest()

        # 3. Numeric Integrity Check
        numeric_grounded = True
        if claim.numeric_value is not None:
            num_val = claim.numeric_value
            int_str = str(int(num_val)) if num_val.is_integer() else str(num_val)
            float_str = str(num_val)
            search_pool = f"{matched_span} {source_text}"

            if int_str not in search_pool and float_str not in search_pool:
                numeric_grounded = False
                warnings.append(f"Numeric value {num_val} was not directly found in evidence text.")
                if require_numeric_grounding:
                    claim.numeric_value = None
                    claim.numeric_unit = None

        # 4. Modality & Negation Alignment
        source_lower = matched_span.lower()
        modality = (claim.modality or "MUST").upper()

        if any(w in source_lower for w in ["must not", "cannot", "prohibited", "forbidden", "shall not", "barred"]):
            modality = "CANNOT"
        elif any(w in source_lower for w in ["must", "shall", "mandatory", "required", "obligated", "enforce"]):
            modality = "MUST"
        elif any(w in source_lower for w in ["may", "permitted", "allowed", "can", "authorized"]):
            modality = "CAN"
        elif any(w in source_lower for w in ["should", "recommended", "advised"]):
            modality = "SHOULD"
        elif any(w in source_lower for w in ["is", "are", "refers to", "defined as", "consists of"]):
            modality = "IS"

        # 5. Condition & Exception check
        condition_grounded = True
        cond_val = getattr(claim, "conditions_or_exceptions", None)
        if cond_val:
            cond_lower = str(cond_val).lower()
            cond_tokens = [w for w in re.findall(r"\w+", cond_lower) if len(w) > 3]
            if cond_tokens:
                source_all_lower = source_text.lower()
                c_overlap = sum(1 for w in cond_tokens if w in source_all_lower) / len(cond_tokens)
                if c_overlap < 0.5:
                    condition_grounded = False
                    warnings.append("Condition/exception clause was partially unsupported in source text.")

        # 6. Status & Confidence Determination
        base_confidence = float(claim.confidence) if claim.confidence else 0.95
        if not numeric_grounded or not condition_grounded:
            base_confidence = max(0.6, base_confidence - 0.2)
            status = VerificationStatus.PARTIALLY_SUPPORTED
        else:
            status = VerificationStatus.VERIFIED

        return ClaimVerificationResult(
            is_valid=True,
            status=status,
            start_offset=abs_start,
            end_offset=abs_end,
            evidence_hash=evidence_hash,
            verified_evidence_text=matched_span,
            verified_modality=modality,
            verified_confidence=min(1.0, max(0.0, base_confidence)),
            numeric_grounded=numeric_grounded,
            condition_grounded=condition_grounded,
            warnings=warnings,
        )
