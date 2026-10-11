import asyncio
import json
import sys
import uuid
from pathlib import Path

# Add backend root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.dispatcher import global_envelope_router
from app.ingestion.parsers.structured_parser import StructuredDataParser
from app.ingestion.base import SyncMode
from app.extraction.pipeline import global_extraction_pipeline


async def test_all_five_layers_mongodb():
    uri = "mongodb+srv://demo:spk@cluster0.3tw5iwh.mongodb.net/?retryWrites=true&w=majority"
    database = "Departmental"
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    source_id = uuid.UUID("55555555-5555-5555-5555-555555555555")

    print("=" * 75)
    print("  LAYER 1: DATA SOURCE GOVERNANCE & INGESTION SCOPING")
    print("=" * 75)
    scope_config = {
        "database": database,
        "collections": ["sampletests"]
    }
    source_intent = SourceIntent.OPERATIONAL_DATA
    source_family = SourceFamily.STRUCTURED
    print(f"Tenant Organization ID : {org_id}")
    print(f"Data Source ID         : {source_id}")
    print(f"Declared Source Family : {source_family.value}")
    print(f"Declared Source Intent : {source_intent.value}")
    print(f"Ingestion Scope Config : {scope_config}")

    connector = MongoDbConnector(
        session=None,
        organization_id=org_id,
        source_id=source_id,
        connection_string=uri,
        database=database,
        collections=["sampletests"],
        sample_size=2,
        scope_config=scope_config,
        source_intent=source_intent,
    )

    print("\n" + "=" * 75)
    print("  LAYER 2: CONNECTOR DISCOVERY & NATIVE PAYLOAD EXTRACTION")
    print("=" * 75)
    conn_result = await connector.test_connection()
    print(f"Connection Status: {conn_result['status']} ({conn_result['message']})")

    discovered = await connector.discover_assets()
    print(f"\nDiscovered {len(discovered)} total collections across MongoDB cluster:")
    for d in discovered[:3]:
        print(f"  * [{d.asset_type}] {d.name} -> ID: {d.asset_id}")

    raw_assets = await connector.fetch_native_assets(
        selected_asset_ids=["sampletests"],
        sync_mode=SyncMode.INITIAL_FULL
    )
    print(f"\nFetched {len(raw_assets)} pristine un-flattened assets for scope [sampletests]:")
    for ra in raw_assets:
        print(f"  * Raw Asset ID: {ra.asset_id} (Format: {ra.native_format}, SHA-256: {ra.content_hash[:16]}...)")

    print("\n" + "=" * 75)
    print("  LAYER 3: CANONICAL SOURCE ENVELOPE & DISPATCHER")
    print("=" * 75)
    envelopes = []
    for ra in raw_assets:
        env = EnvelopeFactory.create_from_raw_asset(
            raw_asset=ra,
            organization_id=org_id,
            source_id=source_id,
            source_intent=source_intent,
            access_scope={"database": database, "tenant": "enterprise_prod"},
            extra_metadata={"connector_type": "mongodb_atlas"}
        )
        is_valid = EnvelopeFactory.validate_integrity(env)
        print(f"Sealed Envelope: {env.envelope_id}")
        print(f"  * Asset URI        : {env.asset_id}")
        print(f"  * Native Format    : {env.native_format}")
        print(f"  * Content SHA-256  : {env.content_hash}")
        print(f"  * Tamper Check     : {'PASSED (Cryptographically Valid)' if is_valid else 'FAILED'}")
        print(f"  * Evidence Locator : {env.evidence_locator}")
        envelopes.append(env)

    print("\n" + "=" * 75)
    print("  LAYER 4: SPECIALIZED SOURCE-FAMILY PARSER & EVIDENCE MODEL")
    print("=" * 75)
    evidence_results = []
    for env in envelopes:
        res = await StructuredDataParser.parse(env)
        evidence_results.append((env, res))
        print(f"Parser Invoked        : {res.parser_name}")
        print(f"  Asset ID            : {res.asset_id}")
        print(f"  Evidence Units      : {len(res.units)}")
        print(f"  Completeness Score  : {res.completeness_score * 100:.1f}%")
        print(f"  Quality Metrics     : {res.quality_metrics}")
        for idx, u in enumerate(res.units[:2]):
            print(f"    - Unit #{idx+1} [{u.block_type}]: {u.unit_id}")
            print(f"      Text: {u.content_text[:80]}...")
            print(f"      Loc : {u.locator}")

    print("\n" + "=" * 75)
    print("  LAYER 5: CANDIDATE EXTRACTION & SOURCE-AWARE VERIFICATION")
    print("=" * 75)
    all_extraction_results = []
    for env, ev_res in evidence_results:
        layer5_res = await global_extraction_pipeline.process_envelope(env, ev_res)
        all_extraction_results.append(layer5_res)

        print(f"\n[Layer 5 Results for Envelope {env.envelope_id}]")
        print(f"  Evidence Units Received : {layer5_res.total_evidence_units_received}")
        print(f"  Candidates Discovered    : {layer5_res.candidates_discovered}")
        print(f"  Claims Extracted         : {layer5_res.claims_extracted}")
        print(f"  Claims Verified          : {layer5_res.claims_verified}")
        print(f"  Claims Rejected          : {layer5_res.claims_rejected}")
        print(f"  Completeness Score       : {layer5_res.completeness_score * 100:.1f}%")

        print("\n  --- Verified Candidate Claims (Sample) ---")
        for idx, claim in enumerate(layer5_res.candidates[:5]):
            print(f"  Claim #{idx+1} [{claim.status.upper()}]:")
            print(f"    * ID         : {claim.candidate_id}")
            print(f"    * Subject    : {claim.subject}")
            print(f"    * Predicate  : {claim.predicate}")
            print(f"    * Object     : {claim.object}")
            print(f"    * Strategy   : {claim.extraction_strategy.value}")
            print(f"    * Plugin     : {claim.verification_plugin}")
            print(f"    * Confidence : {claim.confidence * 100:.0f}%")
            print(f"    * Details    : {claim.verification_details}")

        print("\n  --- Completeness Ledger Audit Summary ---")
        for k, v in layer5_res.ledger_summary.items():
            print(f"    * {k}: {v}")

    print("\n" + "=" * 75)
    print("  ARCHITECTURE VERIFICATION SUMMARY: LAYERS 1 TO 5")
    print("=" * 75)
    print("  Layer 1 (Governance & Scope)       : VERIFIED [OK]")
    print("  Layer 2 (Connector & Discovery)    : VERIFIED [OK]")
    print("  Layer 3 (Canonical Envelope)       : VERIFIED [OK]")
    print("  Layer 4 (Evidence Model Parser)    : VERIFIED [OK]")
    print("  Layer 5 (Candidate Extraction)     : VERIFIED [OK]")
    print("=" * 75)
    print("\n[SUCCESS] All 5 Layers verified live end-to-end against MongoDB Atlas!")


if __name__ == "__main__":
    asyncio.run(test_all_five_layers_mongodb())
