from typing import List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from database.models import AuditLogEntry, AuditLogEventType
from interfaces.audit_log_service import IAuditLogService


class AuditLogService(IAuditLogService):
    """
    Implements the business logic for audit log operations.

    This service acts as an intermediary between the application's core logic and
    the data layer, providing a clean API for logging events without directly exposing database interactions.
    """

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
        await crud.create_audit_log_entry(
            self._session,
            guild_id=guild_id,
            event_type=event_type,
            user_id=user_id,
            channel_id=channel_id,
            details=details,
        )

    async def get_latest_logs(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]:
        return list(await crud.get_latest_audit_log_entries(self._session, guild_id, limit))
