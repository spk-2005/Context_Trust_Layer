"""
Layer 4: Specialized Structured Data Parser.
Processes relational databases (PostgreSQL, MySQL), NoSQL stores (MongoDB BSON),
JSON and JSONL streams, XML hierarchies, CSV/TSV tables, and SQL DDL schemas.
Preserves complete field hierarchies, column positions, source relationships, and typed invariants.
"""

from __future__ import annotations

import csv
import io
import json
import logging
import re
import xml.etree.ElementTree as ET
from typing import Any, List, Optional, Tuple, Union

from app.db.enums import SourceFamily
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceExtractionValidator,
    EvidenceRelationship,
    EvidenceUnit,
    EvidenceValidationResult,
    ExtractionQualityReport,
    ExtractionStatus,
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
    SourceLocator,
    StructuralRelationType,
)

logger = logging.getLogger(__name__)


def _flatten_json_paths(data: Any, prefix: str = "") -> dict[str, Any]:
    """Recursively flattens nested dicts and lists into dot-notation and indexed paths, preserving types."""
    items: dict[str, Any] = {}
    if isinstance(data, dict):
        for k, v in data.items():
            new_key = f"{prefix}.{k}" if prefix else str(k)
            if isinstance(v, dict) and v:
                items.update(_flatten_json_paths(v, new_key))
            elif isinstance(v, list) and v:
                items.update(_flatten_json_paths(v, new_key))
            else:
                items[new_key] = v
    elif isinstance(data, list):
        for idx, item in enumerate(data):
            new_key = f"{prefix}[{idx}]"
            if isinstance(item, dict) and item:
                items.update(_flatten_json_paths(item, new_key))
            elif isinstance(item, list) and item:
                items.update(_flatten_json_paths(item, new_key))
            else:
                items[new_key] = item
    else:
        items[prefix or "$"] = data
    return items


def _parse_sql_ddl_text(sql_text: str) -> list[dict[str, Any]]:
    """Extracts tables, columns, data types, constraints, and defaults from SQL DDL text."""
    tables = []
    table_pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(?:([a-zA-Z0-9_]+)\.)?([a-zA-Z0-9_]+)\s*\((.*?)\);',
        re.DOTALL | re.IGNORECASE,
    )
    for m in table_pattern.finditer(sql_text):
        schema_name = m.group(1) or 'public'
        table_name = m.group(2)
        body = m.group(3)

        entries = []
        paren_depth = 0
        cur = []
        for char in body:
            if char == '(':
                paren_depth += 1
                cur.append(char)
            elif char == ')':
                paren_depth -= 1
                cur.append(char)
            elif char == ',' and paren_depth == 0:
                entries.append(''.join(cur).strip())
                cur = []
            else:
                cur.append(char)
        if cur and ''.join(cur).strip():
            entries.append(''.join(cur).strip())

        columns = []
        constraints = []
        for entry in entries:
            clean_entry = re.sub(r'\s+', ' ', entry).strip()
            if not clean_entry:
                continue

            # Check for table-level constraints
            if re.match(r'^(?:CONSTRAINT\s+[a-zA-Z0-9_]+\s+)?(?:PRIMARY\s+KEY|FOREIGN\s+KEY|CHECK|UNIQUE)\b', clean_entry, re.IGNORECASE):
                c_match = re.match(
                    r'^(?:CONSTRAINT\s+([a-zA-Z0-9_]+)\s+)?(PRIMARY\s+KEY|FOREIGN\s+KEY|CHECK|UNIQUE)\s*(.*)',
                    clean_entry,
                    re.IGNORECASE,
                )
                if c_match:
                    constraints.append({
                        'name': c_match.group(1),
                        'type': c_match.group(2).upper(),
                        'definition': c_match.group(3).strip(),
                    })
                continue

            # Tokenize column entry respecting parens (e.g. DECIMAL(10, 2))
            col_tokens = []
            tok_paren = 0
            cur_tok = []
            for c in clean_entry:
                if c == '(':
                    tok_paren += 1
                    cur_tok.append(c)
                elif c == ')':
                    tok_paren -= 1
                    cur_tok.append(c)
                elif c == ' ' and tok_paren == 0:
                    if cur_tok:
                        col_tokens.append(''.join(cur_tok))
                        cur_tok = []
                else:
                    cur_tok.append(c)
            if cur_tok:
                col_tokens.append(''.join(cur_tok))

            col_name = col_tokens[0].strip('"`[]') if col_tokens else 'unknown'
            col_type = col_tokens[1] if len(col_tokens) > 1 else 'unknown'
            rest = ' '.join(col_tokens[2:]) if len(col_tokens) > 2 else ''

            is_nullable = True
            if re.search(r'\bNOT\s+NULL\b', rest, re.IGNORECASE):
                is_nullable = False

            is_pk = bool(re.search(r'\bPRIMARY\s+KEY\b', rest, re.IGNORECASE))

            default_val = None
            def_match = re.search(r'\bDEFAULT\s+([^,]+?)(?:\s+(?:NOT\s+NULL|NULL|PRIMARY\s+KEY|REFERENCES|CONSTRAINT)|$)', rest, re.IGNORECASE)
            if def_match:
                raw_def = def_match.group(1).strip()
                if raw_def.lower() == 'false':
                    default_val = False
                elif raw_def.lower() == 'true':
                    default_val = True
                elif raw_def.lower() == 'null':
                    default_val = None
                elif raw_def in ('0', '0.0', '0.00'):
                    default_val = 0
                elif raw_def in ("''", '""'):
                    default_val = ''
                else:
                    default_val = raw_def.strip("'\"")

            fk_ref = None
            ref_match = re.search(r'\bREFERENCES\s+([a-zA-Z0-9_.]+)(?:\s*\(([a-zA-Z0-9_]+)\))?', rest, re.IGNORECASE)
            if ref_match:
                fk_ref = {'table': ref_match.group(1), 'column': ref_match.group(2)}

            columns.append({
                'column_name': col_name,
                'data_type': col_type,
                'is_nullable': is_nullable,
                'default': default_val,
                'is_primary_key': is_pk,
                'foreign_key': fk_ref,
            })

        tables.append({
            'schema': schema_name,
            'table': table_name,
            'columns': columns,
            'constraints': constraints,
        })
    return tables


