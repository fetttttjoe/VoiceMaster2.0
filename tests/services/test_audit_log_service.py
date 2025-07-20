# VoiceMaster2.2/tests/services/test_audit_log_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.audit_log_service import AuditLogService
from database.models import AuditLogEventType # Ensure this import is present
from datetime import datetime
from typing import cast # New import for explicit type casting

# Import the repository abstraction
from interfaces.audit_log_repository import IAuditLogRepository

@pytest.mark.asyncio
async def test_log_event(mock_db_session): # mock_db_session is now unused but kept for consistency
    """
    Tests that log_event calls crud.create_audit_log_entry with correct parameters.
    """
    # Create a mock for the repository
    mock_audit_log_repository = AsyncMock(spec=IAuditLogRepository)

    # Instantiate the service with the mocked repository
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
async def test_get_latest_logs(mock_db_session): # mock_db_session is now unused but kept for consistency
    """
    Tests that get_latest_logs calls crud.get_latest_audit_log_entries with correct parameters.
    """
    # Create a mock for the repository
    mock_audit_log_repository = AsyncMock(spec=IAuditLogRepository)

    # Instantiate the service with the mocked repository
    audit_log_service = AuditLogService(mock_audit_log_repository)
    
    guild_id = 123
    limit = 5

    # Mock return value for the repository method.
    mock_audit_log_repository.get_latest_entries.return_value = [
        MagicMock(id=1, guild_id=guild_id, event_type=AuditLogEventType.BOT_SETUP.value, timestamp=datetime.now()),
        MagicMock(id=2, guild_id=guild_id, event_type=AuditLogEventType.CHANNEL_CREATED.value, timestamp=datetime.now()),
    ]

    logs = await audit_log_service.get_latest_logs(guild_id, limit)

    mock_audit_log_repository.get_latest_entries.assert_called_once_with(guild_id, limit)
    assert len(logs) == 2
    # Explicitly cast to str to guide Pylance's type inference at the point of assertion
    assert cast(str, logs[0].event_type) == AuditLogEventType.BOT_SETUP.value