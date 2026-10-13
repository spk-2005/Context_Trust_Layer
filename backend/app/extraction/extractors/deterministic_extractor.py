"""
Layer 5: Deterministic Schema-Based Extractor.
Extracts atomic claims directly from structured database rows, BSON records, schemas, and table matrices.
Provides 100% deterministic, zero-hallucination, sub-millisecond extraction without consuming LLM tokens.
"""

from __future__ import annotations

import logging
from typing import Any, List

from app.extraction.models import CandidateClaim, ExtractionStrategyType, TableGridBinding
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit

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
            is_ambiguous = s_data.get("is_ambiguous", False)
            ambiguity_reason = s_data.get("ambiguity_reason")

            if cols:
                col_keys = list(cols.keys())
                col_keys_lower = [str(k).lower().strip() for k in col_keys]

                from app.normalization.normalizer import DocumentNormalizer

                # Safety check: skip metadata & navigation tables if they reached here
                if (any("ver" in k or "revision" in k for k in col_keys_lower) and any("date" in k or "description" in k for k in col_keys_lower)):
                    return claims
                if (any("section" in k for k in col_keys_lower) and any("title" in k for k in col_keys_lower)):
                    return claims
                if (any("role" in k or "sign" in k for k in col_keys_lower) and any("name" in k or "designation" in k for k in col_keys_lower)):
                    return claims
                if DocumentNormalizer.is_table_of_contents_block(unit.content_text) or any("table of contents" in str(ctx).lower() for ctx in unit.hierarchical_context):
                    return claims
                if s_data.get("table_type") in ("table_of_contents", "revision_history", "approver_signoff"):
                    return claims

                from app.extraction.deontic_classifier import DeonticClassifier

                # Separate scoping/identifier keys from rule/value keys
                scope_keywords = ("level", "grade", "group", "role", "tier", "department", "category", "scope")
                scope_keys = [k for k in col_keys if any(sk in k.lower() for sk in scope_keywords)]
                
                # If no explicit scope keyword, use the first column as primary key
                if not scope_keys:
                    scope_keys = [col_keys[0]]

                # Build scope dictionary and combined subject
                scope_dict = {k: cols[k] for k in scope_keys}
                rule_keys = [k for k in col_keys if k not in scope_keys]
                # If all columns were considered scope keys, fall back to last column as rule
                if not rule_keys and len(col_keys) > 1:
                    rule_keys = [col_keys[-1]]
                    scope_keys = col_keys[:-1]
                    scope_dict = {k: cols[k] for k in scope_keys}

                import re
                for k in rule_keys:
                    v = cols[k]
                    val_str = str(v).strip()
                    clean_val = DeonticClassifier.strip_markdown(val_str)
                    if not clean_val:
                        continue

                    # Extract soft qualifiers (e.g. 'up to', 'typical', 'maximum', 'at manager discretion')
                    qualifiers: List[str] = []
                    val_lower = clean_val.lower()
                    if re.search(r"\bup\s+to\b", val_lower):
                        qualifiers.append("up_to")
                    if re.search(r"\btypical(?:ly)?\b|\busually\b|\bnormally\b", val_lower):
                        qualifiers.append("typical")
                    if re.search(r"\bmaximum\b|\bmax\b", val_lower):
                        qualifiers.append("maximum")
                    if re.search(r"\bminimum\b|\bmin\b", val_lower):
                        qualifiers.append("minimum")
                    if re.search(r"\brecommended\b", val_lower):
                        qualifiers.append("recommended")
                    if re.search(r"\bwithin\b", val_lower):
                        qualifiers.append("within")
                    if re.search(r"\bat\s+(?:manager'?s?|agent|discretion)\b", val_lower):
                        qualifiers.append("discretionary")
                    if re.search(r"\bapprox(?:imately)?\b", val_lower):
                        qualifiers.append("approximate")

                    # Extract scalar number and unit if applicable
                    scalar_val = clean_val
                    unit_val = None
                    num_match = re.search(r"(?:^|[^\d])(\d+(?:\.\d+)?)\s*([a-zA-Z%]+)?(?:$|[^\w])", clean_val)
                    if num_match:
                        try:
                            scalar_val = float(num_match.group(1)) if "." in num_match.group(1) else int(num_match.group(1))
                        except ValueError:
                            scalar_val = num_match.group(1)
                        unit_val = num_match.group(2).lower() if num_match.group(2) else None

                    # Extract condition if column header reflects conditionality
                    conditions = []
                    k_lower = k.lower()
                    if "probation" in k_lower:
                        conditions.append("Probationary status")
                    elif "confirmed" in k_lower:
                        conditions.append("Confirmed status")
                    elif "exemption" in k_lower:
                        conditions.append("Exemption criteria")

                    normalized = DeonticClassifier.normalize_table_policy_claim(
                        scope_dict=scope_dict,
                        rule_key=k,
                        rule_value=val_str,
                        conditions=conditions,
                        qualifiers=qualifiers,
                    )

                    # Build exact grid coordinates for verifiable grounding (NIST AI RMF)
                    grid_key = DeonticClassifier.strip_markdown(str(cols.get(scope_keys[0], "")))
                    grid_coordinates = {
                        "table_type": "policy_matrix",
                        "row_key": grid_key,
                        "row_scope": scope_dict,
                        "col_header": k,
                        "cell_value": clean_val,
                        "unit": unit_val,
                        "qualifiers": qualifiers,
                        "table_start_line": loc.get("table_start_line"),
                        "row_line": loc.get("line_start"),
                    }
                    enhanced_locator = {
                        **loc,
                        "table_grid": grid_coordinates,
                        "grid_label": f"Row '{grid_key}' • Col '{k}' • Cell '{clean_val}'",
                        "heading_path": unit.hierarchical_context,
                        "section_context": unit.hierarchical_context,
                    }

                    table_id_str = str(loc.get("table_id") or f"tbl_{loc.get('table_start_line', 0)}")
                    col_idx = col_keys.index(k) if k in col_keys else 0
                    row_idx = loc.get("line_start", 0)

                    table_binding = TableGridBinding(
                        table_id=table_id_str,
                        row_key=grid_key,
                        column_header=k,
                        cell_value=clean_val,
                        normalized_value=scalar_val,
                        normalized_unit=unit_val,
                        row_index=int(row_idx) if isinstance(row_idx, int) else 0,
                        col_index=int(col_idx),
                        is_merged_cell=is_ambiguous,
                        qualifiers=qualifiers,
                    )

                    c = CandidateClaim.create(
                        envelope_id=unit.envelope_id,
                        unit_id=unit.unit_id,
                        asset_id=unit.asset_id,
                        run_id=getattr(unit, "run_id", None),
                        source_unit_id=unit.unit_id,
                        evidence_id=f"ev:{unit.unit_id}",
                        table_binding=table_binding,
                        claim_text=normalized["claim_text"],
                        subject=normalized["subject"],
                        predicate=normalized["predicate"],
                        object_=normalized["object"],
                        evidence_text_span=f"{' | '.join([f'{sk}: {cols[sk]}' for sk in scope_keys])} | {k}: {v}",
                        value=scalar_val,
                        unit=unit_val,
                        qualifiers=qualifiers,
                        modal_operator=normalized["modal_operator"],
                        modality=normalized["modality"],
                        conditions=normalized.get("conditions", conditions),
                        scope=scope_dict,
                        claim_type="summary_non_canonical" if (any("topic" in ck for ck in col_keys_lower) and any("summary" in ck for ck in col_keys_lower)) else ("definition" if getattr(unit, "content_role", None) == ContentRole.DEFINITION else "policy_rule"),
                        content_role=getattr(unit, "content_role", ContentRole.POLICY_RULE),
                        is_canonical=False if (any("topic" in ck for ck in col_keys_lower) and any("summary" in ck for ck in col_keys_lower)) else getattr(unit, "is_canonical", True),
                        extraction_strategy=ExtractionStrategyType.TABLE_AWARE,
                        locator=enhanced_locator,
                        structured_values={
                            "columns": cols,
                            "scope": scope_dict,
                            "table_grid": grid_coordinates,
                            "section_context": unit.hierarchical_context,
                        },
                        is_ambiguous=is_ambiguous,
                        ambiguity_reason=ambiguity_reason,
                        confidence=0.70 if is_ambiguous else 0.98,
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
