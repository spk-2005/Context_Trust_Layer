"""
Layer 4: Specialized Metadata & Operational Parser.
Processes BI/semantic models (dbt, Looker), lineage graphs, audit telemetry, and configurations.
Preserves metric formulae, dependency graphs, event structures, and governance policies.
"""

from __future__ import annotations

import json
import logging
from typing import Any, List

from app.db.enums import SourceFamily
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit

logger = logging.getLogger(__name__)


class MetadataParser:
    """Specialized parser for BI metrics, lineage graphs, audit logs, and configuration trees."""

    @classmethod
    async def parse(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        units: List[ParsedEvidenceUnit] = []
        payload = envelope.raw_payload
        fmt = (envelope.native_format or "").lower().strip()
        asset_id = envelope.asset_id

        # 1. Parse JSON or Dict payload
        parsed_obj: dict[str, Any] = {}
        if isinstance(payload, dict):
            parsed_obj = payload
        elif isinstance(payload, str):
            try:
                parsed_obj = json.loads(payload)
            except Exception:
                # Text config or log entries
                for idx, line in enumerate(payload.splitlines()):
                    if line.strip():
                        u = ParsedEvidenceUnit.create(
                            envelope_id=envelope.envelope_id,
                            asset_id=asset_id,
                            block_type="operational_entry",
                            content_text=line.strip(),
                            structured_data={"raw_entry": line.strip()},
                            locator={"line_number": idx + 1, **envelope.locator_metadata},
                            hierarchical_context=["Operational Log", f"Entry#{idx+1}"],
                            sequence_index=idx,
                        )
                        units.append(u)

        if parsed_obj:
            # Case A: BI Metric Definition
            if "metrics" in parsed_obj or "calculation" in parsed_obj or "formula" in parsed_obj:
                metrics_list = parsed_obj.get("metrics")
                if isinstance(metrics_list, list):
                    for idx, m in enumerate(metrics_list):
                        name = m.get("name") or f"metric_{idx+1}"
                        formula = m.get("formula") or m.get("calculation") or m.get("sql") or ""
                        desc = m.get("description") or ""
                        unit_text = f"Metric `{name}`: {desc} (Calculation: `{formula}`)"
                        
                        u = ParsedEvidenceUnit.create(
                            envelope_id=envelope.envelope_id,
                            asset_id=asset_id,
                            block_type="metric_definition",
                            content_text=unit_text,
                            structured_data=m,
                            locator={"metric_name": name, **envelope.locator_metadata},
                            hierarchical_context=["BI Semantic Layer", "Metrics", name],
                            sequence_index=idx,
                        )
                        units.append(u)
                else:
                    name = parsed_obj.get("name") or asset_id.split("/")[-1]
                    formula = parsed_obj.get("formula") or parsed_obj.get("calculation") or ""
                    u = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=asset_id,
                        block_type="metric_definition",
                        content_text=f"Metric `{name}`: Calculation: `{formula}`",
                        structured_data=parsed_obj,
                        locator={"metric_name": name, **envelope.locator_metadata},
                        hierarchical_context=["BI Semantic Layer", name],
                        sequence_index=0,
                    )
                    units.append(u)

            # Case B: Lineage Graph / DAG
            elif "nodes" in parsed_obj or "edges" in parsed_obj or "upstream" in parsed_obj:
                nodes = parsed_obj.get("nodes", [])
                for idx, node in enumerate(nodes if isinstance(nodes, list) else []):
                    node_name = node.get("id") or node.get("name") or f"node_{idx+1}"
                    upstreams = node.get("upstream", []) or node.get("depends_on", [])
                    u_text = f"Lineage Node `{node_name}` depends on: {', '.join(upstreams) if upstreams else 'Root'}"
                    
                    u = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=asset_id,
                        block_type="lineage_node",
                        content_text=u_text,
                        structured_data=node,
                        locator={"node_id": node_name, **envelope.locator_metadata},
                        hierarchical_context=["Lineage Graph", node_name],
                        sequence_index=idx,
                    )
                    units.append(u)

            # Case C: Generic Operational Metadata / Configuration
            else:
                for idx, (k, v) in enumerate(parsed_obj.items()):
                    u_text = f"Config Property `{k}` = {v}"
                    u = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=asset_id,
                        block_type="config_property",
                        content_text=u_text,
                        structured_data={"key": k, "value": v},
                        locator={"property_key": k, **envelope.locator_metadata},
                        hierarchical_context=["Configuration", k],
                        sequence_index=idx,
                    )
                    units.append(u)

        quality_metrics = {
            "parsed_units": len(units),
            "asset_id": asset_id,
            "format": fmt,
        }

        return ParsedEvidenceResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.METADATA,
            parser_name="MetadataParser",
            units=units,
            completeness_score=1.0,
            quality_metrics=quality_metrics,
        )
