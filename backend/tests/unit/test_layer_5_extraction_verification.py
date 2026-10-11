"""
Unit tests for Layer 5: Candidate Extraction & Source-Aware Verification.
Validates:
1. Candidate Discovery Engine (modal policies, DB invariants, decisions)
2. Extraction Strategies (Deterministic Schema, Domain Rules, LLM Fallback)
3. Source-Aware Verification Plugins (Text/Document, Database/Record, API/JSON, Formula/BI)
4. Completeness Ledger (Auditing, unit-level tracking, completeness score)
5. Layer 5 End-to-End Extraction Pipeline
"""

import uuid
import pytest
from datetime import datetime, timezone

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import (
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
)
from app.extraction.models import (
    CandidateClaim,
    ExtractionStrategyType,
    CompletenessLedgerRecord,
    Layer5ExtractionResult,
)
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.extractors.llm_extractor import LLMSemanticExtractor
from app.extraction.plugins import (
    TextDocumentVerificationPlugin,
    DatabaseRecordVerificationPlugin,
    ApiJsonVerificationPlugin,
    FormulaBiVerificationPlugin,
    VerificationPluginManager,
)
from app.extraction.completeness_ledger import CompletenessLedger
from app.extraction.pipeline import Layer5ExtractionPipeline, global_extraction_pipeline


def _create_sample_envelope(family: SourceFamily, raw_payload: any, asset_id: str = "test-asset-1") -> CanonicalSourceEnvelope:
    return CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id=asset_id,
        source_family=family,
        source_intent=SourceIntent.GOVERNANCE_POLICY if family == SourceFamily.DOCUMENT else SourceIntent.OPERATIONAL_OBSERVABILITY,
        native_format="json" if isinstance(raw_payload, (dict, list)) else "markdown",
        source_version="v1.0",
        content_hash="hash_123",
        raw_payload=raw_payload,
        locator_metadata={"test": True},
    )


# =========================================================================
# 1. Candidate Discovery Tests
# =========================================================================

def test_candidate_discovery_modal_clauses():
    """Detects normative modal operators (must, shall, required) in text."""
    env_id = uuid.uuid4()
    unit_normative = ParsedEvidenceUnit.create(
        envelope_id=env_id,
        asset_id="policy.md",
        block_type="clause",
        content_text="All database credentials must be rotated every 90 days without exception.",
    )
    is_candidate, strategy, reason = CandidateDiscoveryEngine.is_candidate(unit_normative)
    assert is_candidate is True
    assert strategy in (ExtractionStrategyType.DOMAIN_RULES, ExtractionStrategyType.LLM_SEMANTIC)
    assert "modal" in reason.lower()

    unit_informative = ParsedEvidenceUnit.create(
        envelope_id=env_id,
        asset_id="notes.txt",
        block_type="paragraph",
        content_text="Good morning team, let us have a productive day ahead.",
    )
    is_cand_2, _, reason_2 = CandidateDiscoveryEngine.is_candidate(unit_informative)
    assert is_cand_2 is False
    assert "normative" in reason_2.lower()


def test_candidate_discovery_database_invariants():
    """Detects database records and schema definitions for deterministic extraction."""
    env_id = uuid.uuid4()
    unit_db = ParsedEvidenceUnit.create(
        envelope_id=env_id,
        asset_id="mongodb://cluster/db/coll",
        block_type="database_record",
        content_text='{"_id": "item1", "status": "active", "encryption": "AES-256"}',
        structured_data={
            "raw_record": {"_id": "item1", "status": "active", "encryption": "AES-256"},
            "flattened_fields": {"_id": "item1", "status": "active", "encryption": "AES-256"},
        },
    )
    is_cand, strategy, reason = CandidateDiscoveryEngine.is_candidate(unit_db)
    assert is_cand is True
    assert strategy == ExtractionStrategyType.DETERMINISTIC_SCHEMA
    assert "database" in reason.lower() or "structured" in reason.lower()


# =========================================================================
# 2. Extractor Tests
# =========================================================================

def test_deterministic_schema_extractor_db_record():
    """Deterministic extractor produces zero-hallucination structured invariants with exact values."""
    envelope_id = uuid.uuid4()
    unit = ParsedEvidenceUnit.create(
        envelope_id=envelope_id,
        asset_id="mongodb://prod/auth/users",
        block_type="database_record",
        content_text='{"_id": "usr_99", "status": "active", "role": "admin"}',
        structured_data={
            "raw_record": {"_id": "usr_99", "status": "active", "role": "admin"},
            "flattened_fields": {"_id": "usr_99", "status": "active", "role": "admin"},
        },
        locator={
            "container": "users",
            "primary_key_field": "_id",
            "record_id": "usr_99",
        },
    )

    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    assert len(claims) >= 2

    predicates = [c.predicate for c in claims]
    assert "has_status" in predicates or "has_role" in predicates or "status" in predicates
    for claim in claims:
        assert claim.envelope_id == envelope_id
        assert claim.extraction_strategy == ExtractionStrategyType.DETERMINISTIC_SCHEMA
        assert claim.confidence == 1.0
        assert claim.status == "candidate"


