from typing import cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from database import crud
from database.models import AuditLogEventType
from services.audit_log_service import AuditLogService


@pytest.mark.asyncio
async def test_log_event(mock_db_session):
    """
    Tests that log_event calls create_entry on its repository.
    """
    audit_log_service = AuditLogService(mock_db_session)

    guild_id = 123
    event_type = AuditLogEventType.BOT_SETUP
    user_id = 456
    channel_id = 789
    details = "Bot setup completed successfully."

    # Mock the crud function directly
    crud.create_audit_log_entry = AsyncMock()

    await audit_log_service.log_event(guild_id=guild_id, event_type=event_type, user_id=user_id, channel_id=channel_id, details=details)

    crud.create_audit_log_entry.assert_called_once_with(
        mock_db_session,
        guild_id=guild_id,
        event_type=event_type,
        user_id=user_id,
        channel_id=channel_id,
        details=details,
    )


@pytest.mark.asyncio
async def test_get_latest_logs(mock_db_session):
    """
    Tests that get_latest_logs calls get_latest_entries on its repository.
    """
    audit_log_service = AuditLogService(mock_db_session)

    guild_id = 123
    limit = 5

    # Mock the crud function directly
    crud.get_latest_audit_log_entries = AsyncMock(
        return_value=[
            MagicMock(id=1, event_type=AuditLogEventType.BOT_SETUP.value),
        ]
    )

    logs = await audit_log_service.get_latest_logs(guild_id, limit)

    crud.get_latest_audit_log_entries.assert_called_once_with(mock_db_session, guild_id, limit)
    assert len(logs) == 1
    assert cast(str, logs[0].event_type) == AuditLogEventType.BOT_SETUP.value
