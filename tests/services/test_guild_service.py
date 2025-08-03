from unittest.mock import call

import pytest

from services.guild_service import GuildService


@pytest.mark.asyncio
async def test_get_guild_config(mock_guild_repository, mock_voice_channel_service, mock_bot):
    """
    Tests that get_guild_config calls get_guild_config on its repository.
    """
    guild_service = GuildService(mock_guild_repository, mock_voice_channel_service, mock_bot)
    await guild_service.get_guild_config(123)
    mock_guild_repository.get_guild_config.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_create_or_update_guild(mock_guild_repository, mock_voice_channel_service, mock_bot):
    """
    Tests that create_or_update_guild calls create_or_update_guild on its repository.
    """
    guild_service = GuildService(mock_guild_repository, mock_voice_channel_service, mock_bot)
    await guild_service.create_or_update_guild(1, 2, 3, 4)
    mock_guild_repository.create_or_update_guild.assert_called_once_with(1, 2, 3, 4)


@pytest.mark.asyncio
async def test_cleanup_stale_channels(mock_guild_repository, mock_voice_channel_service, mock_bot):
    """
    Tests that cleanup_stale_channels correctly calls the voice channel service
    to delete each provided channel ID from the database.
    """
    # Arrange
    channel_ids_to_delete = [10, 20, 30]
    guild_service = GuildService(mock_guild_repository, mock_voice_channel_service, mock_bot)

    # Act
    await guild_service.cleanup_stale_channels(channel_ids_to_delete)

    # Assert
    # Check that the delete method on the voice channel service was called for each ID
    assert mock_voice_channel_service.delete_voice_channel.call_count == len(channel_ids_to_delete)
    mock_voice_channel_service.delete_voice_channel.assert_has_calls(
        [call(channel_id) for channel_id in channel_ids_to_delete], any_order=True
    )