class StructuredDataParser:
    """Specialized parser for structured relational records, schemas, BSON/JSON documents, CSVs, and XML."""

    @classmethod
    async def parse(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        units: List[ParsedEvidenceUnit] = []
        fmt = (envelope.native_format or "").lower().strip()
        payload = envelope.raw_payload

        loc = dict(envelope.locator_metadata or {})
        db_name = loc.get("database") or "default_db"
        container_name = loc.get("table") or loc.get("collection") or envelope.asset_id.split("/")[-1]

        warnings: List[str] = []
        completeness_score: Union[float, str, None] = "NOT_MEASURED"
        expected_count: Optional[int] = None

        # Decode payload if bytes
        if isinstance(payload, bytes):
            for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
                try:
                    payload = payload.decode(enc)
                    break
                except UnicodeDecodeError:
                    continue

        # 1. SQL Schema DDL or JSON Schema Definition
        if fmt in ("sql_schema", "json_schema") or "schema" in fmt or (
            isinstance(payload, str) and ("CREATE TABLE" in payload.upper() or "ALTER TABLE" in payload.upper())
        ):
            units, completeness_score, warnings = cls._parse_schema(envelope, payload, db_name, container_name)
            expected_count = len(units)

        # 2. CSV / TSV tabular data
        elif fmt in ("csv", "tsv") or (
            isinstance(payload, str)
            and ("\n" in payload)
            and ("," in payload or "\t" in payload)
            and not payload.strip().startswith(("{", "[", "<"))
            and not fmt.startswith("json")
        ):
            units, completeness_score, warnings, expected_count = cls._parse_csv(envelope, str(payload), db_name, container_name, delimiter="\t" if fmt == "tsv" else None)

        # 3. XML hierarchical markup
        elif fmt == "xml" or (isinstance(payload, str) and payload.strip().startswith("<") and payload.strip().endswith(">")):
            units, completeness_score, warnings, expected_count = cls._parse_xml(envelope, str(payload), db_name, container_name)

        # 4. JSONL / NDJSON streams
        elif fmt in ("jsonl", "ndjson") or (isinstance(payload, str) and envelope.asset_id.endswith(".jsonl")):
            units, completeness_score, warnings, expected_count = cls._parse_jsonl(envelope, str(payload), db_name, container_name)

        # 5. Native Dict / JSON Document
        elif isinstance(payload, dict):
            units = cls._parse_single_dict(envelope, payload, db_name, container_name)
            expected_count = 1
            completeness_score = 1.0

        # 6. Native List of Records
        elif isinstance(payload, list):
            units, completeness_score, warnings, expected_count = cls._parse_record_list(envelope, payload, db_name, container_name)

        # 7. Textual JSON payload or JSON scalar
        elif isinstance(payload, str):
            clean_str = payload.strip()
            try:
                parsed_json = json.loads(clean_str)
                if isinstance(parsed_json, dict):
                    units = cls._parse_single_dict(envelope, parsed_json, db_name, container_name)
                    expected_count = 1
                    completeness_score = 1.0
                elif isinstance(parsed_json, list):
                    units, completeness_score, warnings, expected_count = cls._parse_record_list(envelope, parsed_json, db_name, container_name)
                else:
                    # JSON scalar (int, float, bool, string, null)
                    units = cls._parse_scalar(envelope, parsed_json, db_name, container_name)
                    expected_count = 1
                    completeness_score = "NOT_MEASURED"
            except json.JSONDecodeError:
                # Fallback to plain line records
                lines = [l.strip() for l in clean_str.splitlines() if l.strip()]
                expected_count = len(lines)
                for idx, line in enumerate(lines):
                    u = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        source_id=str(envelope.source_id),
                        source_version=envelope.source_version,
                        source_type=fmt or "structured",
                        block_type="structured_record",
                        content_role=ContentRole.POLICY_RULE,
                        raw_content=line,
                        normalized_content=line,
                        content_text=line,
                        structured_data={"raw_line": line},
                        locator={"line_index": idx + 1, "database": db_name, "table": container_name, "database_table": container_name, **loc},
                        hierarchical_context=[db_name, container_name],
                        sequence_index=idx,
                    )
                    units.append(u)
                completeness_score = 1.0 if expected_count > 0 else "NOT_MEASURED"

        # 8. Raw scalar value (int, float, bool, None) passed directly
        else:
            units = cls._parse_scalar(envelope, payload, db_name, container_name)
            expected_count = 1
            completeness_score = "NOT_MEASURED"

        # Truncation and dropped records detection
        is_truncated = any("truncated" in w.lower() for w in warnings)
        truncation_reason = next((w for w in warnings if "truncated" in w.lower()), None)
        dropped_count = (expected_count - len(units)) if (expected_count and expected_count > len(units) and is_truncated) else 0

        # Run extraction validation
        val_res = EvidenceExtractionValidator.validate(units)
        warnings.extend(val_res.warnings)

        # Compute status
        if len(units) == 0:
            status = ExtractionStatus.EMPTY
            completeness_score = "NOT_MEASURED"
        elif is_truncated or (isinstance(completeness_score, float) and completeness_score < 1.0) or not val_res.is_valid:
            status = ExtractionStatus.PARTIAL
        elif warnings:
            status = ExtractionStatus.PARTIAL
        else:
            status = ExtractionStatus.SUCCESS

        quality_report = ExtractionQualityReport(
            status=status,
            completeness_score=completeness_score,
            expected_csv_rows=expected_count if fmt in ("csv", "tsv") else None,
            processed_csv_rows=len(units) if fmt in ("csv", "tsv") else None,
            expected_jsonl_records=expected_count if fmt in ("jsonl", "ndjson") else None,
            processed_jsonl_records=len(units) if fmt in ("jsonl", "ndjson") else None,
            expected_records=expected_count if fmt in ("json", "database", "postgres", "mysql", "mongodb") else None,
            processed_records=len(units) if fmt in ("json", "database", "postgres", "mysql", "mongodb") else None,
            expected_fields=sum(len(u.structured_data.get("flattened_fields", {})) for u in units),
            processed_fields=sum(len(u.structured_data.get("flattened_fields", {})) for u in units),
            total_units=len(units),
            valid_evidence_units=len(units) - len(val_res.duplicate_ids),
            valid_source_locators=sum(1 for u in units if u.locator and any(u.locator.model_dump().values())),
            is_truncated=is_truncated,
            truncation_reason=truncation_reason,
            dropped_records_count=dropped_count,
            warnings=warnings,
            errors=list(val_res.errors),
            parser_name="StructuredDataParser",
        )

        quality_metrics = {
            "parsed_units": len(units),
            "database": db_name,
            "container": container_name,
            "native_format": fmt,
            "expected_count": expected_count,
            "processed_count": len(units),
            "completeness_status": "COMPLETED" if status == ExtractionStatus.SUCCESS else ("PARTIAL" if status == ExtractionStatus.PARTIAL else status.value),
            "is_truncated": is_truncated,
            "truncation_reason": truncation_reason,
            "dropped_records_count": dropped_count,
            "fields_indexed": sum(len(u.structured_data.get("flattened_fields", {})) for u in units),
            "warnings": warnings,
            "errors": list(val_res.errors),
        }

        return ParsedEvidenceResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.STRUCTURED,
            parser_name="StructuredDataParser",
            units=units,
            completeness_score=completeness_score,
            quality_metrics=quality_metrics,
            quality_report=quality_report,
            extraction_status=status,
        )

    @classmethod
    def _parse_csv(
        cls,
        envelope: CanonicalSourceEnvelope,
        csv_text: str,
        db_name: str,
        container_name: str,
        delimiter: Optional[str] = None,
    ) -> Tuple[List[ParsedEvidenceUnit], float, list[str], int]:
        """Parses CSV/TSV preserving empty cells, column positions, quotes, and source coordinates."""
        units: List[ParsedEvidenceUnit] = []
        warnings: List[str] = []

        f = io.StringIO(csv_text)
        try:
            if not delimiter:
                sample = csv_text[:4096]
                try:
                    dialect = csv.Sniffer().sniff(sample)
                    delimiter = dialect.delimiter
                    if not delimiter or delimiter in ("\r", "\n", "\r\n") or len(delimiter) != 1:
                        delimiter = ","
                except Exception:
                    delimiter = ","
            reader = csv.reader(f, delimiter=delimiter or ",")
            rows = list(reader)
        except Exception as exc:
            warnings.append(f"CSV parsing failed: {exc}")
            return [], 0.0, warnings, 0

        if not rows:
            return [], 1.0, warnings, 0

        headers = [h.strip() for h in rows[0]]
        data_rows = rows[1:]
        expected_rows = len(data_rows)

        # Parent dataset summary unit
        summary_text = f"CSV Dataset `{container_name}` ({expected_rows} rows, {len(headers)} columns): {', '.join(headers)}"
        dataset_summary = ParsedEvidenceUnit.create(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_id=str(envelope.source_id),
            source_version=envelope.source_version,
            source_type="csv",
            block_type="table",
            content_role=ContentRole.POLICY_RULE,
            raw_content=rows[0][0] if rows else "",
            normalized_content=summary_text,
            content_text=summary_text,
            structured_data={"headers": headers, "total_rows": expected_rows, "database": db_name, "container": container_name},
            locator={"database": db_name, "table": container_name, "database_table": container_name, "headers": headers, **envelope.locator_metadata},
            hierarchical_context=[db_name, container_name, "Dataset"],
            sequence_index=0,
        )
        units.append(dataset_summary)

        # Process each row preserving column position and empty cells
        for row_idx, row in enumerate(data_rows, start=1):
            row_dict = {}
            for col_idx, h in enumerate(headers):
                cell_val = row[col_idx] if col_idx < len(row) else ""
                row_dict[h] = cell_val

            # Preserve extra columns if row exceeds headers
            if len(row) > len(headers):
                for col_idx in range(len(headers), len(row)):
                    row_dict[f"extra_col_{col_idx+1}"] = row[col_idx]

            row_text = f"Row {row_idx}: " + " | ".join(f"{k}: {v}" for k, v in row_dict.items())
            raw_row_line = delimiter.join(f'"{c}"' if (delimiter in c or '"' in c or '\n' in c) else c for c in row)

            row_unit = ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                source_id=str(envelope.source_id),
                source_version=envelope.source_version,
                source_type="csv",
                block_type="table_row",
                content_role=ContentRole.POLICY_RULE,
                raw_content=raw_row_line,
                normalized_content=row_text,
                content_text=row_text,
                parent_id=dataset_summary.evidence_instance_id,
                relationships=[
                    EvidenceRelationship(
                        relation_type=StructuralRelationType.TABLE_HAS_ROW,
                        target_unit_id=dataset_summary.evidence_instance_id,
                    )
                ],
                structured_data={
                    "row_index": row_idx,
                    "columns": row_dict,
                    "headers": headers,
                    "database": db_name,
                    "container": container_name,
                },
                locator={
                    "row_index": row_idx,
                    "database": db_name,
                    "container": container_name,
                    "database_table": container_name,
                    "table_id": f"csv_{container_name}",
                    **envelope.locator_metadata,
                },
                hierarchical_context=[db_name, container_name, f"Row#{row_idx}"],
                sequence_index=row_idx,
            )
            units.append(row_unit)

        completeness = len(data_rows) / expected_rows if expected_rows > 0 else 1.0
        return units, completeness, warnings, expected_rows

    @classmethod
    def _parse_xml(
        cls,
        envelope: CanonicalSourceEnvelope,
        xml_text: str,
        db_name: str,
        container_name: str,
    ) -> Tuple[List[ParsedEvidenceUnit], float, list[str], int]:
        """Parses XML preserving element paths, attributes, namespaces, and parent-child hierarchy."""
        units: List[ParsedEvidenceUnit] = []
        warnings: List[str] = []

        try:
            root = ET.fromstring(xml_text)
        except Exception as exc:
            warnings.append(f"XML parsing failed: {exc}")
            return [], 0.0, warnings, 0

        element_map: dict[str, str] = {}
        total_elements = len(list(root.iter()))

        def walk(elem: ET.Element, parent_path: str, parent_unit_id: Optional[str], seq_idx: int) -> int:
            raw_tag = elem.tag
            clean_tag = raw_tag.split("}")[-1] if "}" in raw_tag else raw_tag
            current_path = f"{parent_path}/{clean_tag}"

            elem_text = (elem.text or "").strip()
            attribs = dict(elem.attrib)
            has_children = len(elem) > 0

            # Determine readable representation
            attr_parts = [f'{k}="{v}"' for k, v in attribs.items()]
            attr_summary = f" [{', '.join(attr_parts)}]" if attr_parts else ""
            if elem_text:
                norm_text = f"<{clean_tag}{attr_summary}>: {elem_text}"
            elif attribs:
                norm_text = f"<{clean_tag}{attr_summary}>"
            else:
                norm_text = f"<{clean_tag}>"

            raw_elem_str = ET.tostring(elem, encoding="unicode").strip()
            # If element has children, don't dump all children in raw snippet if too large
            if has_children and len(raw_elem_str) > 500:
                raw_elem_str = f"<{clean_tag}{attr_summary}> ... </{clean_tag}>"

            relations = []
            if parent_unit_id:
                relations.append(
                    EvidenceRelationship(
                        relation_type=StructuralRelationType.PARENT_CHILD,
                        target_unit_id=parent_unit_id,
                    )
                )

            unit = ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                source_id=str(envelope.source_id),
                source_version=envelope.source_version,
                source_type="xml",
                block_type="xml_element",
                content_role=ContentRole.POLICY_RULE,
                raw_content=raw_elem_str,
                normalized_content=norm_text,
                content_text=norm_text,
                parent_id=parent_unit_id,
                relationships=relations,
                structured_data={
                    "tag": clean_tag,
                    "raw_tag": raw_tag,
                    "attributes": attribs,
                    "xpath": current_path,
                    "text": elem_text,
                    "has_children": has_children,
                    "database": db_name,
                    "container": container_name,
                },
                locator={
                    "json_path": current_path,
                    "field_path": clean_tag,
                    "database": db_name,
                    "container": container_name,
                    "database_table": container_name,
                    **envelope.locator_metadata,
                },
                hierarchical_context=[db_name, container_name, current_path.lstrip("/")],
                sequence_index=seq_idx,
            )
            units.append(unit)
            current_unit_id = unit.evidence_instance_id

            next_seq = seq_idx + 1
            for child in elem:
                next_seq = walk(child, current_path, current_unit_id, next_seq)
            return next_seq

        walk(root, "", None, 0)
        completeness = len(units) / total_elements if total_elements > 0 else 1.0
        return units, completeness, warnings, total_elements

    @classmethod
    def _parse_jsonl(
        cls,
        envelope: CanonicalSourceEnvelope,
        jsonl_text: str,
        db_name: str,
        container_name: str,
    ) -> Tuple[List[ParsedEvidenceUnit], float, list[str], int]:
        """Parses JSONL / NDJSON streams without truncating after 100 records and reporting errors."""
        units: List[ParsedEvidenceUnit] = []
        warnings: List[str] = []

        lines = [l.strip() for l in jsonl_text.splitlines() if l.strip()]
        total_lines = len(lines)
        if total_lines == 0:
            return [], 1.0, warnings, 0

        max_records = None
        if envelope.locator_metadata:
            raw_max = envelope.locator_metadata.get("max_records") or envelope.locator_metadata.get("limit")
            if raw_max is not None:
                try:
                    max_records = int(raw_max)
                except (ValueError, TypeError):
                    max_records = None

        for idx, line in enumerate(lines):
            if max_records is not None and len(units) >= max_records:
                warnings.append(f"JSONL stream truncated after {max_records} records.")
                break
            try:
                rec = json.loads(line)
                if isinstance(rec, dict):
                    sub = cls._parse_single_dict(envelope, rec, db_name, container_name, base_seq_index=len(units))
                    units.extend(sub)
                elif isinstance(rec, list):
                    sub, _, sub_warn, _ = cls._parse_record_list(envelope, rec, db_name, container_name, base_seq_index=len(units))
                    units.extend(sub)
                    warnings.extend(sub_warn)
                else:
                    sub = cls._parse_scalar(envelope, rec, db_name, container_name, seq_index=len(units))
                    units.extend(sub)
            except Exception as exc:
                warnings.append(f"JSONL line {idx+1} malformed: {exc}")

        completeness = len(units) / total_lines if total_lines > 0 else 1.0
        return units, min(1.0, completeness), warnings, total_lines

    @classmethod
    def _parse_scalar(
        cls,
        envelope: CanonicalSourceEnvelope,
        value: Any,
        db_name: str,
        container_name: str,
        seq_index: int = 0,
    ) -> List[ParsedEvidenceUnit]:
        """Creates a valid EvidenceUnit for JSON scalar payloads (numbers, booleans, strings, null)."""
        val_repr = "null" if value is None else json.dumps(value, default=str)
        type_name = type(value).__name__ if value is not None else "null"
        content_text = f"Scalar value in `{db_name}.{container_name}`: {val_repr} (type: {type_name})"

        unit = ParsedEvidenceUnit.create(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_id=str(envelope.source_id),
            source_version=envelope.source_version,
            source_type=envelope.native_format or "json_scalar",
            block_type="json_scalar",
            content_role=ContentRole.POLICY_RULE,
            raw_content=val_repr,
            normalized_content=content_text,
            content_text=content_text,
            structured_data={
                "scalar_value": value,
                "data_type": type_name,
                "database": db_name,
                "container": container_name,
            },
            locator={
                "database": db_name,
                "container": container_name,
                "database_table": container_name,
                "json_path": "$",
                **envelope.locator_metadata,
            },
            hierarchical_context=[db_name, container_name, "Scalar"],
            sequence_index=seq_index,
        )
        return [unit]

    @classmethod
    def _parse_schema(
        cls,
        envelope: CanonicalSourceEnvelope,
        payload: Any,
        db_name: str,
        container_name: str,
    ) -> Tuple[List[ParsedEvidenceUnit], float, list[str]]:
        """Parses SQL DDL text or structured schema dictionaries, preserving constraints and falsy defaults."""
        units: List[ParsedEvidenceUnit] = []
        warnings: List[str] = []

        # Case A: SQL DDL text string
        if isinstance(payload, str) and ("CREATE TABLE" in payload.upper() or "ALTER TABLE" in payload.upper()):
            parsed_tables = _parse_sql_ddl_text(payload)
            if not parsed_tables:
                warnings.append("No CREATE TABLE statements found in SQL DDL payload")
                return [], 0.0, warnings

            total_items = 0
            for t_idx, tbl in enumerate(parsed_tables):
                t_schema = tbl['schema'] or db_name
                t_name = tbl['table'] or container_name
                t_cols = tbl['columns']
                t_constraints = tbl['constraints']
                total_items += len(t_cols) + len(t_constraints)

                summary_text = f"Database `{t_schema}` > Table `{t_name}` SQL Schema ({len(t_cols)} columns, {len(t_constraints)} constraints)"
                parent_unit = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    source_id=str(envelope.source_id),
                    source_version=envelope.source_version,
                    source_type="sql_schema",
                    block_type="schema_definition",
                    content_role=ContentRole.DEFINITION,
                    raw_content=payload,
                    normalized_content=summary_text,
                    content_text=summary_text,
                    structured_data={
                        "schema": t_schema,
                        "table": t_name,
                        "column_count": len(t_cols),
                        "constraint_count": len(t_constraints),
                        "database": db_name,
                        "container": t_name,
                    },
                    locator={
                        "database": db_name,
                        "container": t_name,
                        "database_table": t_name,
                        **envelope.locator_metadata,
                    },
                    hierarchical_context=[db_name, t_name, "Schema"],
                    sequence_index=len(units),
                )
                units.append(parent_unit)

                # Column units
                for c_idx, col in enumerate(t_cols, start=1):
                    col_name = col['column_name']
                    col_type = col['data_type']
                    is_nullable = col['is_nullable']
                    default_val = col['default']
                    is_pk = col['is_primary_key']
                    fk = col['foreign_key']

                    desc_parts = [f"Field `{col_name}`: type {col_type}", f"nullable={is_nullable}"]
                    if default_val is not None:
                        desc_parts.append(f"default={default_val}")
                    if is_pk:
                        desc_parts.append("PRIMARY KEY")
                    if fk:
                        desc_parts.append(f"REFERENCES {fk.get('table')}({fk.get('column')})")

                    col_text = ", ".join(desc_parts)
                    col_unit = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        source_id=str(envelope.source_id),
                        source_version=envelope.source_version,
                        source_type="sql_schema",
                        block_type="column_definition",
                        content_role=ContentRole.DEFINITION,
                        raw_content=json.dumps(col, default=str),
                        normalized_content=col_text,
                        content_text=col_text,
                        parent_id=parent_unit.evidence_instance_id,
                        relationships=[
                            EvidenceRelationship(
                                relation_type=StructuralRelationType.RECORD_HAS_FIELD,
                                target_unit_id=parent_unit.evidence_instance_id,
                            )
                        ],
                        structured_data={
                            **col,
                            "schema": t_schema,
                            "table": t_name,
                            "database": db_name,
                            "container": t_name,
                        },
                        locator={
                            "database": db_name,
                            "container": t_name,
                            "database_table": t_name,
                            "column": col_name,
                            "field_path": col_name,
                            **envelope.locator_metadata,
                        },
                        hierarchical_context=[db_name, t_name, col_name],
                        sequence_index=len(units),
                    )
                    units.append(col_unit)

                # Table constraint units
                for c_idx, constr in enumerate(t_constraints, start=1):
                    c_name = constr.get('name') or f"constraint_{c_idx}"
                    c_type = constr.get('type')
                    c_def = constr.get('definition')
                    constr_text = f"Constraint `{c_name}` ({c_type}): {c_def}"

                    constr_unit = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        source_id=str(envelope.source_id),
                        source_version=envelope.source_version,
                        source_type="sql_schema",
                        block_type="constraint_definition",
                        content_role=ContentRole.POLICY_RULE,
                        raw_content=json.dumps(constr, default=str),
                        normalized_content=constr_text,
                        content_text=constr_text,
                        parent_id=parent_unit.evidence_instance_id,
                        relationships=[
                            EvidenceRelationship(
                                relation_type=StructuralRelationType.RECORD_HAS_FIELD,
                                target_unit_id=parent_unit.evidence_instance_id,
                            )
                        ],
                        structured_data={
                            **constr,
                            "schema": t_schema,
                            "table": t_name,
                            "database": db_name,
                            "container": t_name,
                        },
                        locator={
                            "database": db_name,
                            "container": t_name,
                            "database_table": t_name,
                            "constraint": c_name,
                            "field_path": c_name,
                            **envelope.locator_metadata,
                        },
                        hierarchical_context=[db_name, t_name, f"Constraint#{c_name}"],
                        sequence_index=len(units),
                    )
                    units.append(constr_unit)

            return units, 1.0, warnings

        # Case B: Dict/List schema representation
        columns = []
        if isinstance(payload, dict):
            columns = payload.get("columns", []) or payload.get("fields", [])
        elif isinstance(payload, list):
            columns = payload

        schema_text = f"Database `{db_name}` > Container `{container_name}` Schema Definition"
        raw_schema_str = json.dumps(payload, default=str) if not isinstance(payload, str) else payload
        if isinstance(payload, dict):
            summary_parts = [f"Database: {db_name}", f"Container: {container_name}"]
            for k, v in payload.items():
                if k not in ("columns", "fields") and isinstance(v, (str, int, bool)):
                    summary_parts.append(f"{k}: {v}")
            schema_text += " (" + ", ".join(summary_parts) + ")"

        summary_unit = ParsedEvidenceUnit.create(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_id=str(envelope.source_id),
            source_version=envelope.source_version,
            source_type=envelope.native_format or "sql_schema",
            block_type="schema_definition",
            content_role=ContentRole.DEFINITION,
            raw_content=raw_schema_str,
            normalized_content=schema_text,
            content_text=schema_text,
            structured_data={"raw_schema": payload, "database": db_name, "container": container_name},
            locator={"database": db_name, "container": container_name, "database_table": container_name, **envelope.locator_metadata},
            hierarchical_context=[db_name, container_name, "Schema"],
            sequence_index=0,
        )
        units.append(summary_unit)

        for idx, col in enumerate(columns):
            if isinstance(col, dict):
                col_name = col.get("column_name") or col.get("name") or col.get("field") or f"field_{idx+1}"
                col_type = col.get("data_type") or col.get("type") or "unknown"
                is_nullable = col.get("is_nullable", True)
                default_val = col.get("column_default") if "column_default" in col else col.get("default")

                col_text = f"Field `{col_name}`: type {col_type}, nullable={is_nullable}"
                if default_val is not None:
                    col_text += f", default={default_val}"

                u = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    source_id=str(envelope.source_id),
                    source_version=envelope.source_version,
                    source_type=envelope.native_format or "sql_schema",
                    block_type="column_definition",
                    content_role=ContentRole.DEFINITION,
                    raw_content=json.dumps(col, default=str),
                    normalized_content=col_text,
                    content_text=col_text,
                    parent_id=summary_unit.evidence_instance_id,
                    relationships=[
                        EvidenceRelationship(
                            relation_type=StructuralRelationType.RECORD_HAS_FIELD,
                            target_unit_id=summary_unit.evidence_instance_id,
                        )
                    ],
                    structured_data={
                        "column_name": col_name,
                        "data_type": col_type,
                        "is_nullable": is_nullable,
                        "default": default_val,
                        "database": db_name,
                        "container": container_name,
                    },
                    locator={
                        "database": db_name,
                        "container": container_name,
                        "database_table": container_name,
                        "column": col_name,
                        "field_path": col_name,
                        **envelope.locator_metadata,
                    },
                    hierarchical_context=[db_name, container_name, col_name],
                    sequence_index=idx + 1,
                )
                units.append(u)

        return units, 1.0, warnings

    @classmethod
    def _parse_single_dict(
        cls,
        envelope: CanonicalSourceEnvelope,
        doc: dict[str, Any],
        db_name: str,
        container_name: str,
        base_seq_index: int = 0,
    ) -> List[ParsedEvidenceUnit]:
        """Parses a single dictionary/document into a parent record unit and discoverable child units."""
        units: List[ParsedEvidenceUnit] = []
        pk_val = str(doc.get("_id") or doc.get("id") or doc.get("pk") or envelope.asset_id.split("/")[-1])

        flattened = _flatten_json_paths(doc)

        # Full readable representation preserving ALL fields without location coupling
        field_strs = [f"{k}: {v}" for k, v in flattened.items()]
        content_text = f"Record (ID: {pk_val}): " + ", ".join(field_strs)

        parent_unit = ParsedEvidenceUnit.create(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_id=str(envelope.source_id),
            source_version=envelope.source_version,
            source_type=envelope.native_format or "database_record",
            block_type="database_record",
            content_role=ContentRole.POLICY_RULE,
            raw_content=json.dumps(doc, sort_keys=True, default=str),
            normalized_content=content_text,
            content_text=content_text,
            structured_data={
                "record_id": pk_val,
                "raw_record": doc,
                "flattened_fields": flattened,
            },
            locator={
                "database": db_name,
                "container": container_name,
                "database_table": container_name,
                "record_id": pk_val,
                "primary_key": pk_val,
                **envelope.locator_metadata,
            },
            hierarchical_context=[db_name, container_name, f"Record#{pk_val}"],
            sequence_index=base_seq_index,
        )
        units.append(parent_unit)

        # Create child units for meaningful fields or field groups when record has complex sub-resources
        # or when the record is large (> 10 flattened fields), avoiding unnecessary duplication for small records.
        child_seq = base_seq_index + 1
        has_child_lists = any(isinstance(v, list) and v and isinstance(v[0], dict) for v in doc.values())
        is_large_record = len(flattened) > 10

        if is_large_record:
            nested_groups: dict[str, dict[str, Any]] = {}
            scalar_fields: dict[str, Any] = {}
            child_lists: dict[str, list[Any]] = {}

            for k, v in doc.items():
                if isinstance(v, dict) and v:
                    nested_groups[k] = v
                elif isinstance(v, list) and v:
                    child_lists[k] = v
                else:
                    scalar_fields[k] = v

            # Create child units for nested groups
            for group_name, group_data in nested_groups.items():
                flat_group = _flatten_json_paths(group_data, prefix=group_name)
                group_text = f"Section `{group_name}` in Record (ID: {pk_val}): " + ", ".join(f"{k}: {v}" for k, v in flat_group.items())
                child_u = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    source_id=str(envelope.source_id),
                    source_version=envelope.source_version,
                    source_type=envelope.native_format or "database_record",
                    block_type="record_field",
                    content_role=ContentRole.POLICY_RULE,
                    raw_content=json.dumps(group_data, default=str),
                    normalized_content=group_text,
                    content_text=group_text,
                    parent_id=parent_unit.evidence_instance_id,
                    relationships=[
                        EvidenceRelationship(
                            relation_type=StructuralRelationType.RECORD_HAS_FIELD,
                            target_unit_id=parent_unit.evidence_instance_id,
                        )
                    ],
                    structured_data={
                        "field_group": group_name,
                        "fields": flat_group,
                        "database": db_name,
                        "container": container_name,
                        "record_id": pk_val,
                    },
                    locator={
                        "database": db_name,
                        "container": container_name,
                        "database_table": container_name,
                        "record_id": pk_val,
                        "primary_key": pk_val,
                        "field_path": group_name,
                        **envelope.locator_metadata,
                    },
                    hierarchical_context=[db_name, container_name, f"Record#{pk_val}", group_name],
                    sequence_index=child_seq,
                )
                units.append(child_u)
                child_seq += 1

            # For scalar fields: group in coherent clusters of 8 fields
            scalar_items = list(scalar_fields.items())
            chunk_size = 8
            if len(scalar_items) > chunk_size:
                for i in range(0, len(scalar_items), chunk_size):
                    chunk = dict(scalar_items[i : i + chunk_size])
                    chunk_keys = list(chunk.keys())
                    chunk_label = f"fields_{chunk_keys[0]}_to_{chunk_keys[-1]}"
                    chunk_text = f"Fields ({chunk_keys[0]}..{chunk_keys[-1]}) in Record (ID: {pk_val}): " + ", ".join(f"{k}: {v}" for k, v in chunk.items())

                    chunk_u = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        source_id=str(envelope.source_id),
                        source_version=envelope.source_version,
                        source_type=envelope.native_format or "database_record",
                        block_type="record_field",
                        content_role=ContentRole.POLICY_RULE,
                        raw_content=json.dumps(chunk, default=str),
                        normalized_content=chunk_text,
                        content_text=chunk_text,
                        parent_id=parent_unit.evidence_instance_id,
                        relationships=[
                            EvidenceRelationship(
                                relation_type=StructuralRelationType.RECORD_HAS_FIELD,
                                target_unit_id=parent_unit.evidence_instance_id,
                            )
                        ],
                        structured_data={
                            "field_group": chunk_label,
                            "fields": chunk,
                            "database": db_name,
                            "container": container_name,
                            "record_id": pk_val,
                        },
                        locator={
                            "database": db_name,
                            "container": container_name,
                            "database_table": container_name,
                            "record_id": pk_val,
                            "primary_key": pk_val,
                            "field_path": chunk_label,
                            **envelope.locator_metadata,
                        },
                        hierarchical_context=[db_name, container_name, f"Record#{pk_val}", chunk_label],
                        sequence_index=child_seq,
                    )
                    units.append(chunk_u)
                    child_seq += 1

        # For child lists (e.g. Jira comments, GitHub PR reviews, Slack replies), always preserve as child items
        if has_child_lists:
            for list_name, list_val in doc.items():
                if isinstance(list_val, list) and list_val and isinstance(list_val[0], dict):
                    for item_idx, item in enumerate(list_val):
                        item_text = f"Item in `{list_name}[{item_idx}]` (Parent: {pk_val}): " + ", ".join(f"{k}: {v}" for k, v in item.items() if not isinstance(v, (dict, list)))
                        item_u = ParsedEvidenceUnit.create(
                            envelope_id=envelope.envelope_id,
                            asset_id=envelope.asset_id,
                            source_id=str(envelope.source_id),
                            source_version=envelope.source_version,
                            source_type=envelope.native_format or "database_record",
                            block_type="record_item",
                            content_role=ContentRole.POLICY_RULE,
                            raw_content=json.dumps(item, default=str),
                            normalized_content=item_text,
                            content_text=item_text,
                            parent_id=parent_unit.evidence_instance_id,
                            relationships=[
                                EvidenceRelationship(
                                    relation_type=StructuralRelationType.PARENT_CHILD,
                                    target_unit_id=parent_unit.evidence_instance_id,
                                )
                            ],
                            structured_data={
                                "list_name": list_name,
                                "array_index": item_idx,
                                "item_data": item,
                                "parent_record_id": pk_val,
                            },
                            locator={
                                "database": db_name,
                                "container": container_name,
                                "database_table": container_name,
                                "record_id": pk_val,
                                "json_path": f"{list_name}[{item_idx}]",
                                "array_index": item_idx,
                                **envelope.locator_metadata,
                            },
                            hierarchical_context=[db_name, container_name, f"Record#{pk_val}", f"{list_name}[{item_idx}]"],
                            sequence_index=child_seq,
                        )
                        units.append(item_u)
                        child_seq += 1

        return units

    @classmethod
    def _parse_record_list(
        cls,
        envelope: CanonicalSourceEnvelope,
        records: list[Any],
        db_name: str,
        container_name: str,
        base_seq_index: int = 0,
    ) -> Tuple[List[ParsedEvidenceUnit], float, list[str], int]:
        """Parses a list of records preserving indexes, fields, and error handling."""
        units: List[ParsedEvidenceUnit] = []
        warnings: List[str] = []
        expected_records = len(records)

        for idx, rec in enumerate(records):
            cur_seq = base_seq_index + len(units)
            if isinstance(rec, dict):
                sub_units = cls._parse_single_dict(envelope, rec, db_name, container_name, base_seq_index=cur_seq)
                units.extend(sub_units)
            else:
                raw_rec_str = str(rec)
                u = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    source_id=str(envelope.source_id),
                    source_version=envelope.source_version,
                    source_type=envelope.native_format or "database_record",
                    block_type="record_row",
                    content_role=ContentRole.POLICY_RULE,
                    raw_content=raw_rec_str,
                    normalized_content=raw_rec_str,
                    content_text=raw_rec_str,
                    structured_data={"row_value": rec, "database": db_name, "container": container_name},
                    locator={
                        "row_index": idx,
                        "database": db_name,
                        "container": container_name,
                        "database_table": container_name,
                    },
                    hierarchical_context=[db_name, container_name, f"Row#{idx}"],
                    sequence_index=cur_seq,
                )
                units.append(u)

        completeness = len(units) / expected_records if expected_records > 0 else 1.0
        return units, min(1.0, completeness), warnings, expected_records
