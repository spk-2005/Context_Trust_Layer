import uuid
import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

from app.api.v1.organizations import (
    list_organization_workspaces,
    create_organization_workspace,
    update_organization_workspace,
    delete_organization_workspace,
    update_organization_settings,
)
from app.schemas.organization import (
    WorkspaceCreate,
    WorkspaceUpdate,
    OrganizationSettingsUpdate,
)
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.enums import OrganizationStatus, UserRole, RecordStatus
from app.core.security import create_access_token, decode_token


@pytest.mark.asyncio
async def test_workspace_crud_and_governance_persistence():
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name="Acme Corporation",
        slug="acme-corp",
        status=OrganizationStatus.ACTIVE,
        governance_config={},
    )

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_res = MagicMock()
    mock_res.scalar_one_or_none.return_value = org
    mock_db.execute = AsyncMock(return_value=mock_res)

    # 1. List workspaces on fresh org -> auto provisions starter workspace
    workspaces = await list_organization_workspaces(org_id=org_id, db=mock_db)
    assert len(workspaces) == 1
    assert workspaces[0]["name"] == "Acme Corporation Workspace"
    assert org.governance_config.get("workspaces") is not None

    # 2. Create a new departmental workspace
    create_in = WorkspaceCreate(
        name="SecOps & Compliance",
        domain="secops",
        icon="🛡️",
        description="Security operations and access control policies",
    )
    new_ws = await create_organization_workspace(
        org_id=org_id,
        data=create_in,
        current_user=None,
        db=mock_db,
    )
    assert new_ws["name"] == "SecOps & Compliance"
    assert new_ws["domain"] == "secops"
    assert len(org.governance_config["workspaces"]) == 2

    # 3. Update the workspace
    update_in = WorkspaceUpdate(
        name="SecOps, SOC2 & ISO",
        description="Updated security scope",
    )
    ws_id = new_ws["id"]
    updated_ws = await update_organization_workspace(
        org_id=org_id,
        workspace_id=ws_id,
        data=update_in,
        db=mock_db,
    )
    assert updated_ws["name"] == "SecOps, SOC2 & ISO"
    assert updated_ws["description"] == "Updated security scope"

    # 4. Delete the workspace
    await delete_organization_workspace(
        org_id=org_id,
        workspace_id=ws_id,
        db=mock_db,
    )
    assert len(org.governance_config["workspaces"]) == 1
    assert org.governance_config["workspaces"][0]["name"] == "Acme Corporation Workspace"


@pytest.mark.asyncio
async def test_organization_settings_governance_persistence():
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name="Global Holdings",
        slug="global-holdings",
        status=OrganizationStatus.ACTIVE,
        governance_config={"workspaces": [{"id": "ws_1", "name": "Core", "domain": "governance"}]},
    )

    mock_db = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()

    mock_res_org = MagicMock()
    mock_res_org.scalar_one_or_none.return_value = org

    mock_res_count = MagicMock()
    mock_res_count.scalar.return_value = 5

    mock_db.execute = AsyncMock(side_effect=[mock_res_org, mock_res_count])

    update_in = OrganizationSettingsUpdate(
        name="Global Holdings Corp",
        governance_config={
            "workspaces": [
                {"id": "ws_1", "name": "Core Governance", "domain": "governance"},
                {"id": "ws_2", "name": "Engineering Alpha", "domain": "developer"},
            ],
            "enforce_strict_sod": True,
        },
    )

    resp = await update_organization_settings(org_id=org_id, data=update_in, db=mock_db)
    assert resp.name == "Global Holdings Corp"
    assert len(resp.governance_config.get("workspaces", [])) == 2
    assert resp.governance_config.get("enforce_strict_sod") is True


def test_session_id_in_jwt_claims():
    user_id = uuid.uuid4()
    session_id = "sess_device_abc_123"

    token = create_access_token(
        subject=str(user_id),
        claims={
            "email": "sarah.chen@ssfa.com",
            "session_id": session_id,
        },
    )

    payload = decode_token(token)
    assert payload["sub"] == str(user_id)
    assert payload["session_id"] == session_id
    assert payload["email"] == "sarah.chen@ssfa.com"
