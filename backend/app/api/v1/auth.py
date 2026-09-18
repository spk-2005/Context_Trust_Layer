import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
)
from app.db.database import get_db
from app.db.enums import RecordStatus, UserRole
from app.db.models.organization import Organization
from app.db.models.user import User
from app.schemas.auth import (
    PersonaLoginRequest,
    TokenRefreshRequest,
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
)
from app.api.deps import get_current_user, get_optional_current_user
from app.schemas.sso import (
    SSOAuthorizeResponse,
    SSOCallbackRequest,
    SSOProviderInfo,
    SSOSandboxLoginRequest,
)
from app.services.sso_service import SSOService

router = APIRouter(prefix="/auth", tags=["authentication"])


def _build_user_response(user: User) -> UserResponse:
    org_name = user.organization.name if user.organization else "Enterprise Tenant"
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        organization_name=org_name,
        name=user.name,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        avatar_url=user.avatar_url,
        title=user.title,
        department=user.department,
    )


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register_user(
    req: UserRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new enterprise user and assign/create an organization workspace."""
    # 1. Resolve or create organization
    org_name = req.organization_name.strip() if req.organization_name else "Enterprise Tenant"
    org_stmt = select(Organization).where(Organization.name.ilike(org_name)).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()

    if not org:
        # Check if default demo org exists
        default_org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        res_default = await db.execute(select(Organization).where(Organization.id == default_org_id))
        org = res_default.scalar_one_or_none()
        if not org:
            slug = org_name.lower().replace(" ", "-")[:50]
            org = Organization(
                id=default_org_id,
                name=org_name,
                slug=slug,
            )
            db.add(org)
            await db.flush()

    # 2. Check if email already registered in this organization
    user_stmt = select(User).where(User.email.ilike(req.email.strip())).limit(1)
    res_user = await db.execute(user_stmt)
    existing_user = res_user.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An enterprise account with this email address is already registered.",
        )

    # 3. Create user with hashed password
    hashed_pwd = get_password_hash(req.password)
    user_id = uuid.uuid4()
    avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={req.name.replace(' ', '')}"
    
    new_user = User(
        id=user_id,
        organization_id=org.id,
        name=req.name.strip(),
        email=req.email.strip().lower(),
        hashed_password=hashed_pwd,
        role=req.role or UserRole.DEVELOPER,
        status=RecordStatus.ACTIVE,
        is_verified=True,
        avatar_url=avatar,
        title=req.title or "AI Governance Member",
        department=req.department or "Engineering & Operations",
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    # 4. Generate tokens
    access_token = create_access_token(
        subject=str(new_user.id),
        claims={
            "email": new_user.email,
            "role": new_user.role.value if hasattr(new_user.role, "value") else str(new_user.role),
            "org_id": str(org.id),
            "name": new_user.name,
        }
    )
    refresh_token = create_refresh_token(subject=str(new_user.id))

    new_user.organization = org
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(new_user),
    )


@router.post("/login", response_model=TokenResponse)
async def login_user(
    req: UserLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with corporate email and password."""
    stmt = (
        select(User)
        .where(User.email.ilike(req.email.strip()))
        .options(selectinload(User.organization))
        .limit(1)
    )
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or not user.hashed_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your email and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please verify your email and password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.status != RecordStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="This account has been deactivated. Please contact your organization administrator.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        claims={
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "org_id": str(user.organization_id),
            "name": user.name,
        }
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(user),
    )


