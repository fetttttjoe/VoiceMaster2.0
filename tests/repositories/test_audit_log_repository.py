from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.future import select

from database.models import AuditLogEntry, AuditLogEventType
from repositories.audit_log_repository import AuditLogRepository


@pytest.mark.asyncio
async def test_log_event(mock_db_session: AsyncMock):
    """
    Tests that log_event adds an entry and commits.
    """
    repository = AuditLogRepository(mock_db_session)
    await repository.log_event(
        guild_id=1,
        event_type=AuditLogEventType.BOT_SETUP,
        details="Test event",
    )
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_latest_logs(mock_db_session: AsyncMock):
    """
    Tests that get_latest_logs executes a select query.
    """
    repository = AuditLogRepository(mock_db_session)
    # Setup a more explicit mock for the chain of calls
    mock_result = MagicMock()
    mock_scalars = MagicMock()
    mock_scalars.all.return_value = [MagicMock(spec=AuditLogEntry)]
    mock_result.scalars.return_value = mock_scalars
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    logs = await repository.get_latest_logs(guild_id=1, limit=5)

    mock_db_session.execute.assert_called_once()
    assert len(logs) == 1
    # A bit more detailed assertion to check the query structure
    call_args = mock_db_session.execute.call_args[0][0]
    assert isinstance(call_args, type(select(AuditLogEntry)))
