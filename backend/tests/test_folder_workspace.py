import uuid
import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models.document import Document
from app.db.models.folder import Folder
from app.db.models.organization import Organization
from app.db.models.user import User
from app.main import app
from app.services.folder_service import FolderService


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
async def setup_test_org(db: AsyncSession):
    """Provisions a clean test organization and admin user."""
    org_id = uuid.uuid4()
    user_id = uuid.uuid4()

    org = Organization(
        id=org_id,
        name=f"Test Org {str(org_id)[:8]}",
        slug=f"test-org-{str(org_id)[:8]}",
    )
    db.add(org)
    await db.flush()

    user = User(
        id=user_id,
        organization_id=org_id,
        email=f"admin-{str(user_id)[:8]}@test.local",
        name="Test Admin",
        role="admin",
    )
    db.add(user)
    await db.commit()

    return {"org_id": org_id, "user_id": user_id}


@pytest.mark.asyncio
async def test_inbox_idempotency_and_uniqueness(setup_test_org, db: AsyncSession):
    """Verify each organization receives exactly one system Inbox, and provision is idempotent."""
    org_id = setup_test_org["org_id"]
    service = FolderService(db)

    # 1. Provision inbox
    inbox1 = await service.ensure_system_inbox(org_id)
    await db.commit()
    assert inbox1.is_system is True
    assert inbox1.depth == 0
    assert inbox1.name == "Inbox"

    # 2. Re-run provision: must return the exact same instance
    inbox2 = await service.ensure_system_inbox(org_id)
    assert inbox1.id == inbox2.id

    # 3. Direct DB attempt to insert second is_system=TRUE inbox must violate unique index
    dup_inbox = Folder(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Second Inbox",
        depth=0,
        is_system=True,
        folder_type="inbox",
    )
    db.add(dup_inbox)
    with pytest.raises(Exception):
        await db.commit()
    await db.rollback()


@pytest.mark.asyncio
async def test_prevent_inbox_deletion_and_rename(setup_test_org, client: AsyncClient, db: AsyncSession):
    """System Inbox cannot be renamed, moved, or deleted."""
    org_id = setup_test_org["org_id"]
    service = FolderService(db)
    inbox = await service.ensure_system_inbox(org_id)
    await db.commit()

    # 1. Rename Inbox -> HTTP 400
    res = await client.patch(
        f"/v1/folders/{inbox.id}",
        params={"organization_id": str(org_id)},
        json={"name": "Renamed Inbox"},
    )
    assert res.status_code == 400
    assert "System Inbox folder cannot be renamed" in res.json()["detail"]

    # 2. Delete Inbox -> HTTP 400
    del_res = await client.delete(
        f"/v1/folders/{inbox.id}",
        params={"organization_id": str(org_id)},
    )
    assert del_res.status_code == 400
    assert "System Inbox cannot be deleted" in del_res.json()["detail"]


@pytest.mark.asyncio
async def test_sibling_name_normalization_and_uniqueness(setup_test_org, client: AsyncClient):
    """Normalized trimmed case-insensitive name uniqueness enforced at root and under parent."""
    org_id = setup_test_org["org_id"]

    # 1. Create root folder "Legal"
    res1 = await client.post(
        "/v1/folders",
        params={"organization_id": str(org_id)},
        json={"name": "Legal"},
    )
    assert res1.status_code == 201
    legal_id = res1.json()["id"]

    # 2. Duplicate root "  legal  " -> HTTP 409 Conflict
    res2 = await client.post(
        "/v1/folders",
        params={"organization_id": str(org_id)},
        json={"name": "  legal  "},
    )
    assert res2.status_code == 409

    # 3. Create subfolder "Contracts" under Legal
    res3 = await client.post(
        "/v1/folders",
        params={"organization_id": str(org_id)},
        json={"name": "Contracts", "parent_id": legal_id},
    )
    assert res3.status_code == 201

    # 4. Duplicate subfolder under Legal -> HTTP 409
    res4 = await client.post(
        "/v1/folders",
        params={"organization_id": str(org_id)},
        json={"name": "  contracts  ", "parent_id": legal_id},
    )
    assert res4.status_code == 409

    # 5. Sibling in different parent -> 201 Allowed
    res5 = await client.post(
        "/v1/folders",
        params={"organization_id": str(org_id)},
        json={"name": "Contracts"},  # Root contracts
    )
    assert res5.status_code == 201


