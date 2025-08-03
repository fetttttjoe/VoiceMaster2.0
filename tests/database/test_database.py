from unittest.mock import AsyncMock, MagicMock

import pytest

from database.database import Database


@pytest.mark.asyncio
async def test_get_session_rollback_on_exception():
    """
    Tests that the session rolls back on an exception.
    """
    db = Database("sqlite+aiosqlite:///:memory:")
    mock_session = AsyncMock()
    mock_session.commit.side_effect = Exception("Test Exception")

    # The session factory itself is a callable that returns an async context manager.
    # So, we mock the factory to return a mock that has the async context manager methods.
    mock_session_context_manager = AsyncMock()
    mock_session_context_manager.__aenter__.return_value = mock_session
    db.session_factory = MagicMock(return_value=mock_session_context_manager)

    with pytest.raises(Exception, match="Test Exception"):
        async with db.get_session() as session:
            await session.commit()

    mock_session.rollback.assert_called_once()
