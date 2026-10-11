"""
Layer 5: Base Evidence Verification Plugin.
Defines the contract for source-aware verification plugins.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Tuple

from app.extraction.models import CandidateClaim
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit


class EvidenceVerificationPlugin(ABC):
    """Abstract base class for all source-aware evidence verification plugins."""

    @property
    @abstractmethod
    def plugin_name(self) -> str:
        """Name of the verification plugin."""
        pass

    @abstractmethod
    def supports_evidence(self, unit: ParsedEvidenceUnit) -> bool:
        """Determines if this plugin is capable of verifying the given evidence unit."""
        pass

    @abstractmethod
    def verify(
        self,
        candidate: CandidateClaim,
        unit: ParsedEvidenceUnit,
        raw_payload: Any,
    ) -> Tuple[bool, str, dict[str, Any]]:
        """
        Verifies the claim against the source evidence unit and raw payload.
        Returns:
            - is_verified: bool (True if valid and grounded, False if rejected)
            - reason: str (Human-readable audit explanation)
            - verification_details: dict (Proof coordinates, matching score, character spans)
        """
        pass
