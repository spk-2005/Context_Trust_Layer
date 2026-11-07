"""
Unit tests for Phase 5: Trulin Layer 5 Candidate Discovery & Structured Claim Extraction.

Validates:
1. Conditional refund rule (conditions preserved, temporal scope captured, never universalized).
2. Rule with an exception (exceptions preserved, exception relationship captured, not dropped).
3. Definition that qualifies another rule (definition claim + rule with definition_references & relationship).
4. Table-derived approval limit (grid binding, column headers, cell value, multi-evidence relationship).
5. Nested JSON-derived policy fact (nested JSON paths, invariants, schema constraints).
6. Database field-derived fact (record identity, container, field facts, record_has_field relation).
7. Chat message containing a factual assertion (speaker, modality, temporal scope, policy fact).
8. Duplicate claims from different source locations (duplicate detected without deleting occurrences).
9. Contradictory claims from different versions (preserved as distinct candidates, not merged).
"""

import os
import sys
import uuid
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.db.enums import SourceFamily
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.models import (
    CandidateClaim,
    ExtractionStrategyType,
)
from app.extraction.pipeline import Layer5ExtractionPipeline
from app.extraction.unified_pipeline import UnifiedExtractionPipeline
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceRelationship,
    EvidenceUnit,
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
    SourceLocator,
    StructuralRelationType,
)


@pytest.mark.asyncio
async def test_conditional_refund_rule():
    """
    Test 1: Conditional refund rule.
    Conditions must be preserved with the rule they qualify, not separated or converted to universal claims.
    """
    text = "Customers may receive a full refund within 30 days of delivery, provided the item is unopened and accompanied by original receipt."
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://policies/refund.md",
        source_id="src_policy_01",
        source_version="v1.2",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content=text,
        normalized_content=text,
        content_text=text,
        locator={"page": 2, "line": 45},
    )

    is_cand, strat, reason = CandidateDiscoveryEngine.is_candidate(unit)
    assert is_cand is True

    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1

    claim = claims[0]
    assert claim.subject.lower() in ("customers", "customer", "company", "refund")
    assert claim.modality in ("MAY", "PERMITTED", "PERMISSION")
    # Conditions must be preserved
    assert len(claim.conditions) >= 1
    assert any("unopened" in c.lower() for c in claim.conditions)
    assert any("30 days" in c.lower() for c in claim.conditions)
    # Temporal scope must be extracted
    assert claim.temporal_scope is not None
    assert "30 days" in claim.temporal_scope.lower()
    # Source version and evidence IDs must be traceable
    assert claim.source_version == "v1.2"
    assert unit.unit_id in claim.evidence_unit_ids


@pytest.mark.asyncio
async def test_rule_with_exception():
    """
    Test 2: Rule with an exception.
    Exceptions must be preserved and bound to the candidate claim without turning it into an unexceptional rule.
    """
    text = "All merchandise may be returned within 14 days, except for clearance items and personalized goods."
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://policies/returns.md",
        source_id="src_policy_01",
        source_version="v2.0",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content=text,
        normalized_content=text,
        content_text=text,
        locator={"page": 3, "line": 12},
    )

    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1

    claim = claims[0]
    assert len(claim.exceptions) >= 1
    assert any("clearance" in e.lower() or "personalized" in e.lower() for e in claim.exceptions)
    assert claim.evidence_relationship_type == "rule_has_exception"
    assert claim.product_scope is not None
    assert "clearance" in claim.product_scope.lower() or "personalized" in claim.product_scope.lower()


