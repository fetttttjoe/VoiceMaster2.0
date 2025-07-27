from unittest.mock import AsyncMock, call

import pytest

from database import crud
from services.guild_service import GuildService


@pytest.mark.asyncio
async def test_get_guild_config(mock_db_session, mock_voice_channel_service, mock_bot):
    """
    Tests that get_guild_config calls get_guild on its repository.
    """
    guild_service = GuildService(mock_db_session, mock_voice_channel_service, mock_bot)
    crud.get_guild = AsyncMock()
    await guild_service.get_guild_config(123)
    crud.get_guild.assert_called_once_with(mock_db_session, 123)


@pytest.mark.asyncio
async def test_create_or_update_guild(mock_db_session, mock_voice_channel_service, mock_bot):
    """
    Tests that create_or_update_guild calls create_or_update_guild on its repository.
    """
    guild_service = GuildService(mock_db_session, mock_voice_channel_service, mock_bot)
    crud.create_or_update_guild = AsyncMock()
    await guild_service.create_or_update_guild(1, 2, 3, 4)
    crud.create_or_update_guild.assert_called_once_with(mock_db_session, 1, 2, 3, 4)


@pytest.mark.asyncio
async def test_cleanup_stale_channels(mock_db_session, mock_voice_channel_service, mock_bot):
    """
    Tests that cleanup_stale_channels correctly calls the voice channel service
    to delete each provided channel ID from the database.
    """
    # Arrange
    channel_ids_to_delete = [10, 20, 30]
    guild_service = GuildService(mock_db_session, mock_voice_channel_service, mock_bot)

    # Act
    await guild_service.cleanup_stale_channels(channel_ids_to_delete)

    # Assert
    # Check that the delete method on the voice channel service was called for each ID
    assert mock_voice_channel_service.delete_voice_channel.call_count == len(channel_ids_to_delete)
    mock_voice_channel_service.delete_voice_channel.assert_has_calls(
        [call(channel_id) for channel_id in channel_ids_to_delete], any_order=True
    )
