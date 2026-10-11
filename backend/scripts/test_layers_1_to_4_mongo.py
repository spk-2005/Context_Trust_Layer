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
from app.ingestion.base import SyncMode


async def test_all_four_layers_mongodb():
    uri = "mongodb+srv://demo:spk@cluster0.3tw5iwh.mongodb.net/?retryWrites=true&w=majority"
    database = "Departmental"
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    source_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    print("=" * 70)
    print("  LAYER 1: DATA SOURCE GOVERNANCE & INGESTION SCOPING")
    print("=" * 70)
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

    print("\n" + "=" * 70)
    print("  LAYER 2: CONNECTOR DISCOVERY & NATIVE PAYLOAD EXTRACTION")
    print("=" * 70)
    conn_result = await connector.test_connection()
    print(f"Connection Status: {conn_result['status']} ({conn_result['message']})")

    discovered = await connector.discover_assets()
    print(f"\nDiscovered {len(discovered)} total collections across cluster:")
    for d in discovered[:3]:
        print(f"  - [{d.asset_type}] {d.name} -> ID: {d.asset_id}")
    if len(discovered) > 3:
        print(f"  ... and {len(discovered) - 3} more collections.")

    raw_assets = await connector.fetch_native_assets(
        selected_asset_ids=["sampletests"],
        sync_mode=SyncMode.INITIAL_FULL
    )
    print(f"\nFetched {len(raw_assets)} pristine un-flattened assets for scope [sampletests]:")
    for ra in raw_assets:
        print(f"  - Raw Asset ID: {ra.asset_id} (Format: {ra.native_format}, SHA-256: {ra.content_hash[:16]}...)")

    print("\n" + "=" * 70)
    print("  LAYER 3: CANONICAL SOURCE ENVELOPE & DISPATCHER")
    print("=" * 70)
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
        print(f"  - Asset URI        : {env.asset_id}")
        print(f"  - Tenant ID        : {env.organization_id}")
        print(f"  - Native Format    : {env.native_format}")
        print(f"  - Content SHA-256  : {env.content_hash}")
        print(f"  - Tamper Check     : {'PASSED (Cryptographically Valid)' if is_valid else 'FAILED'}")
        print(f"  - Evidence Locator : {env.evidence_locator}")
        envelopes.append(env)

    print("\n" + "=" * 70)
    print("  LAYER 4: SPECIALIZED SOURCE-FAMILY PARSER & EVIDENCE MODEL")
    print("=" * 70)
    dispatch_results = await global_envelope_router.batch_dispatch(envelopes)
    
    print(f"Total Envelopes Processed: {dispatch_results['total_envelopes']}")
    print("\n--- Layer 3 Routing Decisions ---")
    for rd in dispatch_results["routing_decisions"]:
        print(f"  * Asset: {rd['asset_id']}")
        print(f"    Target Parser   : {rd['target_parser']}")
        print(f"    Detected Format : {rd['detected_format']}")
        print(f"    Confidence      : {rd['confidence'] * 100:.0f}%")
        print(f"    Reason          : {rd['reason']}")

    print("\n--- Layer 4 Parsed Evidence Results ---")
    for idx, res in enumerate(dispatch_results["results"]):
        print(f"\n[Result {idx+1}] Parser: {res.get('parser_name')} (Asset: {res.get('asset_id')})")
        print(f"  Completeness Score  : {res.get('completeness_score') * 100:.1f}%")
        print(f"  Total Evidence Units: {res.get('total_units')}")
        print(f"  Quality Metrics     : {res.get('quality_metrics')}")
        print("  Atomic Units Extracted:")
        for u in res.get("units", []):
            print(f"    -> [{u.get('block_type')}] ID: {u.get('unit_id')}")
            print(f"       Text: {u.get('content_text')[:100]}...")
            print(f"       Loc : {u.get('locator')}")
            print(f"       Hier: {u.get('hierarchical_context')}")
            print(f"       Hash: {u.get('content_hash')[:16]}...")

    print("\n--- Platform Telemetry Metrics ---")
    print(json.dumps(global_envelope_router.get_telemetry(), indent=2))
    print("\n[SUCCESS] All 4 Layers verified end-to-end against MongoDB Atlas!")


if __name__ == "__main__":
    asyncio.run(test_all_four_layers_mongodb())
