# tests/database/test_crud.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from database import crud
from database.models import UserSettings


@pytest.mark.asyncio
async def test_update_user_channel_name_existing_settings():
    """Tests updating a user's channel name when settings already exist."""
    mock_db_session = AsyncMock()
    user_id = 123
    new_name = "New Channel Name"

    # Mock the return value of get_user_settings
    mock_settings = UserSettings(
        user_id=user_id, custom_channel_name="Old Name")

    with patch('database.crud.get_user_settings', return_value=mock_settings):
        await crud.update_user_channel_name(mock_db_session, user_id, new_name)

    # Verify that an update was executed and not an add
    mock_db_session.execute.assert_called_once()
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_channel_name_new_settings():
    """Tests creating new settings when a user sets a channel name for the first time."""
    mock_db_session = AsyncMock()
    # Configure the 'add' method to be a synchronous MagicMock to prevent RuntimeWarning
    mock_db_session.add = MagicMock()
    user_id = 123
    new_name = "First Channel Name"

    # Simulate no existing settings
    with patch('database.crud.get_user_settings', return_value=None):
        await crud.update_user_channel_name(mock_db_session, user_id, new_name)

    # Verify that a new UserSettings object was added
    mock_db_session.add.assert_called_once()
    mock_db_session.execute.assert_not_called()
    mock_db_session.commit.assert_called_once()
