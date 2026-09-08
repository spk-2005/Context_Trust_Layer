import uuid
from typing import Sequence
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.db.models.organization import Organization
from app.db.repositories.organization_repository import OrganizationRepository
from app.schemas.organization import OrganizationCreate, OrganizationResponse

router = APIRouter(prefix="/organizations", tags=["organizations"])


class OrganizationUpdate(BaseModel):
    name: str | None = None
    slug: str | None = None


@router.get("", response_model=list[OrganizationResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
):
    """List all registered enterprise organizations / tenant companies."""
    stmt = select(Organization).order_by(Organization.created_at.asc())
    result = await db.execute(stmt)
    orgs = result.scalars().all()
    return [OrganizationResponse.model_validate(o) for o in orgs]


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
):
    """Register a new enterprise organization / client company tenant."""
    repo = OrganizationRepository(db)
    existing = await repo.get_by_slug(data.slug)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with slug '{data.slug}' already exists.",
        )

    org = Organization(
        name=data.name,
        slug=data.slug,
    )
    org = await repo.create(org)
    await db.commit()
    return OrganizationResponse.model_validate(org)


@router.get("/{org_id}", response_model=OrganizationResponse)
async def get_organization(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific organization."""
    repo = OrganizationRepository(db)
    org = await repo.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")
    return OrganizationResponse.model_validate(org)


@router.patch("/{org_id}", response_model=OrganizationResponse)
async def update_organization(
    org_id: uuid.UUID,
    data: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update organization name or slug."""
    repo = OrganizationRepository(db)
    org = await repo.get_by_id(org_id)
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found")

    if data.name is not None:
        org.name = data.name.strip()
    if data.slug is not None:
        org.slug = data.slug.strip().lower()

    await db.commit()
    await db.refresh(org)
    return OrganizationResponse.model_validate(org)