def test_domain_rule_extractor_modal_policies():
    """Extracts claims from normative text sentences using domain rules."""
    envelope_id = uuid.uuid4()
    unit = ParsedEvidenceUnit.create(
        envelope_id=envelope_id,
        asset_id="security_policy.md",
        block_type="clause",
        content_text="Root API keys must be disabled across all staging environments. Production access requires dual authorization.",
    )

    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1
    claim = claims[0]
    assert "Root API keys" in claim.subject or "Production access" in claim.subject or "API" in claim.claim_text
    assert claim.modal_operator in ["must", "requires", "shall", "should"]
    assert claim.extraction_strategy == ExtractionStrategyType.DOMAIN_RULES


@pytest.mark.asyncio
async def test_llm_extractor_graceful_fallback():
    """LLM semantic extractor gracefully falls back to Domain Rules when offline or encountering errors."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc.md",
        block_type="clause",
        content_text="Service accounts must not possess organization-wide owner permissions.",
    )

    extractor = LLMSemanticExtractor()
    claims = await extractor.extract_from_unit(unit)
    assert len(claims) >= 1
    assert "Service accounts" in claims[0].subject or "Service accounts" in claims[0].claim_text


# =========================================================================
# 3. Source-Aware Verification Plugin Tests
# =========================================================================

def test_text_document_verification_plugin():
    """Verifies that authentic text quotes pass and fabricated text quotes fail."""
    raw_document = "# Security Architecture\nAll API tokens must expire after 24 hours of inactivity."
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="doc.md",
        block_type="clause",
        content_text="All API tokens must expire after 24 hours of inactivity.",
    )

    valid_claim = CandidateClaim.create(
        envelope_id=unit.envelope_id,
        unit_id=unit.unit_id,
        asset_id=unit.asset_id,
        claim_text="API tokens expire after 24 hours",
        subject="API tokens",
        predicate="must expire",
        object_="after 24 hours",
        evidence_text_span="All API tokens must expire after 24 hours of inactivity.",
    )

    plugin = TextDocumentVerificationPlugin()
    is_valid, reason, details = plugin.verify(valid_claim, unit, raw_document)
    assert is_valid is True
    assert details.get("quote_grounded") is True

    # Fabricated quote test
    invalid_claim = CandidateClaim.create(
        envelope_id=unit.envelope_id,
        unit_id=unit.unit_id,
        asset_id=unit.asset_id,
        claim_text="Tokens never expire",
        subject="Tokens",
        predicate="never expire",
        object_="forever",
        evidence_text_span="Tokens are permanent and never expire indefinitely anywhere in cosmos.",
    )
    is_valid_inv, reason_inv, _ = plugin.verify(invalid_claim, unit, raw_document)
    assert is_valid_inv is False
    assert "not match" in reason_inv.lower() or "overlap" in reason_inv.lower()


def test_database_record_verification_plugin():
    """Verifies database primary key existence and typed value matches."""
    raw_mongo_doc = {
        "_id": "sec_policy_01",
        "tls_version": "1.3",
        "cipher": "ECDHE-RSA-AES256-GCM-SHA384",
    }
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="mongodb://cluster/policies/sec_policy_01",
        block_type="database_record",
        content_text=str(raw_mongo_doc),
        structured_data={
            "raw_record": raw_mongo_doc,
            "flattened_fields": {"tls_version": "1.3", "cipher": "ECDHE-RSA-AES256-GCM-SHA384"},
        },
        locator={
            "container": "policies",
            "record_id": "sec_policy_01",
        },
    )

    claim = CandidateClaim.create(
        envelope_id=unit.envelope_id,
        unit_id=unit.unit_id,
        asset_id=unit.asset_id,
        claim_text="tls_version is 1.3",
        subject="policies#sec_policy_01",
        predicate="has_tls_version",
        object_="1.3",
        evidence_text_span="tls_version: 1.3",
        structured_values={"tls_version": "1.3"},
        locator={"container": "policies", "record_id": "sec_policy_01", "field_path": "tls_version"},
    )

    plugin = DatabaseRecordVerificationPlugin()
    is_valid, reason, details = plugin.verify(claim, unit, raw_mongo_doc)
    assert is_valid is True
    assert details.get("record_id") == "sec_policy_01"
    assert details.get("native_value") == "1.3"


def test_api_json_and_formula_plugins():
    """Verifies JSON key path verification and formula lineage verification."""
    raw_json = {"key": "auth_endpoint", "value": "https://auth.internal/v1"}
    unit_json = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="https://api.internal/config",
        block_type="config_property",
        content_text=str(raw_json),
        structured_data=raw_json,
    )
    claim_json = CandidateClaim.create(
        envelope_id=unit_json.envelope_id,
        unit_id=unit_json.unit_id,
        asset_id=unit_json.asset_id,
        claim_text="Config key auth_endpoint is https://auth.internal/v1",
        subject="auth_endpoint",
        predicate="is",
        object_="https://auth.internal/v1",
        evidence_text_span="auth_endpoint: https://auth.internal/v1",
    )
    plugin_json = ApiJsonVerificationPlugin()
    is_valid, _, details_json = plugin_json.verify(claim_json, unit_json, raw_json)
    assert is_valid is True
    assert details_json.get("key") == "auth_endpoint"

    raw_formula = {"name": "mrr", "formula": "sum(sub_rev) * 12"}
    unit_formula = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="dbt://models/mrr.sql",
        block_type="metric_definition",
        content_text="mrr is computed as sum(sub_rev) * 12",
        structured_data=raw_formula,
    )
    claim_formula = CandidateClaim.create(
        envelope_id=unit_formula.envelope_id,
        unit_id=unit_formula.unit_id,
        asset_id=unit_formula.asset_id,
        claim_text="Metric mrr formula is sum(sub_rev) * 12",
        subject="mrr",
        predicate="defined_as",
        object_="sum(sub_rev) * 12",
        evidence_text_span="formula: sum(sub_rev) * 12",
    )
    plugin_f = FormulaBiVerificationPlugin()
    is_valid_f, _, details_f = plugin_f.verify(claim_formula, unit_formula, raw_formula)
    assert is_valid_f is True
    assert details_f.get("formula") == "sum(sub_rev) * 12"


# =========================================================================
# 4. Completeness Ledger Tests
# =========================================================================

def test_completeness_ledger_auditing():
    """Validates that CompletenessLedger accurately tracks every unit and calculates scores."""
    envelope_id = uuid.uuid4()
    ledger = CompletenessLedger(envelope_id, "test_doc.md")

    ledger.record_entry("u1", "clause", "verified", "domain_rules", "TextDocumentVerificationPlugin", True, 2)
    ledger.record_entry("u2", "paragraph", "skipped", "none", None, False, 0, "No normative pattern")
    ledger.record_entry("u3", "clause", "rejected", "llm_semantic", "TextDocumentVerificationPlugin", False, 1, "Fabricated evidence quote")

    summary = ledger.get_summary()
    assert summary["total_units_evaluated"] == 3
    assert summary["units_verified"] == 1
    assert summary["units_skipped"] == 1
    assert summary["units_rejected"] == 1
    assert summary["total_claims_generated"] == 3
    # Discovered = 2 (u1, u3). Both accounted for (1 verified + 1 rejected) => completeness = 1.0 (100%)
    assert summary["completeness_score"] == 1.0


# =========================================================================
# 5. End-to-End Layer 5 Pipeline Integration Test
# =========================================================================

@pytest.mark.asyncio
async def test_layer_5_pipeline_full_integration():
    """Executes full Layer 5 pipeline: candidate discovery, routing, verification, and ledger."""
    markdown_payload = """# Enterprise Auth Policy