@pytest.mark.asyncio
async def test_depth_limit_enforcement(setup_test_org, client: AsyncClient):
    """Hierarchy allows depths 0 to 6 (7 levels); depth 7 is rejected."""
    org_id = setup_test_org["org_id"]

    current_parent_id = None
    for d in range(7):  # depths 0, 1, 2, 3, 4, 5, 6
        res = await client.post(
            "/v1/folders",
            params={"organization_id": str(org_id)},
            json={"name": f"Level_{d}", "parent_id": current_parent_id},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["depth"] == d
        current_parent_id = data["id"]

    # 8th level (depth 7) must fail
    res_overflow = await client.post(
        "/v1/folders",
        params={"organization_id": str(org_id)},
        json={"name": "Level_7_Overflow", "parent_id": current_parent_id},
    )
    assert res_overflow.status_code == 400
    assert "Depth limit exceeded" in res_overflow.json()["detail"]


@pytest.mark.asyncio
async def test_cycle_prevention_on_folder_move(setup_test_org, client: AsyncClient):
    """Moving a folder into itself or its own descendant is strictly prevented."""
    org_id = setup_test_org["org_id"]

    # Create A -> B -> C
    res_a = await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "Folder_A"})
    a_id = res_a.json()["id"]

    res_b = await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "Folder_B", "parent_id": a_id})
    b_id = res_b.json()["id"]

    res_c = await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "Folder_C", "parent_id": b_id})
    c_id = res_c.json()["id"]

    # 1. Move A into A -> HTTP 400
    mv_self = await client.post(
        f"/v1/folders/{a_id}/move",
        params={"organization_id": str(org_id)},
        json={"new_parent_id": a_id},
    )
    assert mv_self.status_code == 400

    # 2. Move A into C (grandchild) -> HTTP 400 Circular hierarchy detected
    mv_cycle = await client.post(
        f"/v1/folders/{a_id}/move",
        params={"organization_id": str(org_id)},
        json={"new_parent_id": c_id},
    )
    assert mv_cycle.status_code == 400
    assert "Circular hierarchy detected" in mv_cycle.json()["detail"]


@pytest.mark.asyncio
async def test_safe_move_depth_propagation(setup_test_org, client: AsyncClient):
    """Moving a subtree properly recalculates descendant depths atomically."""
    org_id = setup_test_org["org_id"]

    # Tree 1: Root_1 (depth 0) -> Sub_A (depth 1) -> Sub_B (depth 2)
    r1 = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "Root_1"})).json()
    sa = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "Sub_A", "parent_id": r1["id"]})).json()
    sb = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "Sub_B", "parent_id": sa["id"]})).json()

    assert sa["depth"] == 1
    assert sb["depth"] == 2

    # Tree 2: Target_Root (depth 0) -> Target_Sub (depth 1)
    tr = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "Target_Root"})).json()
    ts = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "Target_Sub", "parent_id": tr["id"]})).json()
    assert ts["depth"] == 1

    # Move Sub_A into Target_Sub: Sub_A should become depth 2, Sub_B should become depth 3
    mv = await client.post(
        f"/v1/folders/{sa['id']}/move",
        params={"organization_id": str(org_id)},
        json={"new_parent_id": ts["id"]},
    )
    assert mv.status_code == 200
    assert mv.json()["depth"] == 2

    # Check Sub_B depth
    folders_list = (await client.get("/v1/folders", params={"organization_id": str(org_id)})).json()
    sub_b_now = next(f for f in folders_list if f["id"] == sb["id"])
    assert sub_b_now["depth"] == 3


