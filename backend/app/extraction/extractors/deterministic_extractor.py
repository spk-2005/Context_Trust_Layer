"""
Layer 5: Deterministic Schema-Based Extractor.
Extracts atomic claims directly from structured database rows, BSON records, schemas, and table matrices.
Provides 100% deterministic, zero-hallucination, sub-millisecond extraction without consuming LLM tokens.
"""

from __future__ import annotations

import logging
from typing import Any, List

from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ParsedEvidenceUnit

logger = logging.getLogger(__name__)


class DeterministicSchemaExtractor:
    """Zero-hallucination extractor for structured and relational data."""

    # Fields that represent high-value enterprise invariants
    HIGH_VALUE_FIELDS = {
        "encryption", "key_rotation_days", "enforce_tls", "tls_version",
        "retention_days", "timeout_minutes", "mfa_required", "status",
        "role", "approval_required", "access_tier", "is_active", "policy_id",
        "correct", "question", "percentage", "score", "timeTaken"
    }

    @classmethod
    def extract_from_unit(cls, unit: ParsedEvidenceUnit) -> List[CandidateClaim]:
        claims: List[CandidateClaim] = []
        b_type = unit.block_type
        s_data = unit.structured_data or {}
        loc = unit.locator or {}

        # 1. Database Record (MongoDB BSON / Postgres Row)
        if b_type in ("database_record", "record_row", "structured_record"):
            container = loc.get("container") or loc.get("collection") or loc.get("table") or "record"
            rec_id = loc.get("record_id") or loc.get("document_id") or loc.get("pk") or "unknown"
            subject = f"{loc.get('database', 'db')}.{container}#{rec_id}"

            fields = s_data.get("flattened_fields") or s_data.get("raw_record") or {}
            
            for field_name, field_val in fields.items():
                if field_name in ("_id", "id", "__v") or field_val is None:
                    continue

                clean_field = field_name.split(".")[-1].split("[")[0].lower()
                # Prioritize high value fields or all non-empty fields
                is_priority = clean_field in cls.HIGH_VALUE_FIELDS or len(fields) <= 12
                if not is_priority:
                    continue

                claim_text = f"`{subject}` defines `{field_name}` as `{field_val}`."
                predicate = f"has_{clean_field}" if not clean_field.startswith("is_") else clean_field
                
                c = CandidateClaim.create(
                    envelope_id=unit.envelope_id,
                    unit_id=unit.unit_id,
                    asset_id=unit.asset_id,
                    claim_text=claim_text,
                    subject=subject,
                    predicate=predicate,
                    object_=str(field_val),
                    evidence_text_span=f"{field_name}: {field_val}",
                    modal_operator="is",
                    claim_type="invariant",
                    extraction_strategy=ExtractionStrategyType.DETERMINISTIC_SCHEMA,
                    locator={**loc, "field_path": field_name},
                    structured_values={field_name: field_val, "container": container, "record_id": rec_id},
                    confidence=1.0,
                )
                claims.append(c)

        # 2. Schema Definition (Collection / Table Level)
        elif b_type == "schema_definition":
            db_name = loc.get("database", "db")
            container = loc.get("container") or loc.get("collection") or loc.get("table", "container")
            subject = f"{db_name}.{container}"
            raw_s = s_data.get("raw_schema") or {}
            col_count = s_data.get("column_count") or len(raw_s.get("columns", [])) or len(raw_s.get("fields", [])) or 1
            claim_text = f"Container `{subject}` enforces schema with {col_count} documented attributes."
            c = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text=claim_text,
                subject=subject,
                predicate="enforces_schema_definition",
                object_=f"{col_count} attributes",
                evidence_text_span=unit.content_text,
                modal_operator="enforces",
                claim_type="schema_invariant",
                extraction_strategy=ExtractionStrategyType.DETERMINISTIC_SCHEMA,
                locator=loc,
                structured_values=s_data,
                confidence=1.0,
            )
            claims.append(c)

        # 3. Schema DDL / Column Definition
        elif b_type == "column_definition":
            col_name = s_data.get("column_name", "column")
            data_type = s_data.get("data_type", "unknown")
            is_nullable = s_data.get("is_nullable", True)
            db_name = loc.get("database", "db")
            table_name = loc.get("container", "table")
            subject = f"{db_name}.{table_name}.{col_name}"

            claim_text = f"Column `{subject}` has type `{data_type}` and is_nullable={is_nullable}."
            c = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text=claim_text,
                subject=subject,
                predicate="has_schema_constraint",
                object_=f"type={data_type}, nullable={is_nullable}",
                evidence_text_span=unit.content_text,
                modal_operator="enforces",
                claim_type="schema_invariant",
                extraction_strategy=ExtractionStrategyType.DETERMINISTIC_SCHEMA,
                locator=loc,
                structured_values=s_data,
                confidence=1.0,
            )
            claims.append(c)

        # 3. Structured Table Matrix Row
        elif b_type == "table_row":
            cols = s_data.get("columns", {})
            if cols:
                # E.g. Role: Developer, Access Tier: Staging, Approval: Team Lead
                primary_key_col = list(cols.keys())[0]
                primary_val = cols[primary_key_col]
                subject = f"{primary_key_col}: {primary_val}"
                
                for k, v in list(cols.items())[1:]:
                    claim_text = f"`{subject}` specifies `{k}` as `{v}`."
                    c = CandidateClaim.create(
                        envelope_id=unit.envelope_id,
                        unit_id=unit.unit_id,
                        asset_id=unit.asset_id,
                        claim_text=claim_text,
                        subject=subject,
                        predicate=f"requires_{k.lower().replace(' ', '_')}",
                        object_=str(v),
                        evidence_text_span=f"{primary_val} | {k}: {v}",
                        modal_operator="requires",
                        claim_type="policy_rule",
                        extraction_strategy=ExtractionStrategyType.DETERMINISTIC_SCHEMA,
                        locator=loc,
                        structured_values={"columns": cols},
                        confidence=0.98,
                    )
                    claims.append(c)

        # 4. BI Metric Rule
        elif b_type == "metric_definition":
            metric_name = s_data.get("name") or loc.get("metric_name") or "metric"
            formula = s_data.get("formula") or s_data.get("calculation") or ""
            subject = f"BI Metric `{metric_name}`"

            c = CandidateClaim.create(
                envelope_id=unit.envelope_id,
                unit_id=unit.unit_id,
                asset_id=unit.asset_id,
                claim_text=f"{subject} is computed as: `{formula}`.",
                subject=subject,
                predicate="is_calculated_as",
                object_=formula,
                evidence_text_span=unit.content_text,
                modal_operator="is",
                claim_type="metric_rule",
                extraction_strategy=ExtractionStrategyType.DETERMINISTIC_SCHEMA,
                locator=loc,
                structured_values=s_data,
                confidence=1.0,
            )
            claims.append(c)

        return claims
