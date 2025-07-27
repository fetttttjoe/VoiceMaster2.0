from abc import ABC, abstractmethod
from typing import List, Optional

from database.models import AuditLogEntry, AuditLogEventType


class IAuditLogService(ABC):
    """
    Abstract interface for audit log business logic.
    """

    @abstractmethod
    async def log_event(
        self,
        guild_id: int,
        event_type: AuditLogEventType,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None: ...

    @abstractmethod
    async def get_latest_logs(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]: ...