@pytest.mark.asyncio
async def test_deletion_policy_non_empty_blocked(setup_test_org, client: AsyncClient, db: AsyncSession):
    """Deleting folders with subfolders or documents is blocked; empty ordinary folders delete cleanly."""
    org_id = setup_test_org["org_id"]
    service = FolderService(db)

    # 1. Folder with subfolder
    p = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "ParentFolder"})).json()
    child = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "ChildFolder", "parent_id": p["id"]})).json()

    # Attempt delete parent -> 409
    del_p = await client.delete(f"/v1/folders/{p['id']}", params={"organization_id": str(org_id)})
    assert del_p.status_code == 409
    assert "contains 1 subfolder(s)" in del_p.json()["detail"]

    # 2. Delete child -> succeeds
    del_c = await client.delete(f"/v1/folders/{child['id']}", params={"organization_id": str(org_id)})
    assert del_c.status_code == 200

    # 3. Put document in ParentFolder
    from app.db.models.data_source import DataSource
    ds = DataSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Upload Source",
        source_type="file",
        external_id=f"src-{str(org_id)[:8]}",
        authority_level=80,
    )
    db.add(ds)
    await db.flush()

    doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=ds.id,
        folder_id=uuid.UUID(p["id"]),
        title="Test Document",
        content_hash="test_content_hash_12345",
    )
    db.add(doc)
    await db.commit()

    # Attempt delete parent containing document -> 409
    del_doc_p = await client.delete(f"/v1/folders/{p['id']}", params={"organization_id": str(org_id)})
    assert del_doc_p.status_code == 409
    assert "contains 0 subfolder(s) and 1 document(s)" in del_doc_p.json()["detail"]


@pytest.mark.asyncio
async def test_document_move_preserves_immutable_identity(setup_test_org, client: AsyncClient, db: AsyncSession):
    """Moving a document from Folder 1 to Folder 2 preserves UUID, version history, and attributes 100%."""
    org_id = setup_test_org["org_id"]
    f1 = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "SourceFolder"})).json()
    f2 = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "DestinationFolder"})).json()

    from app.db.models.data_source import DataSource
    from app.db.models.document_version import DocumentVersion

    ds = DataSource(id=uuid.uuid4(), organization_id=org_id, name="Src", source_type="file", external_id=f"src-{str(org_id)[:6]}")
    db.add(ds)
    await db.flush()

    doc_id = uuid.uuid4()
    doc = Document(
        id=doc_id,
        organization_id=org_id,
        source_id=ds.id,
        folder_id=uuid.UUID(f1["id"]),
        title="Critical Policy",
        content_hash="sha256_original_hash_12345",
    )
    db.add(doc)
    await db.flush()

    ver = DocumentVersion(
        id=uuid.uuid4(),
        document_id=doc_id,
        version_number=1,
        content_hash="sha256_original_hash_12345",
        is_current=True,
    )
    db.add(ver)
    await db.commit()

    # Move document
    mv_res = await client.post(
        f"/v1/documents/{doc_id}/move",
        json={"destination_folder_id": f2["id"]},
    )
    assert mv_res.status_code == 200
    updated_doc = mv_res.json()

    assert updated_doc["id"] == str(doc_id)
    assert updated_doc["folder_id"] == f2["id"]
    assert updated_doc["content_hash"] == "sha256_original_hash_12345"
    assert updated_doc["versions"][0]["id"] == str(ver.id)


@pytest.mark.asyncio
async def test_metrics_transparent_counts(setup_test_org, client: AsyncClient, db: AsyncSession):
    """Metrics return explicit integer counters, not uncalibrated averages."""
    org_id = setup_test_org["org_id"]
    f = (await client.post("/v1/folders", params={"organization_id": str(org_id)}, json={"name": "MetricsTestFolder"})).json()
    fid = f["id"]

    res = await client.get(f"/v1/folders/{fid}/metrics", params={"organization_id": str(org_id)})
    assert res.status_code == 200
    metrics = res.json()

    assert metrics["folder_id"] == fid
    assert "notice" in metrics["scope"]
    assert metrics["documents"]["total"] == 0
    assert "completed" in metrics["documents"]["by_processing_state"]
    assert "human_certified" in metrics["claims"]["by_verification_tier"]
    assert "conflicts_detected_in_scope" in metrics


