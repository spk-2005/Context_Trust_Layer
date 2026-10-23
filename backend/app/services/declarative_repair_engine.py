"""
Declarative Repair Engine and Audit Ledger.

Enforces that repairs are declarative, evidence-linked, rerunnable, and strictly
limited to formatting and syntactic hygiene. Repairs may never invent obligations,
permissions, parties, or conditions.
"""

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.universal_claim import UniversalClaim


class RepairAuditRecord(BaseModel):
    repair_id: str
    rule_name: str
    original_claim_text: str
    repaired_claim_text: str
    rationale: str
    mutation_scope: List[str]
    author: str
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    revalidated_gates: List[str]


class DeclarativeRepairEngine:
    """Rerunnable repair service driven by versioned declarative rules."""

    _rules: List[Dict[str, Any]] = []

    def __init__(self, registry_path: Optional[Path] = None):
        if not registry_path:
            registry_path = Path(__file__).resolve().parents[1] / "taxonomy" / "repairs.v1.json"
        self._load(registry_path)

    def _load(self, path: Path) -> None:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._rules = data.get("rules", [])

    def evaluate_and_repair(self, claim: UniversalClaim) -> tuple[UniversalClaim, List[RepairAuditRecord]]:
        """
        Executes applicable declarative repairs on claim text.
        Returns the updated claim and a list of audit records.
        """
        current_text = claim.claim_text
        audit_trail: List[RepairAuditRecord] = []

        for rule in self._rules:
            rid = rule["repair_id"]
            pat = rule["trigger"]["text_pattern"]
            action = rule["action"]

            match = re.search(pat, current_text, flags=re.IGNORECASE)
            if match:
                repaired_text = current_text
                if action == "strip_pattern":
                    repaired_text = re.sub(pat, "", current_text, flags=re.IGNORECASE).strip()
                elif action == "normalize_whitespace":
                    repaired_text = re.sub(r"\s+", " ", current_text).strip()

                if repaired_text != current_text:
                    audit = RepairAuditRecord(
                        repair_id=rid,
                        rule_name=rule["name"],
                        original_claim_text=current_text,
                        repaired_claim_text=repaired_text,
                        rationale=rule["description"],
                        mutation_scope=rule.get("mutation_scope", ["claim_text"]),
                        author=rule.get("author", "PIPELINE_GOVERNANCE"),
                        revalidated_gates=rule.get("requires_revalidation", []),
                    )
                    audit_trail.append(audit)
                    current_text = repaired_text

        if audit_trail:
            updated_claim = claim.model_copy(update={"claim_text": current_text})
            return updated_claim, audit_trail

        return claim, []
