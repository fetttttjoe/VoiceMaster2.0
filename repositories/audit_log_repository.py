from typing import List, Optional

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditLogEntry, AuditLogEventType
from interfaces.audit_log_repository import IAuditLogRepository


class AuditLogRepository(IAuditLogRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def log_event(
        self,
        guild_id: int,
        event_type: AuditLogEventType,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        self._session.add(
            AuditLogEntry(
                guild_id=guild_id,
                user_id=user_id,
                channel_id=channel_id,
                event_type=event_type.value,
                details=details,
            )
        )
        await self._session.commit()

    async def get_latest_logs(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]:
        result = await self._session.execute(
            select(AuditLogEntry)
            .where(AuditLogEntry.guild_id == guild_id)
            .order_by(desc(AuditLogEntry.timestamp))
            .limit(limit)
        )
        return list(result.scalars().all())
