from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from database.database import Database


@pytest.mark.asyncio
async def test_get_session_rollback_on_exception():
    """
    Tests that the session rolls back when an exception is raised within the
    'async with' block.
    """
    # Arrange
    db = Database()
    db.init_db("sqlite+aiosqlite:///:memory:")
    mock_session = AsyncMock()

    # Mock the session factory to return our mock session context manager
    with patch("database.database.async_sessionmaker") as mock_async_sessionmaker:
        mock_async_sessionmaker.return_value = MagicMock(return_value=mock_session)
        db.session_factory = mock_async_sessionmaker.return_value

        # Act & Assert
        with pytest.raises(Exception, match="Test Exception"):
            async with db.get_session():
                # This simulates a database operation failing inside the 'with' block.
                raise Exception("Test Exception")

    # Assert that the rollback method was called in the 'except' block of the context manager.
    mock_session.rollback.assert_called_once()
