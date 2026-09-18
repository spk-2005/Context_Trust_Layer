import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_optional_current_user
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.db.database import get_db
from app.db.enums import OrganizationStatus, RecordStatus, UserRole
from app.db.models.organization import Organization
from app.db.models.organization_invite import OrganizationInvite
from app.db.models.user import User
from app.schemas.auth import UserResponse
from app.schemas.organization import (
    InviteAcceptRequest,
    InviteCreateRequest,
    InviteInspectResponse,
    InviteResponse,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationMemberRoleUpdate,
    OrganizationResponse,
    OrganizationSettingsUpdate,
    TenantSwitchResponse,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _build_org_response(org: Organization, member_count: int = 0) -> OrganizationResponse:
    whitelist = org.domain_whitelist if org.domain_whitelist is not None else []
    auth_methods = org.allowed_auth_methods if org.allowed_auth_methods is not None else ["password", "google", "microsoft", "okta"]
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status,
        domain_whitelist=whitelist,
        allowed_auth_methods=auth_methods,
        member_count=member_count,
        created_at=org.created_at,
        updated_at=org.updated_at,
    )


def _build_user_response(user: User, org_name: Optional[str] = None) -> UserResponse:
    resolved_org_name = org_name or (user.organization.name if user.organization else "Enterprise Tenant")
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        organization_name=resolved_org_name,
        name=user.name,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        avatar_url=user.avatar_url,
        title=user.title,
        department=user.department,
    )


