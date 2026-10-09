import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.enums import UserRole
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.user import (
    ActivityLogCreate,
    ActivityLogResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/users", tags=["Users & Governance"])

DEMO_ORG_ID = uuid.UUID("11111111-1111-1111-1111-111111111111")


@router.get("", response_model=list[UserResponse])
async def list_users(
    organization_id: uuid.UUID = Query(default=DEMO_ORG_ID),
    db: AsyncSession = Depends(get_db),
):
    """List team members for the organization. Auto-seeds default Atlan personas if table is empty."""
    user_repo = UserRepository(db)
    users = await user_repo.seed_default_personas(organization_id)
    await db.commit()
    return users


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
):
    """Invite or register a new team member with specific role and persona."""
    user_repo = UserRepository(db)
    activity_service = ActivityService(db)

    existing = await user_repo.get_by_email(user_in.organization_id, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists in organization.")

    user = await user_repo.create_user(
        organization_id=user_in.organization_id,
        name=user_in.name,
        email=user_in.email,
        role=user_in.role,
        title=user_in.title,
        department=user_in.department,
        avatar_url=user_in.avatar_url or f"https://api.dicebear.com/7.x/bottts/svg?seed={user_in.name}",
    )

    await activity_service.log_activity(
        organization_id=user_in.organization_id,
        user_id=user.id,
        user_name=user.name,
        user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        action_type="MEMBER_INVITED",
        target_type="user",
        target_id=str(user.id),
        target_title=f"{user.name} ({user.role})",
        domain=user.department or "General",
        details={"email": user.email, "role": str(user.role), "title": user.title},
    )
    await db.commit()
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update user role, title, department, or status."""
    user_repo = UserRepository(db)
    activity_service = ActivityService(db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_in.name is not None:
        user.name = user_in.name
    if user_in.role is not None:
        old_role = str(user.role)
        user.role = user_in.role
        await activity_service.log_activity(
            organization_id=user.organization_id,
            user_id=user.id,
            user_name=user.name,
            user_role=str(user.role),
            action_type="ROLE_UPDATED",
            target_type="user",
            target_id=str(user.id),
            target_title=user.name,
            domain=user.department or "General",
            details={"old_role": old_role, "new_role": str(user.role)},
        )
    if user_in.title is not None:
        user.title = user_in.title
    if user_in.department is not None:
        user.department = user_in.department
    if user_in.avatar_url is not None:
        user.avatar_url = user_in.avatar_url
    if user_in.status is not None:
        user.status = user_in.status

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a team member from the organization, protecting against deleting the sole administrator."""
    user_repo = UserRepository(db)
    activity_service = ActivityService(db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    # Guard against deleting the last administrator
    if user.role == UserRole.ADMIN or str(user.role).lower() == "admin":
        admin_count_stmt = (
            select(func.count(User.id))
            .where(User.organization_id == user.organization_id)
            .where(User.role == UserRole.ADMIN)
        )
        res = await db.execute(admin_count_stmt)
        admin_count = res.scalar() or 0
        if admin_count <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the sole Administrator / CEO of the organization.",
            )

    await activity_service.log_activity(
        organization_id=user.organization_id,
        user_id=user.id,
        user_name=user.name,
        user_role=user.role.value if hasattr(user.role, "value") else str(user.role),
        action_type="MEMBER_REMOVED",
        target_type="user",
        target_id=str(user.id),
        target_title=f"{user.name} ({user.role})",
        domain=user.department or "General",
        details={"email": user.email, "role": str(user.role)},
    )

    await db.delete(user)
    await db.commit()
    return None


@router.post("/seed-personas", response_model=list[UserResponse])
async def seed_personas(
    organization_id: uuid.UUID = Query(default=DEMO_ORG_ID),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly seed or reset the 5 Atlan default operational personas."""
    user_repo = UserRepository(db)
    users = await user_repo.seed_default_personas(organization_id)
    await db.commit()
    return users


@router.get("/activity", response_model=dict[str, Any])
async def list_activity_logs(
    organization_id: uuid.UUID = Query(default=DEMO_ORG_ID),
    user_id: uuid.UUID | None = Query(default=None),
    action_type: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Query paginated user & collaborative governance activity stream."""
    activity_service = ActivityService(db)
    activities, total = await activity_service.get_activities(
        organization_id=organization_id,
        user_id=user_id,
        action_type=action_type,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "activities": [ActivityLogResponse.model_validate(a) for a in activities],
    }


@router.post("/activity", response_model=ActivityLogResponse, status_code=201)
async def create_activity_log(
    activity_in: ActivityLogCreate,
    db: AsyncSession = Depends(get_db),
):
    """Record an operational activity log."""
    activity_service = ActivityService(db)
    log_entry = await activity_service.log_activity(
        organization_id=activity_in.organization_id,
        user_id=activity_in.user_id,
        user_name=activity_in.user_name,
        user_role=activity_in.user_role,
        action_type=activity_in.action_type,
        target_type=activity_in.target_type,
        target_id=activity_in.target_id,
        target_title=activity_in.target_title,
        domain=activity_in.domain,
        details=activity_in.details,
    )
    await db.commit()
    return ActivityLogResponse.model_validate(log_entry)


@router.get("/domains", response_model=list[dict[str, Any]])
async def list_governance_domains(
    organization_id: uuid.UUID = Query(default=DEMO_ORG_ID),
    db: AsyncSession = Depends(get_db),
):
    """Return Atlan-style Data Domains with assigned leads, description, and asset health status."""
    return [
        {
            "id": "domain_finance",
            "name": "Finance & Billing",
            "description": "Enterprise customer refund policies, invoice verification, and payment gateway SLAs.",
            "lead_name": "Diana Vance",
            "lead_role": "Principal Data Steward",
            "lead_avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Diana",
            "data_sources_count": 4,
            "claims_count": 18,
            "trust_score_avg": 94,
            "sensitivity": "CONFIDENTIAL",
        },
        {
            "id": "domain_eng",
            "name": "Engineering & Platform",
            "description": "Database schemas, Kafka event stream contracts, API rate limits, and Git security rules.",
            "lead_name": "Alex Rivera",
            "lead_role": "Lead Data Engineer",
            "lead_avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Alex",
            "data_sources_count": 8,
            "claims_count": 42,
            "trust_score_avg": 98,
            "sensitivity": "INTERNAL",
        },
        {
            "id": "domain_compliance",
            "name": "Risk & Legal Compliance",
            "description": "SOC2 controls, GDPR/CCPA data retention SLAs, AI safety bounds, and decision audits.",
            "lead_name": "Sarah Chen",
            "lead_role": "Chief Compliance Officer",
            "lead_avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Sarah",
            "data_sources_count": 3,
            "claims_count": 15,
            "trust_score_avg": 99,
            "sensitivity": "RESTRICTED",
        },
        {
            "id": "domain_ai",
            "name": "AI Agents & Autonomous Systems",
            "description": "MCP server endpoints, AI agent access tokens, prompt templates, and Decision Gates.",
            "lead_name": "Liam Thorne",
            "lead_role": "AI Solutions Architect",
            "lead_avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=Liam",
            "data_sources_count": 2,
            "claims_count": 24,
            "trust_score_avg": 96,
            "sensitivity": "INTERNAL",
        },
    ]