## Section 1: Invariants
- Admin users must enforce multi-factor authentication.
- API keys shall be rotated every 30 days.

General informative text without any policy assertions.
"""
    envelope = _create_sample_envelope(SourceFamily.DOCUMENT, markdown_payload, "policy_doc_v1")

    evidence_result = ParsedEvidenceResult(
        envelope_id=envelope.envelope_id,
        asset_id=envelope.asset_id,
        source_family=SourceFamily.DOCUMENT,
        parser_name="DocumentParser",
        units=[
            ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                block_type="clause",
                content_text="Admin users must enforce multi-factor authentication.",
            ),
            ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                block_type="clause",
                content_text="API keys shall be rotated every 30 days.",
            ),
            ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                block_type="paragraph",
                content_text="General informative text without any policy assertions.",
            ),
        ],
    )

    pipeline = Layer5ExtractionPipeline()
    result = await pipeline.process_envelope(envelope, evidence_result)

    assert isinstance(result, Layer5ExtractionResult)
    assert result.total_evidence_units_received == 3
    assert result.candidates_discovered == 2  # unit 1 and 2
    assert result.claims_extracted >= 2
    assert result.claims_verified >= 2
    assert result.claims_rejected == 0
    assert result.completeness_score == 1.0

    # Ensure all claims have verification provenance
    for claim in result.candidates:
        assert claim.status == "verified"
        assert claim.verification_plugin == "TextDocumentVerificationPlugin"
        assert claim.verification_details["quote_grounded"] is True
