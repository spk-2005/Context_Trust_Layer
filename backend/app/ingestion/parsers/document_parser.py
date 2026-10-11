"""
Layer 4: Specialized Document Parser.
Processes narrative documents and files (Markdown, PDF, DOCX, HTML, Confluence pages, Plain text).
Preserves hierarchical heading trees, clause structures, markdown tables, and exact character offsets.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List

from app.db.enums import SourceFamily
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit

logger = logging.getLogger(__name__)


class DocumentParser:
    """Specialized AST parser for narrative documents and text files."""

    CLAUSE_PATTERN = re.compile(r"^(?:(?:Section|Article|Clause|Rule)\s+)?(\d+(?:\.\d+)*|[A-Z]\.|\([a-z0-9]+\))\s*[:.-]?\s+(.*)", re.IGNORECASE)
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)")
    TABLE_ROW_PATTERN = re.compile(r"^\|(.+)\|$")

    @classmethod
    async def parse(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        """Parses a document envelope into structured ParsedEvidenceUnits."""
        raw_text = envelope.get_payload_as_text()
        units: List[ParsedEvidenceUnit] = []
        
        lines = raw_text.splitlines(keepends=True)
        breadcrumb_stack: list[tuple[int, str]] = []  # (level, title)
        
        char_cursor = 0
        line_num = 1
        seq_idx = 0

        in_table = False
        table_headers: list[str] = []
        table_rows_buffer: list[dict[str, Any]] = []
        table_start_char = 0
        table_start_line = 0

        total_lines = len(lines)
        parsed_lines = 0

        for line_raw in lines:
            line_str = line_raw.strip()
            line_len = len(line_raw)
            line_start_char = char_cursor
            line_end_char = char_cursor + line_len
            parsed_lines += 1

            if not line_str:
                char_cursor = line_end_char
                line_num += 1
                continue

            # 1. Heading Detection (# H1, ## H2, etc.)
            h_match = cls.HEADING_PATTERN.match(line_str)
            if h_match:
                # Flush table if was in table
                if in_table:
                    in_table = False
                    table_headers = []

                level = len(h_match.group(1))
                h_title = h_match.group(2).strip()

                # Adjust breadcrumb hierarchy
                while breadcrumb_stack and breadcrumb_stack[-1][0] >= level:
                    breadcrumb_stack.pop()
                breadcrumb_stack.append((level, h_title))

                context = [h[1] for h in breadcrumb_stack]

                unit = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    block_type="heading",
                    content_text=h_title,
                    structured_data={"heading_level": level, "heading_text": h_title},
                    locator={
                        "line_start": line_num,
                        "line_end": line_num,
                        "start_char": line_start_char,
                        "end_char": line_end_char,
                        **envelope.locator_metadata,
                    },
                    hierarchical_context=context,
                    sequence_index=seq_idx,
                    metadata={"source_version": envelope.source_version},
                )
                units.append(unit)
                seq_idx += 1
                char_cursor = line_end_char
                line_num += 1
                continue

            # 2. Markdown Table Detection (| Col 1 | Col 2 |)
            t_match = cls.TABLE_ROW_PATTERN.match(line_str)
            if t_match:
                row_cells = [c.strip() for c in t_match.group(1).split("|")]
                
                # Check if separator row (|---|---|)
                is_separator = all(re.match(r"^:?-+:?$", c) for c in row_cells if c)
                if is_separator:
                    char_cursor = line_end_char
                    line_num += 1
                    continue

                if not in_table:
                    # First row is table header
                    in_table = True
                    table_headers = row_cells
                    table_start_char = line_start_char
                    table_start_line = line_num
                else:
                    # Data row
                    row_dict = {}
                    for idx, cell_val in enumerate(row_cells):
                        col_name = table_headers[idx] if idx < len(table_headers) else f"col_{idx+1}"
                        row_dict[col_name] = cell_val

                    context = [h[1] for h in breadcrumb_stack]
                    row_text = " | ".join(f"{k}: {v}" for k, v in row_dict.items())

                    unit = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        block_type="table_row",
                        content_text=row_text,
                        structured_data={"columns": row_dict, "table_headers": table_headers},
                        locator={
                            "line_start": line_num,
                            "line_end": line_num,
                            "start_char": line_start_char,
                            "end_char": line_end_char,
                            **envelope.locator_metadata,
                        },
                        hierarchical_context=context,
                        sequence_index=seq_idx,
                        metadata={"in_table": True, "table_start_line": table_start_line},
                    )
                    units.append(unit)
                    seq_idx += 1

                char_cursor = line_end_char
                line_num += 1
                continue
            else:
                in_table = False
                table_headers = []

            # 3. Clause / Bullet / Statement Detection
            context = [h[1] for h in breadcrumb_stack]
            clause_match = cls.CLAUSE_PATTERN.match(line_str)
            
            block_type = "clause" if clause_match or line_str.startswith(("-", "*", "•")) else "paragraph"
            
            clean_text = line_str.lstrip("-*• ").strip()
            
            unit = ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                block_type=block_type,
                content_text=clean_text,
                structured_data={"raw_line": line_str},
                locator={
                    "line_start": line_num,
                    "line_end": line_num,
                    "start_char": line_start_char,
                    "end_char": line_end_char,
                    **envelope.locator_metadata,
                },
                hierarchical_context=context,
                sequence_index=seq_idx,
                metadata={"source_version": envelope.source_version},
            )
            units.append(unit)
            seq_idx += 1

            char_cursor = line_end_char
            line_num += 1

        completeness = 1.0 if total_lines > 0 else 1.0
        quality_metrics = {
            "total_lines": total_lines,
            "parsed_units": len(units),
            "headings_count": sum(1 for u in units if u.block_type == "heading"),
            "clauses_count": sum(1 for u in units if u.block_type == "clause"),
            "table_rows_count": sum(1 for u in units if u.block_type == "table_row"),
            "char_count": char_cursor,
        }

        return ParsedEvidenceResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.DOCUMENT,
            parser_name="DocumentParser",
            units=units,
            completeness_score=completeness,
            quality_metrics=quality_metrics,
        )