@pytest.mark.asyncio
async def test_slack_5_tier_folder_hierarchy_and_routing(setup_test_org, db: AsyncSession):
    """
    Verifies that FolderService constructs the exact 5-tier Slack hierarchy:
    Connected Integrations (L0) -> Slack (L1) -> Slack Channels (L2) -> #{channel} (L3) -> (Slack Messages, Slack Documents) (L4)
    and that migration routes messages and attachments into their respective subfolders.
    """
    from app.db.models.data_source import DataSource

    org_id = setup_test_org["org_id"]
    service = FolderService(db)

    # 1. Provision Slack channel hierarchy for #social
    msgs_folder, docs_folder = await service.ensure_slack_hierarchy(org_id, "#social")
    await db.commit()

    assert msgs_folder.name == "Slack Messages"
    assert msgs_folder.folder_type == "slack_messages"
    assert msgs_folder.depth == 4

    assert docs_folder.name == "Slack Documents"
    assert docs_folder.folder_type == "slack_documents"
    assert docs_folder.depth == 4
    assert msgs_folder.parent_id == docs_folder.parent_id

    # Verify Level 3: Channel folder #social
    res_ch = await db.execute(select(Folder).where(Folder.id == msgs_folder.parent_id))
    channel_folder = res_ch.scalar_one()
    assert channel_folder.name == "#social"
    assert channel_folder.depth == 3
    assert channel_folder.folder_type == "slack_channel"

    # Verify Level 2: Slack Channels container
    res_ch_root = await db.execute(select(Folder).where(Folder.id == channel_folder.parent_id))
    channels_root = res_ch_root.scalar_one()
    assert channels_root.name == "Slack Channels"
    assert channels_root.depth == 2

    # Verify Level 1: Slack Provider
    res_slack = await db.execute(select(Folder).where(Folder.id == channels_root.parent_id))
    slack_root = res_slack.scalar_one()
    assert slack_root.name == "Slack"
    assert slack_root.depth == 1
    assert slack_root.folder_type == "connector_service"

    # Verify Level 0: Connected Integrations
    res_conn = await db.execute(select(Folder).where(Folder.id == slack_root.parent_id))
    conn_root = res_conn.scalar_one()
    assert conn_root.name == "Connected Integrations"
    assert conn_root.depth == 0

    # 2. Idempotency check: Calling ensure_slack_hierarchy again returns identical folders
    msgs_folder2, docs_folder2 = await service.ensure_slack_hierarchy(org_id, "social")
    assert msgs_folder2.id == msgs_folder.id
    assert docs_folder2.id == docs_folder.id

    # 3. Test Migration: Create documents currently in Inbox
    inbox = await service.ensure_system_inbox(org_id)
    ds = DataSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Slack Test Source",
        source_type="slack",
        external_id=f"slack-test-{uuid.uuid4().hex[:8]}",
    )
    ds_manual = DataSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Direct File Upload",
        source_type="file_upload",
        external_id=f"upload-test-{uuid.uuid4().hex[:8]}",
    )
    db.add_all([ds, ds_manual])
    await db.flush()

    # Thread document in Inbox
    thread_doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=ds.id,
        folder_id=inbox.id,
        title="Slack Thread: #social (1792988883.172359)",
        document_type="slack_message",
        external_id="slack://C01/1792988883.172359",
        content_hash="hash_thread_1",
        metadata={"connector": "slack", "channel": "social"},
    )
    # Extracted attached file in Inbox
    attached_doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=ds.id,
        folder_id=inbox.id,
        title="Basics Of Python Questions",
        document_type="document",
        external_id="slack://C01/file/F999",
        content_hash="hash_attached_1",
        metadata={"connector": "slack", "channel": "social", "filename": "Basics of python questions.docx"},
    )
    # Manual direct upload in Inbox
    manual_doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=ds_manual.id,
        folder_id=inbox.id,
        title="My Manual Notes",
        document_type="document",
        content_hash="hash_manual_1",
        metadata={"upload": True},
    )
    db.add_all([thread_doc, attached_doc, manual_doc])
    await db.commit()

    # Run migration
    migration_res = await service.migrate_existing_slack_documents(org_id)
    await db.commit()

    assert migration_res["success"] is True
    assert migration_res["migrated_messages"] >= 1
    assert migration_res["migrated_documents"] >= 1

    # Reload documents
    await db.refresh(thread_doc)
    await db.refresh(attached_doc)
    await db.refresh(manual_doc)

    # Thread doc moved to Slack Messages
    assert thread_doc.folder_id == msgs_folder.id
    # Attached doc moved to Slack Documents
    assert attached_doc.folder_id == docs_folder.id
    # Manual doc stays in Inbox!
    assert manual_doc.folder_id == inbox.id