# ==========================================
# 1. Organization Listings & Registration
# ==========================================

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
):
    """List all registered enterprise organizations / tenant workspaces with member counts."""
    # Query organizations with aggregate member count
    stmt = (
        select(Organization, func.count(User.id).label("member_count"))
        .outerjoin(User, (User.organization_id == Organization.id) & (User.status == RecordStatus.ACTIVE))
        .group_by(Organization.id)
        .order_by(Organization.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    response = []
    for org, count in rows:
        response.append(_build_org_response(org, member_count=count or 0))
    return response


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new enterprise organization / client company tenant."""
    slug = data.slug.strip().lower()
    existing_stmt = select(Organization).where(Organization.slug == slug).limit(1)
    res_exist = await db.execute(existing_stmt)
    if res_exist.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with slug '{slug}' already exists.",
        )

    org = Organization(
        id=uuid.uuid4(),
        name=data.name.strip(),
        slug=slug,
        status=OrganizationStatus.ACTIVE,
        domain_whitelist=data.domain_whitelist or [],
        allowed_auth_methods=data.allowed_auth_methods or ["password", "google", "microsoft", "okta"],
    )
    db.add(org)
    await db.commit()
    await db.refresh(org)
    return _build_org_response(org, member_count=0)


# ==========================================
# 2. Multi-Tenant Workspace Switching
# ==========================================

@router.post("/{org_id}/switch", response_model=TenantSwitchResponse)
async def switch_organization(
    org_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch active tenant context. Validates organization, updates context, and issues refreshed JWT."""
    # 1. Resolve organization
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target organization not found.")

    # 2. Resolve user: if user authenticated via JWT use them, else fallback to active persona or default
    target_user = current_user
    if not target_user:
        # Fallback to Sarah Chen (admin) or first available user for demo
        fallback_stmt = select(User).where(User.status == RecordStatus.ACTIVE).limit(1)
        res_fb = await db.execute(fallback_stmt)
        target_user = res_fb.scalar_one_or_none()

    if not target_user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No active user session to switch tenant.")

    # 3. Update target user's active organization in DB
    target_user.organization_id = org.id
    await db.commit()
    await db.refresh(target_user)

    # 4. Mint freshly signed JWT tokens carrying the new active org_id
    access_token = create_access_token(
        subject=str(target_user.id),
        claims={
            "email": target_user.email,
            "role": target_user.role.value if hasattr(target_user.role, "value") else str(target_user.role),
            "org_id": str(org.id),
            "name": target_user.name,
        },
    )
    refresh_token = create_refresh_token(subject=str(target_user.id))

    # 5. Get member count for target organization
    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return TenantSwitchResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(target_user, org_name=org.name),
        active_organization=_build_org_response(org, member_count=m_count),
    )


# ==========================================
# 3. Organization Settings & Domain Whitelists
# ==========================================

@router.get("/{org_id}/settings", response_model=OrganizationResponse)
async def get_organization_settings(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve complete organization configuration, domain whitelists, and auth settings."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return _build_org_response(org, member_count=m_count)


@router.patch("/{org_id}/settings", response_model=OrganizationResponse)
async def update_organization_settings(
    org_id: uuid.UUID,
    data: OrganizationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update organization name, slug, domain whitelist, and allowed SSO auth methods."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    if data.name is not None:
        org.name = data.name.strip()
    if data.slug is not None:
        org.slug = data.slug.strip().lower()
    if data.domain_whitelist is not None:
        # Clean domains: lowercase, remove @
        cleaned_domains = [d.strip().lower().replace("@", "") for d in data.domain_whitelist if d.strip()]
        org.domain_whitelist = cleaned_domains
    if data.allowed_auth_methods is not None:
        org.allowed_auth_methods = data.allowed_auth_methods

    await db.commit()
    await db.refresh(org)

    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return _build_org_response(org, member_count=m_count)


# ==========================================
# 4. Member Management & Roles
# ==========================================

@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
async def list_organization_members(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all team members currently belonging to an organization workspace."""
    stmt = (
        select(User)
        .where(User.organization_id == org_id)
        .order_by(User.name.asc())
    )
    res = await db.execute(stmt)
    users = res.scalars().all()

    return [
        OrganizationMemberResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            status=u.status.value if hasattr(u.status, "value") else str(u.status),
            title=u.title,
            department=u.department,
            avatar_url=u.avatar_url,
            is_verified=u.is_verified,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.patch("/{org_id}/members/{user_id}", response_model=OrganizationMemberResponse)
async def update_member_role(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: OrganizationMemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a team member's role (Admin, Data Steward, Auditor, Operator, Developer)."""
    stmt = select(User).where((User.id == user_id) & (User.organization_id == org_id)).limit(1)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this organization.")

    try:
        user.role = UserRole(data.role.lower())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role '{data.role}'.")

    await db.commit()
    await db.refresh(user)

    return OrganizationMemberResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        title=user.title,
        department=user.department,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the organization workspace."""
    stmt = select(User).where((User.id == user_id) & (User.organization_id == org_id)).limit(1)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    user.status = RecordStatus.DEPRECATED
    await db.commit()
    return None


# ==========================================
# 5. Enterprise Invite Links & Invitations
# ==========================================

@router.post("/{org_id}/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    org_id: uuid.UUID,
    data: InviteCreateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an enterprise invitation link for a corporate colleague."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    try:
        assigned_role = UserRole(data.role.lower())
    except ValueError:
        assigned_role = UserRole.DEVELOPER

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    inviter_id = current_user.id if current_user else None

    invite = OrganizationInvite(
        id=uuid.uuid4(),
        organization_id=org.id,
        email=data.email.strip().lower(),
        role=assigned_role,
        token=token,
        invited_by_id=inviter_id,
        expires_at=expires_at,
        status="pending",
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    invite_url = f"http://localhost:4000/invite?token={token}"
    return InviteResponse(
        id=invite.id,
        organization_id=org.id,
        organization_name=org.name,
        email=invite.email,
        role=invite.role.value if hasattr(invite.role, "value") else str(invite.role),
        token=invite.token,
        invite_url=invite_url,
        status=invite.status,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.get("/{org_id}/invites", response_model=List[InviteResponse])
async def list_invites(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all pending invitations for an organization workspace."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    org_name = org.name if org else "Enterprise Tenant"

    stmt = (
        select(OrganizationInvite)
        .where((OrganizationInvite.organization_id == org_id) & (OrganizationInvite.status == "pending"))
        .order_by(OrganizationInvite.created_at.desc())
    )
    res = await db.execute(stmt)
    invites = res.scalars().all()

    return [
        InviteResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            organization_name=org_name,
            email=inv.email,
            role=inv.role.value if hasattr(inv.role, "value") else str(inv.role),
            token=inv.token,
            invite_url=f"http://localhost:4000/invite?token={inv.token}",
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invites
    ]


@router.delete("/{org_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    org_id: uuid.UUID,
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Revoke an active invitation."""
    stmt = select(OrganizationInvite).where(
        (OrganizationInvite.id == invite_id) & (OrganizationInvite.organization_id == org_id)
    ).limit(1)
    res = await db.execute(stmt)
    invite = res.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")

    invite.status = "revoked"
    await db.commit()
    return None


# Global invite inspection and acceptance (unauthenticated)
@router.get("/invites/inspect", response_model=InviteInspectResponse)
async def inspect_invite(
    token: str = Query(..., description="Invite secret token"),
    db: AsyncSession = Depends(get_db),
):
    """Inspect invitation token details without logging in."""
    stmt = (
        select(OrganizationInvite)
        .where(OrganizationInvite.token == token.strip())
        .options(selectinload(OrganizationInvite.organization))
        .limit(1)
    )
    res = await db.execute(stmt)
    invite = res.scalar_one_or_none()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invitation link.")

    now = datetime.now(timezone.utc)
    is_expired = invite.expires_at < now
    org_name = invite.organization.name if invite.organization else "Enterprise Tenant"
    org_slug = invite.organization.slug if invite.organization else "tenant"

    return InviteInspectResponse(
        token=invite.token,
        organization_id=invite.organization_id,
        organization_name=org_name,
        organization_slug=org_slug,
        email=invite.email,
        role=invite.role.value if hasattr(invite.role, "value") else str(invite.role),
        expires_at=invite.expires_at,
        is_expired=is_expired,
    )


@router.post("/invites/accept", response_model=TenantSwitchResponse)
async def accept_invite(
    data: InviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation, onboard the user, and return JWT authentication session."""
    stmt = (
        select(OrganizationInvite)
        .where(OrganizationInvite.token == data.token.strip())
        .options(selectinload(OrganizationInvite.organization))
        .limit(1)
    )
    res = await db.execute(stmt)
    invite = res.scalar_one_or_none()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already accepted invitation.")

    now = datetime.now(timezone.utc)
    if invite.expires_at < now:
        invite.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation link has expired.")

    org = invite.organization
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target organization no longer exists.")

    # Find or create User
    user_stmt = select(User).where(User.email == invite.email.lower()).limit(1)
    res_user = await db.execute(user_stmt)
    user = res_user.scalar_one_or_none()

    if user:
        user.organization_id = org.id
        user.role = invite.role
        user.status = RecordStatus.ACTIVE
        user.is_verified = True
    else:
        user_name = data.full_name or invite.email.split("@")[0].replace(".", " ").title()
        hashed_pwd = get_password_hash(data.password or uuid.uuid4().hex)
        user = User(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=user_name,
            email=invite.email.lower(),
            hashed_password=hashed_pwd,
            role=invite.role,
            status=RecordStatus.ACTIVE,
            is_verified=True,
            avatar_url=f"https://api.dicebear.com/7.x/bottts/svg?seed={user_name.replace(' ', '')}",
            title="Enterprise Team Member",
            department="Risk & AI Governance",
        )
        db.add(user)

    invite.status = "accepted"
    await db.commit()
    await db.refresh(user)

    # Issue JWT tokens
    access_token = create_access_token(
        subject=str(user.id),
        claims={
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "org_id": str(org.id),
            "name": user.name,
        },
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return TenantSwitchResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(user, org_name=org.name),
        active_organization=_build_org_response(org, member_count=m_count),
    )