@router.post("/persona-login", response_model=TokenResponse)
async def persona_quick_login(
    req: PersonaLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """One-click instant authentication for pre-seeded enterprise personas."""
    stmt = select(User).options(selectinload(User.organization))
    
    if req.user_id:
        stmt = stmt.where(User.id == req.user_id)
    elif req.email:
        stmt = stmt.where(User.email.ilike(req.email.strip()))
    elif req.role:
        try:
            r_enum = UserRole(req.role.lower())
            stmt = stmt.where(User.role == r_enum)
        except Exception:
            stmt = stmt.where(User.role == req.role)
    else:
        # Default to primary admin (Sarah Chen)
        stmt = stmt.where(User.role == UserRole.ADMIN)

    res = await db.execute(stmt.limit(1))
    user = res.scalar_one_or_none()

    if not user:
        # Fallback: get any active user
        fallback_res = await db.execute(select(User).options(selectinload(User.organization)).limit(1))
        user = fallback_res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No enterprise persona accounts found in database.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        claims={
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "org_id": str(user.organization_id),
            "name": user.name,
        }
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(user),
    )


@router.get("/personas", response_model=List[UserResponse])
async def list_available_personas(
    db: AsyncSession = Depends(get_db),
):
    """List all available enterprise personas for quick-switch and testing."""
    stmt = (
        select(User)
        .where(User.status == RecordStatus.ACTIVE)
        .options(selectinload(User.organization))
        .order_by(User.name)
    )
    res = await db.execute(stmt)
    users = res.scalars().all()
    return [_build_user_response(u) for u in users]


@router.get("/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user),
):
    """Retrieve the currently authenticated user's profile and active organization context."""
    return _build_user_response(current_user)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_access_token(
    req: TokenRefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a valid refresh token for a newly signed access token."""
    try:
        payload = decode_token(req.refresh_token)
        if payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type for refresh.",
            )
        user_id = uuid.UUID(payload.get("sub"))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Expired or invalid refresh token: {str(e)}",
        )

    stmt = select(User).where(User.id == user_id).options(selectinload(User.organization))
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user or user.status != RecordStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account inactive or not found.",
        )

    access_token = create_access_token(
        subject=str(user.id),
        claims={
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "org_id": str(user.organization_id),
            "name": user.name,
        }
    )
    new_refresh = create_refresh_token(subject=str(user.id))

    return TokenResponse(
        access_token=access_token,
        refresh_token=new_refresh,
        user=_build_user_response(user),
    )


# ==========================================
# Enterprise SSO & Identity Federation
# ==========================================

@router.get("/sso/providers", response_model=List[SSOProviderInfo])
async def list_sso_providers():
    """List available enterprise identity providers (Google Workspace, Microsoft Entra ID, Okta)."""
    return SSOService.get_providers()


@router.get("/sso/authorize/{provider}", response_model=SSOAuthorizeResponse)
async def get_sso_authorize_url(
    provider: str,
    redirect_uri: Optional[str] = None,
):
    """Generate authorization redirect URL for an identity provider."""
    return SSOService.get_authorization_url(provider=provider, redirect_uri=redirect_uri)


@router.post("/sso/callback", response_model=TokenResponse)
async def handle_sso_callback(
    req: SSOCallbackRequest,
    db: AsyncSession = Depends(get_db),
):
    """Process OAuth2/OIDC code exchange or sandbox token exchange and auto-provision user."""
    return await SSOService.exchange_and_login(db=db, req=req)


@router.post("/sso/sandbox-login", response_model=TokenResponse)
async def sso_sandbox_login(
    req: SSOSandboxLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Instant corporate domain SSO login for developer testing and multi-tenant domain verification."""
    return await SSOService.sandbox_login(db=db, req=req)


# ==========================================
# 6. Granular RBAC Permissions Matrix
# ==========================================

@router.get("/permissions/matrix")
async def get_rbac_matrix(
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Retrieve full Atlan-grade RBAC permissions matrix and calling user's active permissions."""
    from app.core.permissions import get_permission_matrix, get_role_permissions

    matrix_data = get_permission_matrix()
    active_role = current_user.role.value if (current_user and hasattr(current_user.role, "value")) else (str(current_user.role) if current_user else "admin")
    granted = get_role_permissions(active_role)

    return {
        **matrix_data,
        "active_role": active_role,
        "granted_permissions": granted,
    }