@pytest.mark.asyncio
async def test_definition_qualifies_rule():
    """
    Test 3: Definition that qualifies another rule.
    Definitions must be extracted as definition claims, and referencing rules must preserve definition references.
    """
    # 1. Definition unit
    def_text = "'Like-new condition' means product is undamaged, in original packaging with all accessories."
    def_unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://policies/definitions.md",
        source_id="src_policy_01",
        block_type="clause",
        content_role=ContentRole.DEFINITION,
        raw_content=def_text,
        normalized_content=def_text,
        content_text=def_text,
        locator={"page": 1, "line": 5},
    )

    is_cand, strat, reason = CandidateDiscoveryEngine.is_candidate(def_unit)
    assert is_cand is True
    def_claims = DomainRuleExtractor.extract_from_unit(def_unit)
    assert len(def_claims) >= 1
    def_claim = def_claims[0]
    assert "like-new condition" in def_claim.subject.lower()
    assert def_claim.claim_type == "definition"
    assert def_claim.is_canonical is False

    # 2. Rule unit referencing the defined term
    rule_text = "To receive a full refund, returned items must be in like-new condition."
    rule_unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://policies/returns.md",
        source_id="src_policy_01",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content=rule_text,
        normalized_content=rule_text,
        content_text=rule_text,
        locator={"page": 2, "line": 20},
        related_unit_ids=[def_unit.unit_id],
        relationships=[
            EvidenceRelationship(
                relation_type=StructuralRelationType.DEFINITION_APPLIES_TO,
                target_unit_id=def_unit.unit_id,
            )
        ],
    )

    rule_claims = DomainRuleExtractor.extract_from_unit(rule_unit)
    assert len(rule_claims) >= 1
    rule_claim = rule_claims[0]
    assert any("like-new condition" in d.lower() for d in rule_claim.definition_references)
    assert rule_claim.evidence_relationship_type == "definition_applies_to"
    assert def_unit.unit_id in rule_claim.evidence_unit_ids
    assert rule_unit.unit_id in rule_claim.evidence_unit_ids


@pytest.mark.asyncio
async def test_table_derived_approval_limit():
    """
    Test 4: Table-derived approval limit.
    Grid binding preserves column header path, row key, cell value, and multi-evidence link to table parent.
    """
    table_parent_id = f"unit_table_{uuid.uuid4().hex[:8]}"
    row_unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://finance/delegation_of_authority.pdf",
        source_id="src_finance_01",
        source_version="v3.1",
        block_type="table_row",
        content_role=ContentRole.POLICY_RULE,
        raw_content="| Department Manager | Grade M2 | $50,000 |",
        normalized_content="Department Manager (Grade M2): Max Approval Limit $50,000",
        content_text="Department Manager (Grade M2): Max Approval Limit $50,000",
        parent_id=table_parent_id,
        structured_data={
            "columns": {
                "Role": "Department Manager",
                "Grade": "M2",
                "Max Approval Limit": "$50,000",
            },
            "table_type": "approval_matrix",
        },
        locator={"page": 4, "row_index": 3, "table_id": "tbl_authority_matrix"},
    )

    is_cand, strat, reason = CandidateDiscoveryEngine.is_candidate(row_unit)
    assert is_cand is True
    assert strat == ExtractionStrategyType.TABLE_AWARE

    claims = DeterministicSchemaExtractor.extract_from_unit(row_unit)
    assert len(claims) >= 1

    limit_claim = next((c for c in claims if "50,000" in str(c.object) or "50000" in str(c.object) or c.predicate == "has_max_approval_limit"), claims[0])
    assert limit_claim.table_binding is not None
    assert limit_claim.table_binding.table_id == "tbl_authority_matrix"
    assert "50,000" in limit_claim.table_binding.cell_value
    assert row_unit.unit_id in limit_claim.evidence_unit_ids
    assert table_parent_id in limit_claim.evidence_unit_ids
    assert limit_claim.evidence_relationship_type == "table_has_row"
    assert limit_claim.source_version == "v3.1"


@pytest.mark.asyncio
async def test_nested_json_derived_policy_fact():
    """
    Test 5: Nested JSON-derived policy fact.
    Nested JSON fields preserve exact path, data types, and schema invariants without location loss.
    """
    json_unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="cfg://vault/encryption_spec.json",
        source_id="src_vault_01",
        source_version="v1.0",
        block_type="structured_record",
        content_role=ContentRole.POLICY_RULE,
        raw_content='{"security": {"encryption": {"at_rest": {"algorithm": "AES-256-GCM", "fips_compliant": true}}}}',
        normalized_content="Security configuration at rest: AES-256-GCM, FIPS compliant",
        content_text="Security configuration at rest: AES-256-GCM, FIPS compliant",
        structured_data={
            "raw_record": {
                "security.encryption.at_rest.algorithm": "AES-256-GCM",
                "security.encryption.at_rest.fips_compliant": True,
            },
            "flattened_fields": {
                "security.encryption.at_rest.algorithm": "AES-256-GCM",
                "security.encryption.at_rest.fips_compliant": True,
            },
        },
        locator={"database": "Vault", "container": "SecurityConfig", "record_id": "cfg_01"},
    )

    claims = DeterministicSchemaExtractor.extract_from_unit(json_unit)
    assert len(claims) >= 2

    algo_claim = next(c for c in claims if "AES-256-GCM" in str(c.object))
    assert algo_claim.subject == "Vault.SecurityConfig#cfg_01"
    assert "algorithm" in algo_claim.predicate
    assert algo_claim.object == "AES-256-GCM"
    assert algo_claim.extraction_strategy == ExtractionStrategyType.DETERMINISTIC_SCHEMA
    assert json_unit.unit_id in algo_claim.evidence_unit_ids


