import uuid
from collections.abc import Sequence
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.enums import RecordStatus, UserRole
from app.db.models.user import User
from app.db.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def list_by_organization(self, organization_id: uuid.UUID) -> Sequence[User]:
        stmt = (
            select(User)
            .where(User.organization_id == organization_id, User.status != RecordStatus.DELETED)
            .order_by(User.created_at.asc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_by_email(self, organization_id: uuid.UUID, email: str) -> User | None:
        stmt = select(User).where(User.organization_id == organization_id, User.email == email)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_user(
        self,
        organization_id: uuid.UUID,
        name: str,
        email: str,
        role: UserRole = UserRole.VIEWER,
        title: str | None = None,
        department: str | None = None,
        avatar_url: str | None = None,
        status: RecordStatus = RecordStatus.ACTIVE,
    ) -> User:
        user = User(
            organization_id=organization_id,
            name=name,
            email=email,
            role=role,
            title=title,
            department=department,
            avatar_url=avatar_url,
            status=status,
        )
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

    async def seed_default_personas(self, organization_id: uuid.UUID) -> Sequence[User]:
        """Seed 5 Atlan-inspired personas for an organization if not already seeded."""
        existing = await self.list_by_organization(organization_id)
        if len(existing) >= 4:
            return existing

        default_personas = [
            {
                "name": "Alex Rivera",
                "email": "alex.rivera@demo.local",
                "role": UserRole.DATA_OWNER,
                "title": "Lead Data Engineer",
                "department": "Data Platform & Infrastructure",
                "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Alex",
            },
            {
                "name": "Diana Vance",
                "email": "diana.vance@demo.local",
                "role": UserRole.REVIEWER,
                "title": "Principal Data Steward",
                "department": "Governance & Policy Compliance",
                "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Diana",
            },
            {
                "name": "Sarah Chen",
                "email": "sarah.chen@demo.local",
                "role": UserRole.ADMIN,
                "title": "Chief Compliance Officer",
                "department": "Risk, Trust & Security",
                "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Sarah",
            },
            {
                "name": "Liam Thorne",
                "email": "liam.thorne@demo.local",
                "role": UserRole.DEVELOPER,
                "title": "AI Solutions Architect",
                "department": "Generative AI Platform",
                "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Liam",
            },
            {
                "name": "Rachel Adams",
                "email": "rachel.adams@demo.local",
                "role": UserRole.VIEWER,
                "title": "VP Business Operations",
                "department": "Executive Strategy",
                "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=Rachel",
            },
        ]

        created_users = []
        for p in default_personas:
            existing_user = await self.get_by_email(organization_id, p["email"])
            if not existing_user:
                u = await self.create_user(
                    organization_id=organization_id,
                    name=p["name"],
                    email=p["email"],
                    role=p["role"],
                    title=p["title"],
                    department=p["department"],
                    avatar_url=p["avatar_url"],
                )
                created_users.append(u)
            else:
                created_users.append(existing_user)

        return created_users
