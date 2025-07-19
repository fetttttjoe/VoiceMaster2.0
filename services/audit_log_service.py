# VoiceMaster2.0/services/audit_log_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from database import crud
from typing import List, Optional
from database.models import AuditLogEventType # New import

class AuditLogService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def log_event(
        self,
        guild_id: int,
        event_type: AuditLogEventType, 
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        details: Optional[str] = None
    ):
        """Logs an event to the audit log."""
        await crud.create_audit_log_entry(
            self.db_session,
            guild_id=guild_id,
            event_type=event_type,
            user_id=user_id,
            channel_id=channel_id,
            details=details
        )

    async def get_latest_logs(self, guild_id: int, limit: int = 10):
        """Retrieves the latest audit log entries for a guild."""
        return await crud.get_latest_audit_log_entries(self.db_session, guild_id, limit)