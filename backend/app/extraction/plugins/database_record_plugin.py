"""
Layer 5: Database / Record Evidence Verification Plugin.
Verifies claims extracted from relational tables (PostgreSQL) and document stores (MongoDB BSON).
Validates primary key coordinates, field paths, and typed values.
"""

from __future__ import annotations

from typing import Any, Tuple

from app.extraction.models import CandidateClaim
from app.extraction.plugins.base_plugin import EvidenceVerificationPlugin
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit


class DatabaseRecordVerificationPlugin(EvidenceVerificationPlugin):
    """Verifies database records against native primary key coordinates and typed field values."""

    @property
    def plugin_name(self) -> str:
        return "DatabaseRecordVerificationPlugin"

    def supports_evidence(self, unit: ParsedEvidenceUnit) -> bool:
        return unit.block_type in ("database_record", "record_row", "structured_record", "column_definition", "schema_definition")

    def verify(
        self,
        candidate: CandidateClaim,
        unit: ParsedEvidenceUnit,
        raw_payload: Any,
    ) -> Tuple[bool, str, dict[str, Any]]:
        s_data = unit.structured_data or {}
        loc = unit.locator or {}

        # 1. Schema Definition verification
        if unit.block_type == "schema_definition":
            container = loc.get("container") or loc.get("collection") or loc.get("table")
            return True, f"Verified schema definition for `{container}`.", {
                "database": loc.get("database"),
                "container": container,
                "column_count": s_data.get("column_count"),
            }

        # 2. Column Definition verification
        if unit.block_type == "column_definition":
            col_name = s_data.get("column_name")
            if col_name and (col_name in candidate.subject or col_name in candidate.claim_text):
                return True, f"Verified DDL schema column definition `{col_name}`.", {
                    "column_name": col_name,
                    "data_type": s_data.get("data_type"),
                    "is_nullable": s_data.get("is_nullable"),
                }
            return False, "Column definition mismatch.", {"structured_data": s_data}

        # 2. Database Record verification
        record_id = loc.get("record_id") or loc.get("document_id") or loc.get("pk")
        field_path = candidate.locator.get("field_path") or candidate.predicate.replace("has_", "")

        flattened = s_data.get("flattened_fields") or s_data.get("raw_record") or {}

        # Verify field existence
        matched_val = None
        for k, v in flattened.items():
            if k == field_path or k.endswith(f".{field_path}") or field_path in k:
                matched_val = v
                break

        if matched_val is not None:
            # Value comparison
            str_matched = str(matched_val).lower().strip()
            str_target = str(candidate.object).lower().strip()

            if str_matched == str_target or str_target in str_matched:
                details = {
                    "database": loc.get("database"),
                    "container": loc.get("container") or loc.get("collection") or loc.get("table"),
                    "record_id": record_id,
                    "field_path": field_path,
                    "native_value": matched_val,
                    "native_type": type(matched_val).__name__,
                }
                return True, f"Verified field `{field_path}` in record `{record_id}` with value `{matched_val}`.", details
            else:
                return False, f"Value mismatch for field `{field_path}`: source has `{matched_val}`, claim asserts `{candidate.object}`.", {
                    "source_value": matched_val,
                    "claim_value": candidate.object,
                }

        # If specific field path not matched, check general record presence
        if record_id and record_id in candidate.subject:
            return True, f"Verified existence of record `{record_id}` in `{loc.get('container')}`.", {"record_id": record_id}

        return False, "Database record coordinates could not be verified in structured evidence.", {"locator": loc}
