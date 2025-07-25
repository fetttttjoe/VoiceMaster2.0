from abc import ABC, abstractmethod
from typing import Optional, List
from database.models import AuditLogEntry, AuditLogEventType

class IAuditLogRepository(ABC):
    """
    Abstract interface for audit log data operations.
    """
    @abstractmethod
    async def create_entry(
        self,
        guild_id: int,
        event_type: AuditLogEventType,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        ...

    @abstractmethod
    async def get_latest_entries(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]:
        ...