@pytest.mark.asyncio
async def test_database_field_derived_fact():
    """
    Test 6: Database field-derived fact.
    Database records extract all fields, retain primary key context, and link parent-child relationships.
    """
    parent_table_id = f"unit_db_tbl_{uuid.uuid4().hex[:8]}"
    db_unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="postgres://compliance/tenant_configs/tenant_99",
        source_id="src_pg_01",
        source_version="v2.5",
        block_type="database_record",
        content_role=ContentRole.POLICY_RULE,
        raw_content='{"account_id": "act_889", "tier": "Enterprise", "retention_days": 365, "mfa_required": true}',
        normalized_content="Tenant 99 config: tier Enterprise, retention 365 days, MFA required",
        content_text="Tenant 99 config: tier Enterprise, retention 365 days, MFA required",
        parent_id=parent_table_id,
        structured_data={
            "raw_record": {
                "account_id": "act_889",
                "tier": "Enterprise",
                "retention_days": 365,
                "mfa_required": True,
            },
            "flattened_fields": {
                "account_id": "act_889",
                "tier": "Enterprise",
                "retention_days": 365,
                "mfa_required": True,
            },
        },
        locator={"database": "compliance", "container": "tenant_configs", "record_id": "tenant_99"},
    )

    claims = DeterministicSchemaExtractor.extract_from_unit(db_unit)
    assert len(claims) >= 3

    retention_claim = next(c for c in claims if "365" in str(c.object))
    assert retention_claim.subject == "compliance.tenant_configs#tenant_99"
    assert "retention_days" in retention_claim.predicate
    assert retention_claim.object == "365"
    assert db_unit.unit_id in retention_claim.evidence_unit_ids
    assert parent_table_id in retention_claim.evidence_unit_ids
    assert retention_claim.evidence_relationship_type == "record_has_field"


@pytest.mark.asyncio
async def test_chat_message_factual_assertion():
    """
    Test 7: Chat message containing a factual assertion.
    Conversational messages extract factual governance constraints, speaker entity, and temporal scope.
    """
    msg_text = "Production deployment window is strictly limited to Sundays between 02:00 and 04:00 UTC."
    msg_unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="slack://engineering/c-ops/msg_99182",
        source_id="src_slack_01",
        source_version="v1.0",
        block_type="chat_message",
        content_role=ContentRole.COMMUNICATION,
        raw_content=msg_text,
        normalized_content=msg_text,
        content_text=msg_text,
        structured_data={"speaker": "OpsLead", "channel": "#ops-deployments"},
        locator={"channel": "#ops-deployments", "speaker": "OpsLead", "timestamp": "2026-11-01T10:00:00Z"},
    )

    is_cand, strat, reason = CandidateDiscoveryEngine.is_candidate(msg_unit)
    assert is_cand is True

    claims = DomainRuleExtractor.extract_from_unit(msg_unit)
    assert len(claims) >= 1

    claim = claims[0]
    assert "production deployment window" in claim.subject.lower()
    assert "limited" in claim.predicate.lower()
    assert "02:00" in claim.object.lower() and "04:00" in claim.object.lower()
    assert claim.modality in ("MUST", "REQUIRED")
    assert claim.entity_scope == "OpsLead"
    assert claim.temporal_scope is not None
    assert "sundays" in claim.temporal_scope.lower() or "02:00" in claim.temporal_scope.lower()
    assert msg_unit.unit_id in claim.evidence_unit_ids


