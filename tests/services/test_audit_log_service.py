# VoiceMaster2.0/tests/services/test_audit_log_service.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from services.audit_log_service import AuditLogService
from database.models import AuditLogEventType # Ensure this import is present
from datetime import datetime
from typing import cast # New import for explicit type casting

@pytest.mark.asyncio
async def test_log_event(mock_db_session):
    """
    Tests that log_event calls crud.create_audit_log_entry with correct parameters.
    """
    with patch('database.crud.create_audit_log_entry', new_callable=AsyncMock) as mock_create_entry:
        audit_log_service = AuditLogService(mock_db_session)
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

        mock_create_entry.assert_called_once_with(
            mock_db_session,
            guild_id=guild_id,
            event_type=event_type, # Pass the enum member directly to log_event
            user_id=user_id,
            channel_id=channel_id,
            details=details
        )

@pytest.mark.asyncio
async def test_get_latest_logs(mock_db_session):
    """
    Tests that get_latest_logs calls crud.get_latest_audit_log_entries with correct parameters.
    """
    with patch('database.crud.get_latest_audit_log_entries', new_callable=AsyncMock) as mock_get_latest:
        audit_log_service = AuditLogService(mock_db_session)
        guild_id = 123
        limit = 5

        # Mock return value for crud function. The stored value in DB is the string value of the enum.
        mock_get_latest.return_value = [
            MagicMock(id=1, guild_id=guild_id, event_type=AuditLogEventType.BOT_SETUP.value, timestamp=datetime.now()),
            MagicMock(id=2, guild_id=guild_id, event_type=AuditLogEventType.CHANNEL_CREATED.value, timestamp=datetime.now()),
        ]

        logs = await audit_log_service.get_latest_logs(guild_id, limit)

        mock_get_latest.assert_called_once_with(mock_db_session, guild_id, limit)
        assert len(logs) == 2
        # Explicitly cast to str to guide Pylance's type inference at the point of assertion
        assert cast(str, logs[0].event_type) == AuditLogEventType.BOT_SETUP.value