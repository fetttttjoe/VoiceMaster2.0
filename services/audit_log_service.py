from typing import List, Optional
from interfaces.audit_log_service import IAuditLogService
from interfaces.audit_log_repository import IAuditLogRepository
from database.models import AuditLogEventType, AuditLogEntry

class AuditLogService(IAuditLogService):
    """
    Implements the business logic for audit log operations.

    This service acts as an intermediary between the application's command/event
    handlers and the `AuditLogRepository`, providing a clean interface for
    logging events without directly exposing database interactions.
    It depends on an abstraction (`IAuditLogRepository`) for its data persistence.
    """
    def __init__(self, audit_log_repository: IAuditLogRepository):
        """
        Initializes the AuditLogService with an audit log repository.

        Args:
            audit_log_repository: An implementation of `IAuditLogRepository`
                                  responsible for persisting audit log data.
        """
        self._audit_log_repository = audit_log_repository

    async def log_event(
        self,
        guild_id: int,
        event_type: AuditLogEventType,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        """
        Logs a new audit event.

        This method forwards the event data to the underlying repository for storage.

        Args:
            guild_id: The ID of the guild where the event occurred.
            event_type: The type of event (an `AuditLogEventType` enum member).
            user_id: Optional. The ID of the user associated with the event.
            channel_id: Optional. The ID of the channel associated with the event.
            details: Optional. A detailed description of the event.
        """
        await self._audit_log_repository.create_entry(
            guild_id=guild_id,
            event_type=event_type,
            user_id=user_id,
            channel_id=channel_id,
            details=details,
        )

    async def get_latest_logs(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]:
        """
        Retrieves the latest audit log entries for a specified guild.

        This method delegates the data retrieval to the underlying repository.

        Args:
            guild_id: The ID of the guild to retrieve logs for.
            limit: The maximum number of log entries to return (default is 10).

        Returns:
            A list of `AuditLogEntry` objects, representing the most recent events.
        """
        return await self._audit_log_repository.get_latest_entries(guild_id, limit)