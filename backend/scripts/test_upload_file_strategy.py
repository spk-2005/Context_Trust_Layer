"""
Test Script: File Upload & Extraction Strategy Simulation in Document Explorer.
Uploads enterprise_cloud_security_v3.md to /v1/documents/upload-and-extract
and checks how the extraction strategy executes (auto fallback, rule extraction, and LLM).
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

# Add backend root to sys.path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.db.database import AsyncSessionLocal
from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.universal_file_parser import UniversalFileParser
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.strategy_router import StrategyRouter
from app.extraction.pipeline import global_extraction_pipeline
from app.ingestion.parsers.document_parser import DocumentParser


async def test_file_upload_and_strategy_selection():
    file_path = backend_root / "storage" / "uploads" / "66a7a901-35ec-43e6-bbf4-30dbedacd67d" / "enterprise_cloud_security_v3.md"
    assert file_path.exists(), f"File {file_path} not found"

    print("=" * 80)
    print("SIMULATING DOCUMENT EXPLORER TAB: FILE UPLOAD & STRATEGY SELECTION")
    print("=" * 80)
    print(f"File Name     : {file_path.name}")
    print(f"File Size     : {file_path.stat().st_size} bytes")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    print("\n--- File Content Preview ---")
    print(raw_text.strip())

    # Step 1: Universal Parsing
    print("\n[Step 1: Universal File Intake]")
    parsed_text = UniversalFileParser.parse_file(
        filename=file_path.name,
        raw_bytes=raw_text.encode("utf-8"),
        doc_title="Enterprise Cloud Security Policy (v3.0)",
    )
    print(f"Parsed Content Characters: {len(parsed_text)}")

    # Step 2: Canonical Envelope
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    source_id = uuid.UUID("44444444-4444-4444-4444-444444444444")
    envelope = EnvelopeFactory.create_from_file_upload(
        filename=file_path.name,
        raw_bytes=raw_text.encode("utf-8"),
        parsed_content=parsed_text,
        organization_id=org_id,
        source_id=source_id,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )
    print(f"Envelope Sealed: {envelope.envelope_id} (SHA-256: {envelope.content_hash[:16]}...)")

    # Step 3: Layer 4 AST Decomposition
    evidence_res = await DocumentParser.parse(envelope)
    print(f"Parsed {len(evidence_res.units)} atomic evidence units")

    # Step 4: Layer 5 Strategy Auto-Detection per Unit
    print("\n[Step 4: Layer 5 Strategy Auto-Detection]")
    for idx, unit in enumerate(evidence_res.units):
        is_candidate, strategy, reason = CandidateDiscoveryEngine.is_candidate(unit)
        status_label = "ELIGIBLE" if is_candidate else "SKIPPED"
        print(f"\nUnit #{idx+1} [{unit.block_type}] ({status_label}):")
        print(f"  Text     : '{unit.content_text.strip()}'")
        print(f"  Strategy : {strategy.value if strategy else 'None'}")
        print(f"  Reason   : {reason}")

    # Step 5: Full Extraction & Verification Pipeline
    print("\n[Step 5: Pipeline Execution with Graceful Auto-Selection]")
    extraction_result = await global_extraction_pipeline.process_envelope(envelope, evidence_res)
    print(f"  Candidates Discovered : {extraction_result.candidates_discovered}")
    print(f"  Claims Extracted      : {extraction_result.claims_extracted}")
    print(f"  Claims Verified       : {extraction_result.claims_verified}")
    print(f"  Completeness Score    : {extraction_result.completeness_score * 100:.1f}%")

    print("\n--- Extracted & Verified Claims ---")
    for claim in extraction_result.candidates:
        print(f"  * Claim ID   : {claim.candidate_id}")
        print(f"    Subject    : {claim.subject}")
        print(f"    Predicate  : {claim.predicate}")
        print(f"    Object     : {claim.object}")
        print(f"    Strategy   : {claim.extraction_strategy.value}")
        print(f"    Plugin     : {claim.verification_plugin}")
        print(f"    Confidence : {claim.confidence * 100:.0f}%")

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_file_upload_and_strategy_selection())
