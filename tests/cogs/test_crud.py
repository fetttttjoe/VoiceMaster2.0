# tests/cogs/test_crud.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from database import crud
from database.models import UserSettings, Guild

@pytest.mark.asyncio
async def test_update_user_channel_name_existing_settings():
    """
    Tests that `crud.update_user_channel_name` correctly updates an existing
    `UserSettings` entry when a user's settings are already present in the DB.
    It verifies that `db.execute` is called for an update and `db.add` is not.
    """
    mock_db_session = AsyncMock() # Mock the AsyncSession
    user_id = 123
    new_name = "New Channel Name"
    
    # Simulate existing settings being returned by `get_user_settings`.
    mock_settings = UserSettings(user_id=user_id, custom_channel_name="Old Name")
    
    # Patch `crud.get_user_settings` to control its return value.
    with patch('database.crud.get_user_settings', return_value=mock_settings):
        await crud.update_user_channel_name(mock_db_session, user_id, new_name)
    
    # Verify that `db.execute` was called once (for the update statement).
    mock_db_session.execute.assert_called_once()
    # Verify that `db.add` was NOT called, indicating no new record was added.
    mock_db_session.add.assert_not_called()
    # Verify that `db.commit` was called once to persist the changes.
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_user_channel_name_new_settings():
    """
    Tests that `crud.update_user_channel_name` correctly creates a new
    `UserSettings` entry when a user sets a channel name for the first time.
    It verifies that `db.add` is called and `db.execute` is not.
    """
    mock_db_session = AsyncMock()
    # Configure `mock_db_session.add` to be a synchronous MagicMock to
    # prevent a `RuntimeWarning` that can occur with AsyncMock's default `add`
    # behavior in some pytest-asyncio versions.
    mock_db_session.add = MagicMock()
    user_id = 123
    new_name = "First Channel Name"
    
    # Simulate no existing settings (returns None).
    with patch('database.crud.get_user_settings', return_value=None):
        await crud.update_user_channel_name(mock_db_session, user_id, new_name)
    
    # Verify that `db.add` was called once to add the new settings object.
    mock_db_session.add.assert_called_once()
    # Verify that `db.execute` was NOT called, as no update statement was needed.
    mock_db_session.execute.assert_not_called()
    # Verify that `db.commit` was called once to persist the new record.
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_or_update_guild_creates_new_guild():
    """
    Tests that `crud.create_or_update_guild` creates a new `Guild` entry
    when a guild with the given ID does not already exist in the database.
    It asserts that `db.add` is called for creation.
    """
    mock_db_session = AsyncMock()
    mock_db_session.add = MagicMock() # Mock `add` synchronously for consistency.

    # Simulate `get_guild` returning None, indicating no existing guild.
    with patch('database.crud.get_guild', return_value=None):
        await crud.create_or_update_guild(mock_db_session, 1, 2, 3, 4) # Arbitrary guild data

    # Verify that `db.add` was called to add the new Guild object.
    mock_db_session.add.assert_called_once()
    # Verify that `db.commit` was called to persist the new record.
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_create_or_update_guild_updates_existing_guild():
    """
    Tests that `crud.create_or_update_guild` updates an existing `Guild` entry
    when a guild with the given ID is already present in the database.
    It asserts that `db.execute` is called for the update statement.
    """
    mock_db_session = AsyncMock()
    # Simulate an existing guild object returned by `get_guild`.
    existing_guild = Guild(id=1, owner_id=10, voice_category_id=20, creation_channel_id=30)

    # Simulate `get_guild` returning an existing guild.
    with patch('database.crud.get_guild', return_value=existing_guild):
        # Call `create_or_update_guild` with new values for the existing guild.
        await crud.create_or_update_guild(mock_db_session, 1, 2, 3, 4)

    # Verify that `db.execute` was called once (for the update statement).
    mock_db_session.execute.assert_called_once()
    # Verify that `db.add` was NOT called, as no new record was added.
    mock_db_session.add.assert_not_called()
    # Verify that `db.commit` was called to persist the update.
    mock_db_session.commit.assert_called_once()

@pytest.mark.asyncio
async def test_update_user_channel_limit_new_settings():
    """
    Tests that `crud.update_user_channel_limit` creates new `UserSettings`
    when a user sets a channel limit for the first time (no existing settings).
    It asserts that `db.add` is called for creation.
    """
    mock_db_session = AsyncMock()
    mock_db_session.add = MagicMock() # Mock `add` synchronously.
    user_id = 456
    new_limit = 5

    # Simulate no existing settings.
    with patch('database.crud.get_user_settings', return_value=None):
        await crud.update_user_channel_limit(mock_db_session, user_id, new_limit)

    # Verify that `db.add` was called.
    mock_db_session.add.assert_called_once()
    # Verify that `db.execute` was NOT called.
    mock_db_session.execute.assert_not_called()
    # Verify that `db.commit` was called.
    mock_db_session.commit.assert_called_once()