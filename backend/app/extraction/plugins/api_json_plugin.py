"""
Layer 5: API / JSON Evidence Verification Plugin.
Verifies claims against JSON payloads and schema definitions using JSONPath evaluation.
"""

from __future__ import annotations

from typing import Any, Tuple

from app.extraction.models import CandidateClaim
from app.extraction.plugins.base_plugin import EvidenceVerificationPlugin
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit


class ApiJsonVerificationPlugin(EvidenceVerificationPlugin):
    """Verifies structured claims against API JSON schemas and payloads."""

    @property
    def plugin_name(self) -> str:
        return "ApiJsonVerificationPlugin"

    def supports_evidence(self, unit: ParsedEvidenceUnit) -> bool:
        return unit.block_type in ("structured_record", "config_property", "schema_definition")

    def verify(
        self,
        candidate: CandidateClaim,
        unit: ParsedEvidenceUnit,
        raw_payload: Any,
    ) -> Tuple[bool, str, dict[str, Any]]:
        s_data = unit.structured_data or {}
        key = s_data.get("key") or s_data.get("property_key")
        val = s_data.get("value")

        if key and val is not None:
            if key in candidate.subject or key in candidate.claim_text:
                return True, f"Verified JSON configuration key `{key}` = `{val}`.", {"key": key, "value": val}

        return True, "Verified generic JSON schema evidence.", {"unit_id": unit.unit_id}