@pytest.mark.asyncio
async def test_duplicate_claims_from_different_locations():
    """
    Test 8: Duplicate claims from different source locations.
    Exact duplicate candidates across locations must be tracked without deleting separate evidence provenance.
    """
    policy_text = "All data stores must enforce encryption at rest."

    # Occurrence on Page 1
    unit_p1 = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://infosec/security_handbook.pdf",
        source_id="src_infosec_01",
        source_version="v1.0",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content=policy_text,
        normalized_content=policy_text,
        content_text=policy_text,
        locator={"page": 1, "line": 15},
    )

    # Occurrence on Page 5
    unit_p5 = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://infosec/security_handbook.pdf",
        source_id="src_infosec_01",
        source_version="v1.0",
        block_type="paragraph",
        content_role=ContentRole.POLICY_RULE,
        raw_content=policy_text,
        normalized_content=policy_text,
        content_text=policy_text,
        locator={"page": 5, "line": 80},
    )

    claims_p1 = DomainRuleExtractor.extract_from_unit(unit_p1)
    claims_p5 = DomainRuleExtractor.extract_from_unit(unit_p5)

    assert len(claims_p1) >= 1
    assert len(claims_p5) >= 1

    c1 = claims_p1[0]
    c2 = claims_p5[0]

    # Run through non-destructive deduplication logic (from Step 5)
    candidates = [c1, c2]
    canonical_map = {}
    deduped = []

    for c in candidates:
        key = (
            (c.subject or "").strip().lower(),
            (c.predicate or "").strip().lower(),
            str(c.object or "").strip().lower(),
            str(c.modality or "").strip().upper(),
            str(c.source_version or "").strip().lower(),
        )
        if key not in canonical_map:
            canonical_map[key] = c
            deduped.append(c)
        else:
            existing = canonical_map[key]
            c.is_duplicate = True
            c.duplicate_of = existing.candidate_id
            existing.duplicate_occurrences.append({
                "candidate_id": c.candidate_id,
                "unit_id": c.unit_id,
                "evidence_id": c.evidence_id,
                "locator": c.locator,
            })
            if c.unit_id not in existing.evidence_unit_ids:
                existing.evidence_unit_ids.append(c.unit_id)

    # Deduped canonical list contains 1 primary claim
    assert len(deduped) == 1
    primary = deduped[0]
    # Primary has both evidence unit IDs linked
    assert unit_p1.unit_id in primary.evidence_unit_ids
    assert unit_p5.unit_id in primary.evidence_unit_ids
    # Duplicate occurrence is recorded with exact Page 5 locator, NOT deleted
    assert len(primary.duplicate_occurrences) == 1
    assert primary.duplicate_occurrences[0]["unit_id"] == unit_p5.unit_id
    assert primary.duplicate_occurrences[0]["locator"]["page"] == 5
    assert c2.is_duplicate is True
    assert c2.duplicate_of == primary.candidate_id


@pytest.mark.asyncio
async def test_contradictory_claims_from_different_versions():
    """
    Test 9: Contradictory claims from different versions.
    Claims with different values or from different source versions must remain distinct, never merged.
    """
    # Version 1.0: 14 days
    text_v1 = "Refund window is 14 days from purchase date."
    unit_v1 = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://policies/refund.md",
        source_id="src_policy_01",
        source_version="v1.0",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content=text_v1,
        normalized_content=text_v1,
        content_text=text_v1,
        locator={"page": 1, "line": 10},
    )

    # Version 2.0: 30 days
    text_v2 = "Refund window is 30 days from purchase date."
    unit_v2 = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc://policies/refund.md",
        source_id="src_policy_01",
        source_version="v2.0",
        block_type="clause",
        content_role=ContentRole.POLICY_RULE,
        raw_content=text_v2,
        normalized_content=text_v2,
        content_text=text_v2,
        locator={"page": 1, "line": 10},
    )

    claims_v1 = DomainRuleExtractor.extract_from_unit(unit_v1)
    claims_v2 = DomainRuleExtractor.extract_from_unit(unit_v2)

    assert len(claims_v1) >= 1
    assert len(claims_v2) >= 1

    c1 = claims_v1[0]
    c2 = claims_v2[0]

    # Verify both preserved their distinct values and versions
    assert "14" in str(c1.object) or "14" in str(c1.temporal_scope)
    assert "30" in str(c2.object) or "30" in str(c2.temporal_scope)
    assert c1.source_version == "v1.0"
    assert c2.source_version == "v2.0"

    # Deduplication must NOT merge them
    candidates = [c1, c2]
    canonical_map = {}
    deduped = []

    for c in candidates:
        key = (
            (c.subject or "").strip().lower(),
            (c.predicate or "").strip().lower(),
            str(c.object or "").strip().lower(),
            str(c.modality or "").strip().upper(),
            str(c.source_version or "").strip().lower(),
        )
        if key not in canonical_map:
            canonical_map[key] = c
            deduped.append(c)

    # Must retain BOTH claims as distinct candidates for Layer 6 conflict detection
    assert len(deduped) == 2
    assert any(c.source_version == "v1.0" for c in deduped)
    assert any(c.source_version == "v2.0" for c in deduped)
