"""
Layer 4: Specialized Structured Data Parser.
Processes relational databases (PostgreSQL, MySQL), NoSQL stores (MongoDB BSON), JSON schemas, and CSVs.
Preserves table relationships, column schemas, primary key coordinates, and nested JSON paths.
"""

from __future__ import annotations

import json
import logging
from typing import Any, List, Union

from app.db.enums import SourceFamily
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit

logger = logging.getLogger(__name__)


def _flatten_json_paths(data: Any, prefix: str = "") -> dict[str, Any]:
    """Recursively flattens nested dicts and lists into dot-notation paths."""
    items: dict[str, Any] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, (dict, list)) and v:
                items.update(_flatten_json_paths(v, new_key))
            else:
                items[new_key] = v
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            new_key = f"{prefix}[{idx}]"
            if isinstance(item, (dict, list)) and item:
                items.update(_flatten_json_paths(item, new_key))
            else:
                items[new_key] = item
    else:
        items[prefix] = data
    return items


class StructuredDataParser:
    """Specialized parser for structured relational records, schemas, and BSON/JSON documents."""

    @classmethod
    async def parse(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        units: List[ParsedEvidenceUnit] = []
        fmt = (envelope.native_format or "").lower().strip()
        payload = envelope.raw_payload

        # Extract contextual identifiers
        loc = dict(envelope.locator_metadata or {})
        db_name = loc.get("database") or "default_db"
        container_name = loc.get("table") or loc.get("collection") or envelope.asset_id.split("/")[-1]
        seq_idx = 0

        # Case 1: Schema Definition (SQL Schema DDL or JSON Schema)
        if fmt in ("sql_schema", "json_schema") or "schema" in fmt:
            units = cls._parse_schema(envelope, payload, db_name, container_name)

        # Case 2: Individual JSON/BSON Document
        elif isinstance(payload, dict):
            units = cls._parse_single_dict(envelope, payload, db_name, container_name)

        # Case 3: List of Records / Table Rows
        elif isinstance(payload, list):
            units = cls._parse_record_list(envelope, payload, db_name, container_name)

        # Case 4: Text representation of JSON / CSV
        elif isinstance(payload, str):
            try:
                parsed_json = json.loads(payload)
                if isinstance(parsed_json, dict):
                    units = cls._parse_single_dict(envelope, parsed_json, db_name, container_name)
                elif isinstance(parsed_json, list):
                    units = cls._parse_record_list(envelope, parsed_json, db_name, container_name)
            except Exception:
                # Fallback to plain line records
                lines = [l.strip() for l in payload.splitlines() if l.strip()]
                for idx, line in enumerate(lines):
                    u = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        block_type="structured_record",
                        content_text=line,
                        structured_data={"raw_line": line},
                        locator={"line_index": idx + 1, **loc},
                        hierarchical_context=[db_name, container_name],
                        sequence_index=idx,
                    )
                    units.append(u)

        quality_metrics = {
            "parsed_units": len(units),
            "database": db_name,
            "container": container_name,
            "native_format": fmt,
            "fields_indexed": sum(len(u.structured_data.get("flattened_fields", {})) for u in units),
        }

        return ParsedEvidenceResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.STRUCTURED,
            parser_name="StructuredDataParser",
            units=units,
            completeness_score=1.0,
            quality_metrics=quality_metrics,
        )

    @classmethod
    def _parse_schema(
        cls,
        envelope: CanonicalSourceEnvelope,
        payload: Any,
        db_name: str,
        container_name: str,
    ) -> List[ParsedEvidenceUnit]:
        units: List[ParsedEvidenceUnit] = []
        columns = []

        if isinstance(payload, dict):
            columns = payload.get("columns", []) or payload.get("fields", [])
        elif isinstance(payload, list):
            columns = payload

        # Full Schema Summary Unit
        schema_text = f"Database `{db_name}` > Container `{container_name}` Schema Definition"
        if isinstance(payload, dict):
            summary_parts = [f"Database: {db_name}", f"Container: {container_name}"]
            for k, v in payload.items():
                if k not in ("columns", "fields") and isinstance(v, (str, int, bool)):
                    summary_parts.append(f"{k}: {v}")
            schema_text += " (" + ", ".join(summary_parts) + ")"

        units.append(
            ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                block_type="schema_definition",
                content_text=schema_text,
                structured_data={"raw_schema": payload, "database": db_name, "container": container_name},
                locator={"database": db_name, "container": container_name, **envelope.locator_metadata},
                hierarchical_context=[db_name, container_name, "Schema"],
                sequence_index=0,
            )
        )

        # Individual Column / Field Units
        for idx, col in enumerate(columns):
            if isinstance(col, dict):
                col_name = col.get("column_name") or col.get("name") or col.get("field") or f"field_{idx+1}"
                col_type = col.get("data_type") or col.get("type") or "unknown"
                is_nullable = col.get("is_nullable", True)
                default_val = col.get("column_default") or col.get("default")
                
                col_text = f"Field `{col_name}`: type {col_type}, nullable={is_nullable}"
                if default_val is not None:
                    col_text += f", default={default_val}"

                u = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    block_type="column_definition",
                    content_text=col_text,
                    structured_data={
                        "column_name": col_name,
                        "data_type": col_type,
                        "is_nullable": is_nullable,
                        "default": default_val,
                    },
                    locator={
                        "database": db_name,
                        "container": container_name,
                        "column": col_name,
                        **envelope.locator_metadata,
                    },
                    hierarchical_context=[db_name, container_name, col_name],
                    sequence_index=idx + 1,
                )
                units.append(u)

        return units

    @classmethod
    def _parse_single_dict(
        cls,
        envelope: CanonicalSourceEnvelope,
        doc: dict[str, Any],
        db_name: str,
        container_name: str,
    ) -> List[ParsedEvidenceUnit]:
        units: List[ParsedEvidenceUnit] = []
        pk_val = str(doc.get("_id") or doc.get("id") or doc.get("pk") or envelope.asset_id.split("/")[-1])
        
        flattened = _flatten_json_paths(doc)
        
        # Summary description of record
        field_strs = [f"{k}: {v}" for k, v in list(flattened.items())[:10]]
        content_text = f"Record in `{db_name}.{container_name}` (ID: {pk_val}): " + ", ".join(field_strs)
        if len(flattened) > 10:
            content_text += f" ... (+{len(flattened)-10} more fields)"

        unit = ParsedEvidenceUnit.create(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            block_type="database_record",
            content_text=content_text,
            structured_data={
                "record_id": pk_val,
                "raw_record": doc,
                "flattened_fields": flattened,
                "database": db_name,
                "container": container_name,
            },
            locator={
                "database": db_name,
                "container": container_name,
                "record_id": pk_val,
                **envelope.locator_metadata,
            },
            hierarchical_context=[db_name, container_name, f"Record#{pk_val}"],
            sequence_index=0,
        )
        units.append(unit)
        return units

    @classmethod
    def _parse_record_list(
        cls,
        envelope: CanonicalSourceEnvelope,
        records: list[Any],
        db_name: str,
        container_name: str,
    ) -> List[ParsedEvidenceUnit]:
        units: List[ParsedEvidenceUnit] = []
        for idx, rec in enumerate(records):
            if isinstance(rec, dict):
                sub_units = cls._parse_single_dict(envelope, rec, db_name, container_name)
                for su in sub_units:
                    su.sequence_index = idx
                    units.append(su)
            else:
                u = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    block_type="record_row",
                    content_text=str(rec),
                    structured_data={"row_value": rec},
                    locator={"row_index": idx, "database": db_name, "container": container_name},
                    hierarchical_context=[db_name, container_name, f"Row#{idx}"],
                    sequence_index=idx,
                )
                units.append(u)
        return units
