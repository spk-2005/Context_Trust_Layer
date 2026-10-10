import asyncio
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.connectors.mongodb_connector import MongoDbConnector
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.dispatcher import global_envelope_router
from app.ingestion.base import SyncMode

async def test_all_three_layers():
    uri = "mongodb+srv://demo:spk@cluster0.3tw5iwh.mongodb.net/?retryWrites=true&w=majority"
    database = "Departmental"
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    source_id = uuid.UUID("44444444-4444-4444-4444-444444444444")

    print("===============================================================")
    print("  LAYER 1: DATA SOURCE GOVERNANCE & INGESTION SCOPING")
    print("===============================================================")
    scope_config = {
        "database": database,
        "collections": ["sampletests"]
    }
    source_intent = SourceIntent.OPERATIONAL_DATA
    source_family = SourceFamily.STRUCTURED
    print(f"Tenant Organization ID: {org_id}")
    print(f"Data Source ID:        {source_id}")
    print(f"Declared Source Family: {source_family.value}")
    print(f"Declared Source Intent: {source_intent.value}")
    print(f"Ingestion Scope:        {scope_config}")

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

    print("\n===============================================================")
    print("  LAYER 2: CONNECTOR DISCOVERY & NATIVE EXTRACTION")
    print("===============================================================")
    conn_result = await connector.test_connection()
    print(f"Connection Status: {conn_result['status']} ({conn_result['message']})")
    
    discovered = await connector.discover_assets()
    print(f"Discovered {len(discovered)} total collections across cluster:")
    for d in discovered[:3]:
        print(f"  - {d.name} -> ID: {d.asset_id}")
    if len(discovered) > 3:
        print(f"  ... and {len(discovered) - 3} more collections.")

    raw_assets = await connector.fetch_native_assets(
        selected_asset_ids=["sampletests"],
        sync_mode=SyncMode.INITIAL_FULL
    )
    print(f"\nFetched {len(raw_assets)} pristine un-flattened assets for scope [sampletests]:")
    for ra in raw_assets:
        print(f"  - Raw Asset: {ra.asset_id} (Format: {ra.native_format}, Hash: {ra.content_hash[:16]}...)")

    print("\n===============================================================")
    print("  LAYER 3: CANONICAL SOURCE ENVELOPE & DISPATCHER")
    print("===============================================================")
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
        print(f"  - Asset URI:       {env.asset_id}")
        print(f"  - Tenant ID:       {env.organization_id}")
        print(f"  - Native Format:   {env.native_format}")
        print(f"  - Content SHA-256: {env.content_hash}")
        print(f"  - Tamper Check:    {'PASSED (Valid)' if is_valid else 'FAILED'}")
        print(f"  - Evidence Loc:    {env.evidence_locator}")
        envelopes.append(env)

    print("\n--- Layer 3 Type Detection & Routing Matrix ---")
    dispatch_results = await global_envelope_router.batch_dispatch(envelopes)
    
    print(json.dumps(dispatch_results, indent=2))

    print("\n--- Layer 3 Telemetry Metrics ---")
    print(json.dumps(global_envelope_router.get_telemetry(), indent=2))

if __name__ == "__main__":
    asyncio.run(test_all_three_layers())
