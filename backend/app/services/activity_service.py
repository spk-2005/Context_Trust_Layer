import uuid
from typing import Any
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.user_activity import UserActivityLog


class ActivityService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def log_activity(
        self,
        organization_id: uuid.UUID,
        action_type: str,
        target_type: str,
        target_id: str | None = None,
        target_title: str | None = None,
        domain: str = "General",
        details: dict[str, Any] | None = None,
        user_id: uuid.UUID | None = None,
        user_name: str = "System",
        user_role: str = "system",
    ) -> UserActivityLog:
        """Create and persist an activity log entry."""
        log_entry = UserActivityLog(
            organization_id=organization_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action_type=action_type,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            target_title=target_title,
            domain=domain,
            details=details or {},
        )
        self.session.add(log_entry)
        await self.session.flush()
        return log_entry

    async def get_activities(
        self,
        organization_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        action_type: str | None = None,
        domain: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[UserActivityLog], int]:
        """Fetch paginated activity logs for an organization."""
        query = select(UserActivityLog).where(UserActivityLog.organization_id == organization_id)
        count_query = select(func.count(UserActivityLog.id)).where(UserActivityLog.organization_id == organization_id)

        if user_id:
            query = query.where(UserActivityLog.user_id == user_id)
            count_query = count_query.where(UserActivityLog.user_id == user_id)

        if action_type:
            query = query.where(UserActivityLog.action_type == action_type)
            count_query = count_query.where(UserActivityLog.action_type == action_type)

        if domain and domain.lower() != "all":
            query = query.where(UserActivityLog.domain == domain)
            count_query = count_query.where(UserActivityLog.domain == domain)

        total_res = await self.session.execute(count_query)
        total = total_res.scalar_one()

        query = query.order_by(desc(UserActivityLog.created_at)).offset(offset).limit(limit)
        result = await self.session.execute(query)
        activities = list(result.scalars().all())

        return activities, total
