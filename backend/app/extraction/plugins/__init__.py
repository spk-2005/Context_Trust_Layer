"""
Layer 5 Evidence Verification Plugins Package.
Provides centralized verification plugin registry and selector.
"""

from typing import Any, List, Optional, Tuple

from app.extraction.models import CandidateClaim
from app.extraction.plugins.base_plugin import EvidenceVerificationPlugin
from app.extraction.plugins.database_record_plugin import DatabaseRecordVerificationPlugin
from app.extraction.plugins.text_document_plugin import TextDocumentVerificationPlugin
from app.extraction.plugins.api_json_plugin import ApiJsonVerificationPlugin
from app.extraction.plugins.formula_bi_plugin import FormulaBiVerificationPlugin
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit

__all__ = [
    "EvidenceVerificationPlugin",
    "TextDocumentVerificationPlugin",
    "DatabaseRecordVerificationPlugin",
    "ApiJsonVerificationPlugin",
    "FormulaBiVerificationPlugin",
    "VerificationPluginManager",
]


class VerificationPluginManager:
    """Manages and invokes source-aware verification plugins for candidates."""

    def __init__(self, custom_plugins: Optional[List[EvidenceVerificationPlugin]] = None):
        self.plugins: List[EvidenceVerificationPlugin] = custom_plugins or [
            DatabaseRecordVerificationPlugin(),
            FormulaBiVerificationPlugin(),
            ApiJsonVerificationPlugin(),
            TextDocumentVerificationPlugin(),  # Default fallback for text/clauses
        ]

    def get_plugin_for_unit(self, unit: ParsedEvidenceUnit) -> EvidenceVerificationPlugin:
        for plugin in self.plugins:
            if plugin.supports_evidence(unit):
                return plugin
        return self.plugins[-1]

    def verify_candidate(
        self,
        candidate: CandidateClaim,
        unit: ParsedEvidenceUnit,
        raw_payload: Any,
    ) -> Tuple[bool, str, str, dict[str, Any]]:
        """
        Runs the appropriate verification plugin.
        Returns: (is_verified, plugin_name, reason, details)
        """
        plugin = self.get_plugin_for_unit(unit)
        is_verified, reason, details = plugin.verify(candidate, unit, raw_payload)
        return is_verified, plugin.plugin_name, reason, details
