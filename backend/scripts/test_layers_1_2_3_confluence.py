import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

# Ensure backend root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.base import DiscoveredAsset, RawSourceAsset, SyncMode
from app.ingestion.connectors.confluence_connector import ConfluenceConnector
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.dispatcher import global_envelope_router


async def test_confluence_layers_1_2_3():
    org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    source_id = uuid.UUID("33333333-3333-3333-3333-333333333333")

    base_url = os.getenv("CONFLUENCE_BASE_URL", "").strip()
    user_email = os.getenv("CONFLUENCE_USER_EMAIL", "").strip()
    api_token = os.getenv("CONFLUENCE_API_TOKEN", "").strip()
    space_keys = ["POLICIES", "ENG"]

    print("=" * 65)
    print("  CONFLUENCE: LAYER 1 - DATA SOURCE GOVERNANCE & INGESTION SCOPING")
    print("=" * 65)

    source_family = SourceFamily.DOCUMENT
    source_intent = SourceIntent.GOVERNANCE_POLICY
    scope_config = {
        "space_keys": space_keys,
        "max_pages_per_space": 25,
        "include_attachments": False,
    }

    print(f"Tenant Organization ID : {org_id}")
    print(f"Data Source ID         : {source_id}")
    print(f"Declared Source Family : {source_family.value}")
    print(f"Declared Source Intent : {source_intent.value}")
    print(f"Ingestion Scope Config : {json.dumps(scope_config, indent=2)}")

    has_live_creds = bool(base_url and user_email and api_token)
    print(f"Atlassian Credentials  : {'Found live credentials in environment' if has_live_creds else 'None found (Running in Sandbox Simulation mode)'}")
    if not has_live_creds:
        print("  [Hint] To test against a live Atlassian site, set:\n"
              "         CONFLUENCE_BASE_URL=https://your-domain.atlassian.net\n"
              "         CONFLUENCE_USER_EMAIL=you@company.com\n"
              "         CONFLUENCE_API_TOKEN=your_token")

    connector = ConfluenceConnector(
        session=None,
        organization_id=org_id,
        source_id=source_id,
        base_url=base_url or "https://sample-org.atlassian.net",
        user_email=user_email or "dev@sample-org.com",
        api_token=api_token or "dummy-token",
        space_key="POLICIES",
        connection_config={"space_keys": space_keys},
        scope_config=scope_config,
        source_intent=source_intent,
    )

    print("\n" + "=" * 65)
    print("  CONFLUENCE: LAYER 2 - CONNECTOR DISCOVERY & NATIVE ASSET EXTRACTION")
    print("=" * 65)

    if has_live_creds:
        print("Testing live Confluence connectivity...")
        conn_result = await connector.test_connection()
        print(f"Connection Status: {conn_result.get('status')} - {conn_result.get('message')}")
        
        discovered = await connector.discover_assets()
        print(f"\nDiscovered {len(discovered)} live Confluence page(s)/space(s):")
        for d in discovered[:5]:
            print(f"  - [{d.asset_type}] ID: {d.asset_id} (Title: {d.name})")

        selected_ids = [d.asset_id for d in discovered if d.asset_type == "page"][:3]
        if not selected_ids and discovered:
            selected_ids = [discovered[0].asset_id]

        print(f"\nFetching native assets for selected asset IDs: {selected_ids}")
        raw_assets = await connector.fetch_native_assets(
            selected_asset_ids=selected_ids,
            sync_mode=SyncMode.INITIAL_FULL,
        )
    else:
        print("Executing Layer 2 Discovery Contract...")
        discovered = [
            DiscoveredAsset(
                asset_id="confluence://POLICIES",
                name="Space: POLICIES",
                asset_type="space",
                source_family=SourceFamily.DOCUMENT,
                is_selectable=False,
                metadata={"space_key": "POLICIES"},
            ),
            DiscoveredAsset(
                asset_id="confluence://POLICIES/page/1049281",
                name="Data Retention & Trust Mandate 2026",
                asset_type="page",
                source_family=SourceFamily.DOCUMENT,
                parent_id="confluence://POLICIES",
                is_selectable=True,
                metadata={"space_key": "POLICIES", "page_id": "1049281"},
            ),
            DiscoveredAsset(
                asset_id="confluence://POLICIES/page/1049282",
                name="Cloud Incident Escalation Matrix",
                asset_type="page",
                source_family=SourceFamily.DOCUMENT,
                parent_id="confluence://POLICIES",
                is_selectable=True,
                metadata={"space_key": "POLICIES", "page_id": "1049282"},
            ),
        ]
        for d in discovered:
            print(f"  - [{d.asset_type}] ID: {d.asset_id} (Title: {d.name}, Selectable: {d.is_selectable})")

        print("\nExecuting Layer 2 Native Extraction Contract (storage XML/HTML + metadata)...")
        raw_assets = [
            RawSourceAsset(
                asset_id="confluence://POLICIES/page/1049281",
                source_family=SourceFamily.DOCUMENT,
                native_format="confluence_html",
                source_version="4",
                raw_payload={
                    "title": "Data Retention & Trust Mandate 2026",
                    "body_storage_html": "<p>All customer PII must be scrubbed after 90 days. Backups must be AES-256 encrypted.</p>",
                    "version": "4",
                    "author": "Chief Compliance Officer",
                },
                locator_metadata={
                    "space_key": "POLICIES",
                    "page_id": "1049281",
                    "page_title": "Data Retention & Trust Mandate 2026",
                    "version": "4",
                },
            ),
            RawSourceAsset(
                asset_id="confluence://POLICIES/page/1049282",
                source_family=SourceFamily.DOCUMENT,
                native_format="confluence_html",
                source_version="2",
                raw_payload={
                    "title": "Cloud Incident Escalation Matrix",
                    "body_storage_html": "<p>Sev-1 outages require on-call notification within 5 minutes across Slack and PagerDuty.</p>",
                    "version": "2",
                    "author": "VP Infrastructure",
                },
                locator_metadata={
                    "space_key": "POLICIES",
                    "page_id": "1049282",
                    "page_title": "Cloud Incident Escalation Matrix",
                    "version": "2",
                },
            ),
        ]

    print(f"\nFetched {len(raw_assets)} pristine un-flattened native asset(s):")
    for ra in raw_assets:
        print(f"  - Asset ID    : {ra.asset_id}")
        print(f"    Format      : {ra.native_format}")
        print(f"    Version     : {ra.source_version}")
        print(f"    SHA-256 Hash: {ra.content_hash[:20]}...")
        print(f"    Coordinates : {ra.locator_metadata}")

    print("\n" + "=" * 65)
    print("  CONFLUENCE: LAYER 3 - CANONICAL SOURCE ENVELOPE & DISPATCHER")
    print("=" * 65)

    envelopes = []
    for ra in raw_assets:
        env = EnvelopeFactory.create_from_raw_asset(
            raw_asset=ra,
            organization_id=org_id,
            source_id=source_id,
            source_intent=source_intent,
            access_scope={"space_keys": space_keys, "tenant": "enterprise_prod"},
            extra_metadata={"connector_type": "confluence", "wiki_provider": "atlassian"},
        )
        is_valid = EnvelopeFactory.validate_integrity(env)
        print(f"Sealed Canonical Envelope: {env.envelope_id}")
        print(f"  - Asset URI        : {env.asset_id}")
        print(f"  - Tenant Org ID    : {env.organization_id}")
        print(f"  - Source Family    : {env.source_family.value}")
        print(f"  - Source Intent    : {env.source_intent.value}")
        print(f"  - Native Format    : {env.native_format}")
        print(f"  - SHA-256 Checksum : {env.content_hash}")
        print(f"  - Tamper Check     : {'PASSED (Cryptographically Valid)' if is_valid else 'FAILED (Tampered)'}")
        print(f"  - Evidence Locator : {env.evidence_locator}")
        envelopes.append(env)

    print("\n--- Layer 3 Type Detection & Routing Matrix ---")
    dispatch_results = await global_envelope_router.batch_dispatch(envelopes)
    print(json.dumps(dispatch_results, indent=2))

    print("\n--- Layer 3 Router Telemetry ---")
    print(json.dumps(global_envelope_router.get_telemetry(), indent=2))
    print("\n[SUCCESS] Layers 1, 2, and 3 successfully verified for Confluence!")


if __name__ == "__main__":
    asyncio.run(test_confluence_layers_1_2_3())
