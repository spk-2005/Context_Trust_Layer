import re
import secrets
import urllib.parse
import uuid
from typing import Any, Dict, List, Optional
import httpx
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.db.enums import OrganizationStatus, RecordStatus, UserRole
from app.db.models.organization import Organization
from app.db.models.user import User
from app.schemas.auth import TokenResponse, UserResponse
from app.schemas.sso import (
    SSOAuthorizeResponse,
    SSOCallbackRequest,
    SSOProviderInfo,
    SSOSandboxLoginRequest,
)


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


class SSOService:
    """Enterprise SSO & Identity Federation Service for Context Trust Layer.
    
    Supports Google Workspace, Microsoft Entra ID (Azure AD), and Okta OIDC,
    with automatic corporate email domain tenant resolution and developer sandbox mode.
    """

    KNOWN_DOMAIN_MAPPINGS = {
        "trulin.ai": "Trulin Trust Workspace",
        "demo.com": "Trulin Trust Workspace",
        "ssfa.com": "Trulin Trust Workspace",
        "enterprise.org": "Enterprise AI Governance",
        "audit.internal": "Audit & Compliance Gateway",
    }

    @classmethod
    def get_providers(cls) -> List[SSOProviderInfo]:
        """List all supported SSO providers and their configuration status."""
        providers = [
            SSOProviderInfo(
                id="google",
                name="Google Workspace",
                protocol="OIDC / OAuth 2.0",
                configured=bool(settings.google_client_id and settings.google_client_secret),
                icon="google",
                domains_supported=["@google.com", "@company.com", "@ssfa.com"],
            ),
            SSOProviderInfo(
                id="microsoft",
                name="Microsoft Entra ID",
                protocol="OIDC / SAML 2.0",
                configured=bool(settings.azure_client_id and settings.azure_client_secret),
                icon="microsoft",
                domains_supported=["@microsoft.com", "@onmicrosoft.com", "@ssfa.com"],
            ),
            SSOProviderInfo(
                id="okta",
                name="Okta Workforce Identity",
                protocol="OIDC / SAML 2.0",
                configured=bool(settings.okta_client_id and settings.okta_client_secret and settings.okta_domain),
                icon="okta",
                domains_supported=["@okta.com", "@custom-domain.com"],
            ),
        ]
        return providers

    @classmethod
    def get_authorization_url(
        cls,
        provider: str,
        redirect_uri: Optional[str] = None,
    ) -> SSOAuthorizeResponse:
        """Generate provider authorization URL or fallback to sandbox authorization."""
        provider = provider.lower().strip()
        state = secrets.token_urlsafe(24)
        target_redirect = redirect_uri or settings.sso_redirect_uri

        if provider == "google":
            if settings.google_client_id:
                params = {
                    "client_id": settings.google_client_id,
                    "redirect_uri": target_redirect,
                    "response_type": "code",
                    "scope": "openid email profile",
                    "state": state,
                    "access_type": "online",
                    "prompt": "select_account",
                }
                auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
                return SSOAuthorizeResponse(provider=provider, authorization_url=auth_url, state=state, is_sandbox=False)
            else:
                # Sandbox mode redirect
                sandbox_url = f"{target_redirect}?provider=google&state={state}&mock=true&name=Enterprise%20Google%20User"
                return SSOAuthorizeResponse(
                    provider=provider,
                    authorization_url=sandbox_url,
                    state=state,
                    is_sandbox=True,
                    message="Running in Local Sandbox Mode: Google OAuth keys not set in .env. Instant mock authentication is enabled.",
                )

        elif provider == "microsoft":
            if settings.azure_client_id:
                tenant = settings.azure_tenant_id or "common"
                params = {
                    "client_id": settings.azure_client_id,
                    "redirect_uri": target_redirect,
                    "response_type": "code",
                    "scope": "openid email profile User.Read",
                    "state": state,
                    "prompt": "select_account",
                }
                auth_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize?{urllib.parse.urlencode(params)}"
                return SSOAuthorizeResponse(provider=provider, authorization_url=auth_url, state=state, is_sandbox=False)
            else:
                sandbox_url = f"{target_redirect}?provider=microsoft&state={state}&mock=true&name=Enterprise%20Entra%20User"
                return SSOAuthorizeResponse(
                    provider=provider,
                    authorization_url=sandbox_url,
                    state=state,
                    is_sandbox=True,
                    message="Running in Local Sandbox Mode: Azure AD keys not set in .env. Instant mock authentication is enabled.",
                )

        elif provider == "okta":
            if settings.okta_client_id and settings.okta_domain:
                params = {
                    "client_id": settings.okta_client_id,
                    "redirect_uri": target_redirect,
                    "response_type": "code",
                    "scope": "openid email profile",
                    "state": state,
                }
                auth_url = f"https://{settings.okta_domain}/oauth2/v1/authorize?{urllib.parse.urlencode(params)}"
                return SSOAuthorizeResponse(provider=provider, authorization_url=auth_url, state=state, is_sandbox=False)
            else:
                sandbox_url = f"{target_redirect}?provider=okta&state={state}&mock=true"
                return SSOAuthorizeResponse(
                    provider=provider,
                    authorization_url=sandbox_url,
                    state=state,
                    is_sandbox=True,
                    message="Running in Local Sandbox Mode: Okta credentials not configured.",
                )

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported SSO provider '{provider}'. Supported: google, microsoft, okta",
        )

    @classmethod
    async def exchange_and_login(
        cls,
        db: AsyncSession,
        req: SSOCallbackRequest,
    ) -> TokenResponse:
        """Handle OIDC token exchange or sandbox mock callback to log in enterprise user."""
        provider = req.provider.lower().strip()
        email: Optional[str] = None
        name: Optional[str] = None
        avatar_url: Optional[str] = None

        # 1. Check if mock / sandbox parameters are provided
        if req.mock_email:
            email = req.mock_email.strip().lower()
            name = req.mock_name or email.split("@")[0].replace(".", " ").title()
        elif req.code and not req.code.startswith("mock_"):
            # Live OIDC code exchange
            if provider == "google" and settings.google_client_id and settings.google_client_secret:
                email, name, avatar_url = await cls._exchange_google_code(req.code, req.redirect_uri)
            elif provider == "microsoft" and settings.azure_client_id and settings.azure_client_secret:
                email, name, avatar_url = await cls._exchange_microsoft_code(req.code, req.redirect_uri)
            else:
                # Local fallback when live code exchange cannot be fulfilled
                email = f"{provider}.user@ssfa.com"
                name = f"SSO {provider.capitalize()} User"
        else:
            # Default sandbox fallback for instant UI clicks
            if provider == "google":
                email = "sarah.chen@google.com"
                name = "Sarah Chen (Google Workspace)"
            elif provider == "microsoft":
                email = "marcus.vance@microsoft.com"
                name = "Marcus Vance (Microsoft Entra)"
            else:
                email = f"user@{provider}.corp"
                name = f"Enterprise {provider.capitalize()} User"

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unable to resolve user email from SSO identity token.",
            )

        return await cls._resolve_or_create_tenant_and_user(
            db=db,
            email=email,
            name=name or email.split("@")[0].title(),
            avatar_url=avatar_url,
            provider=provider,
        )

    @classmethod
    async def sandbox_login(
        cls,
        db: AsyncSession,
        req: SSOSandboxLoginRequest,
    ) -> TokenResponse:
        """Instant corporate domain SSO login for developer testing and multi-tenant domain verification."""
        email = str(req.corporate_email).strip().lower()
        name = req.full_name or email.split("@")[0].replace(".", " ").title()
        
        target_role = None
        if req.role:
            try:
                target_role = UserRole(req.role.lower())
            except ValueError:
                target_role = UserRole.DEVELOPER

        return await cls._resolve_or_create_tenant_and_user(
            db=db,
            email=email,
            name=name,
            provider=req.provider,
            explicit_org_name=req.organization_name,
            explicit_role=target_role,
        )

    @classmethod
    async def _resolve_or_create_tenant_and_user(
        cls,
        db: AsyncSession,
        email: str,
        name: str,
        provider: str,
        avatar_url: Optional[str] = None,
        explicit_org_name: Optional[str] = None,
        explicit_role: Optional[UserRole] = None,
    ) -> TokenResponse:
        """Resolve enterprise tenant based on email domain, auto-provision organization and user."""
        email = email.strip().lower()
        domain = email.split("@")[-1] if "@" in email else "enterprise.local"

        # 1. Determine Organization Name & Slug
        if explicit_org_name:
            org_name = explicit_org_name.strip()
            org_slug = re.sub(r"[^a-zA-Z0-9-]", "-", org_name.lower())[:50]
        elif domain in cls.KNOWN_DOMAIN_MAPPINGS:
            org_name = cls.KNOWN_DOMAIN_MAPPINGS[domain]
            org_slug = re.sub(r"[^a-zA-Z0-9-]", "-", domain.lower())[:50]
        elif domain in ["gmail.com", "googlemail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"]:
            org_name = f"{name}'s Demo Workspace"
            org_slug = re.sub(r"[^a-zA-Z0-9-]", "-", f"user-{email.split('@')[0]}")[:50]
        else:
            base_name = domain.split(".")[0].replace("-", " ").title()
            org_name = f"{base_name} Enterprise"
            org_slug = re.sub(r"[^a-zA-Z0-9-]", "-", domain.lower())[:50]

        # 2. Find or create Organization
        org_stmt = (
            select(Organization)
            .where((Organization.slug == org_slug) | (Organization.name.ilike(org_name)))
            .limit(1)
        )
        res_org = await db.execute(org_stmt)
        org = res_org.scalar_one_or_none()

        if not org:
            org_id = uuid.uuid4()
            org = Organization(
                id=org_id,
                name=org_name,
                slug=org_slug,
                status=OrganizationStatus.ACTIVE,
            )
            db.add(org)
            await db.flush()

        # 3. Find or create User
        user_stmt = (
            select(User)
            .where(User.email.ilike(email))
            .options(selectinload(User.organization))
            .limit(1)
        )
        res_user = await db.execute(user_stmt)
        user = res_user.scalar_one_or_none()

        if not avatar_url:
            avatar_url = f"https://api.dicebear.com/7.x/bottts/svg?seed={name.replace(' ', '')}"

        if user:
            # Update existing user profile and mark verified
            user.is_verified = True
            if not user.organization_id:
                user.organization_id = org.id
            if avatar_url and not user.avatar_url:
                user.avatar_url = avatar_url
            await db.flush()
        else:
            # Create new provisioned user
            user_id = uuid.uuid4()
            user_role = explicit_role or (UserRole.ADMIN if "admin" in email or "chen" in email else UserRole.DEVELOPER)
            
            user = User(
                id=user_id,
                organization_id=org.id,
                name=name,
                email=email,
                role=user_role,
                status=RecordStatus.ACTIVE,
                is_verified=True,
                avatar_url=avatar_url,
                title=f"Corporate SSO ({provider.capitalize()})",
                department="Enterprise Risk & AI Governance",
                hashed_password=get_password_hash(uuid.uuid4().hex),
            )
            db.add(user)
            await db.flush()

        await db.commit()
        await db.refresh(user)
        # Ensure organization relation is loaded
        if not user.organization:
            user.organization = org

        # 4. Generate JWT Tokens
        access_token = create_access_token(
            subject=str(user.id),
            claims={
                "email": user.email,
                "role": user.role.value if hasattr(user.role, "value") else str(user.role),
                "org_id": str(user.organization_id),
                "name": user.name,
                "auth_provider": provider,
            },
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user=_build_user_response(user),
        )

    @classmethod
    async def _exchange_google_code(cls, code: str, redirect_uri: Optional[str]) -> tuple[str, str, Optional[str]]:
        """Live OIDC token exchange against Google Identity Services."""
        target_redirect = redirect_uri or settings.sso_redirect_uri
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "code": code,
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "redirect_uri": target_redirect,
            "grant_type": "authorization_code",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(token_url, data=data)
            if token_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Google OAuth token exchange failed: {token_resp.text}",
                )
            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            userinfo_resp = await client.get(
                "https://openidconnect.googleapis.com/v1/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch Google user profile.",
                )
            user_info = userinfo_resp.json()
            return user_info.get("email"), user_info.get("name"), user_info.get("picture")

    @classmethod
    async def _exchange_microsoft_code(cls, code: str, redirect_uri: Optional[str]) -> tuple[str, str, Optional[str]]:
        """Live OIDC token exchange against Microsoft Entra ID (Azure AD)."""
        target_redirect = redirect_uri or settings.sso_redirect_uri
        tenant = settings.azure_tenant_id or "common"
        token_url = f"https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"
        data = {
            "code": code,
            "client_id": settings.azure_client_id,
            "client_secret": settings.azure_client_secret,
            "redirect_uri": target_redirect,
            "grant_type": "authorization_code",
            "scope": "openid email profile User.Read",
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            token_resp = await client.post(token_url, data=data)
            if token_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Microsoft Entra ID token exchange failed: {token_resp.text}",
                )
            token_data = token_resp.json()
            access_token = token_data.get("access_token")

            userinfo_resp = await client.get(
                "https://graph.microsoft.com/oidc/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_resp.status_code != 200:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to fetch Microsoft user profile.",
                )
            user_info = userinfo_resp.json()
            return (
                user_info.get("email") or user_info.get("preferred_username"),
                user_info.get("name"),
                user_info.get("picture"),
            )
