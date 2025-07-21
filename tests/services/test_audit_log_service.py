import pytest
from unittest.mock import AsyncMock, MagicMock
from services.audit_log_service import AuditLogService
from database.models import AuditLogEventType
from datetime import datetime
from typing import cast

from interfaces.audit_log_repository import IAuditLogRepository

@pytest.mark.asyncio
async def test_log_event(mock_audit_log_repository):
    """
    Tests that log_event calls create_entry on its repository.
    """
    audit_log_service = AuditLogService(mock_audit_log_repository)
    
    guild_id = 123
    event_type = AuditLogEventType.BOT_SETUP
    user_id = 456
    channel_id = 789
    details = "Bot setup completed successfully."

    await audit_log_service.log_event(
        guild_id=guild_id,
        event_type=event_type,
        user_id=user_id,
        channel_id=channel_id,
        details=details
    )

    mock_audit_log_repository.create_entry.assert_called_once_with(
        guild_id=guild_id,
        event_type=event_type,
        user_id=user_id,
        channel_id=channel_id,
        details=details
    )

@pytest.mark.asyncio
async def test_get_latest_logs(mock_audit_log_repository):
    """
    Tests that get_latest_logs calls get_latest_entries on its repository.
    """
    audit_log_service = AuditLogService(mock_audit_log_repository)
    
    guild_id = 123
    limit = 5

    mock_audit_log_repository.get_latest_entries.return_value = [
        MagicMock(id=1, event_type=AuditLogEventType.BOT_SETUP.value),
    ]

    logs = await audit_log_service.get_latest_logs(guild_id, limit)

    mock_audit_log_repository.get_latest_entries.assert_called_once_with(guild_id, limit)
    assert len(logs) == 1
    assert cast(str, logs[0].event_type) == AuditLogEventType.BOT_SETUP.value
