# tests/cogs/test_crud.py
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from database import crud
from database.models import Guild, UserSettings


@pytest.mark.asyncio
async def test_update_user_channel_name_existing_settings():
    """
    Tests that `crud.update_user_channel_name` correctly updates an existing
    `UserSettings` entry when a user's settings are already present in the DB.
    It verifies that `db.execute` is called for an update and `db.add` is not.
    """
    mock_db_session = AsyncMock()  # Mock the AsyncSession
    user_id = 123
    new_name = "New Channel Name"

    # Simulate existing settings being returned by `get_user_settings`.
    mock_settings = UserSettings(user_id=user_id, custom_channel_name="Old Name")

    # Patch `crud.get_user_settings` to control its return value.
    with patch("database.crud.get_user_settings", return_value=mock_settings):
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
    with patch("database.crud.get_user_settings", return_value=None):
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
    mock_db_session.add = MagicMock()  # Mock `add` synchronously for consistency.

    # Simulate `get_guild` returning None, indicating no existing guild.
    with patch("database.crud.get_guild", return_value=None):
        await crud.create_or_update_guild(mock_db_session, 1, 2, 3, 4)  # Arbitrary guild data

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
    with patch("database.crud.get_guild", return_value=existing_guild):
        # Call `create_or_update_guild` with new values for the existing guild.
        await crud.create_or_update_guild(mock_db_session, 1, 2, 3, 4)

    # Verify that `db.execute` was called once (for the update statement).
    mock_db_session.execute.assert_called_once()
    # Verify that `db.add` was NOT called, as no new record was added.
    mock_db_session.add.assert_not_called()
    # Verify that `db.commit` was called to persist the update.
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_latest_audit_log_entries():
    """
    Tests that `crud.get_latest_audit_log_entries` queries the database correctly.
    """
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_result
    guild_id = 456
    await crud.get_latest_audit_log_entries(mock_db_session, guild_id)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_create_audit_log_entry():
    """
    Tests that `crud.create_audit_log_entry` adds a new AuditLogEntry object.
    """
    mock_db_session = AsyncMock()
    mock_db_session.add = MagicMock()
    await crud.create_audit_log_entry(mock_db_session, 1, crud.AuditLogEventType.BOT_SETUP)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_user_settings():
    """
    Tests that `crud.get_user_settings` queries the database correctly.
    """
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    user_id = 123
    await crud.get_user_settings(mock_db_session, user_id)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_voice_channel_owner():
    """
    Tests that `crud.update_voice_channel_owner` executes an update statement.
    """
    mock_db_session = AsyncMock()
    channel_id = 789
    new_owner_id = 987
    await crud.update_voice_channel_owner(mock_db_session, channel_id, new_owner_id)
    mock_db_session.execute.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_voice_channel():
    """
    Tests that `crud.delete_voice_channel` executes a delete statement.
    """
    mock_db_session = AsyncMock()
    channel_id = 456
    await crud.delete_voice_channel(mock_db_session, channel_id)
    mock_db_session.execute.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_voice_channel():
    """
    Tests that `crud.create_voice_channel` adds a new VoiceChannel object.
    """
    mock_db_session = AsyncMock()
    mock_db_session.add = MagicMock()
    await crud.create_voice_channel(mock_db_session, 1, 2, 3)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_guild_cleanup_flag():
    """
    Tests that `crud.update_guild_cleanup_flag` executes an update statement.
    """
    mock_db_session = AsyncMock()
    guild_id = 123
    await crud.update_guild_cleanup_flag(mock_db_session, guild_id, True)
    mock_db_session.execute.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_get_voice_channels_by_guild():
    """
    Tests that `crud.get_voice_channels_by_guild` queries the database correctly.
    """
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_result
    guild_id = 789
    await crud.get_voice_channels_by_guild(mock_db_session, guild_id)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_all_voice_channels():
    """
    Tests that `crud.get_all_voice_channels` queries the database correctly.
    """
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_db_session.execute.return_value = mock_result
    await crud.get_all_voice_channels(mock_db_session)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_voice_channel():
    """
    Tests that `crud.get_voice_channel` queries the database correctly.
    """
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    channel_id = 456
    await crud.get_voice_channel(mock_db_session, channel_id)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_voice_channel_by_owner():
    """
    Tests that `crud.get_voice_channel_by_owner` queries the database correctly.
    """
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    owner_id = 123
    await crud.get_voice_channel_by_owner(mock_db_session, owner_id)
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_get_guild():
    """
    Tests that `crud.get_guild` correctly queries the database for a guild.
    """
    mock_db_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_db_session.execute.return_value = mock_result
    guild_id = 12345

    await crud.get_guild(mock_db_session, guild_id)

    # Verify that execute was called, indicating a query was made.
    mock_db_session.execute.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_channel_limit_existing_settings():
    """
    Tests that `crud.update_user_channel_limit` correctly updates an existing
    `UserSettings` entry when a user's settings are already present in the DB.
    """
    mock_db_session = AsyncMock()
    user_id = 789
    new_limit = 10
    mock_settings = UserSettings(user_id=user_id, custom_channel_limit=5)

    with patch("database.crud.get_user_settings", return_value=mock_settings):
        await crud.update_user_channel_limit(mock_db_session, user_id, new_limit)

    mock_db_session.execute.assert_called_once()
    mock_db_session.add.assert_not_called()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_channel_limit_new_settings():
    """
    Tests that `crud.update_user_channel_limit` creates new `UserSettings`
    when a user sets a channel limit for the first time (no existing settings).
    It asserts that `db.add` is called for creation.
    """
    mock_db_session = AsyncMock()
    mock_db_session.add = MagicMock()  # Mock `add` synchronously.
    user_id = 456
    new_limit = 5

    # Simulate no existing settings.
    with patch("database.crud.get_user_settings", return_value=None):
        await crud.update_user_channel_limit(mock_db_session, user_id, new_limit)

    # Verify that `db.add` was called.
    mock_db_session.add.assert_called_once()
    # Verify that `db.execute` was NOT called.
    mock_db_session.execute.assert_not_called()
    # Verify that `db.commit` was called.
    mock_db_session.commit.assert_called_once()
