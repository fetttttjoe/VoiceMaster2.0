from typing import List, Optional

from database.models import AuditLogEntry, AuditLogEventType
from interfaces.audit_log_repository import IAuditLogRepository
from interfaces.audit_log_service import IAuditLogService


class AuditLogService(IAuditLogService):
    def __init__(self, audit_log_repository: IAuditLogRepository):
        self._audit_log_repository = audit_log_repository

    async def log_event(
        self,
        guild_id: int,
        event_type: AuditLogEventType,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        await self._audit_log_repository.log_event(
            guild_id=guild_id,
            event_type=event_type,
            user_id=user_id,
            channel_id=channel_id,
            details=details,
        )

    async def get_latest_logs(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]:
        return await self._audit_log_repository.get_latest_logs(guild_id, limit)
