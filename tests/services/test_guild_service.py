import pytest
from unittest.mock import patch, AsyncMock

from services.guild_service import GuildService
from interfaces.guild_repository import IGuildRepository


@pytest.mark.asyncio
async def test_get_guild_config(mock_guild_repository, mock_voice_channel_service, mock_bot):
    """
    Tests that get_guild_config calls get_guild on its repository.
    """
    # Instantiate the service with all required mocked dependencies.
    guild_service = GuildService(mock_guild_repository, mock_voice_channel_service, mock_bot)
    await guild_service.get_guild_config(123)
    # Assert that the method on the MOCKED REPOSITORY was called
    mock_guild_repository.get_guild.assert_called_once_with(123)

@pytest.mark.asyncio
async def test_create_or_update_guild(mock_guild_repository, mock_voice_channel_service, mock_bot):
    """
    Tests that create_or_update_guild calls create_or_update_guild on its repository.
    """
    # Instantiate the service with all required mocked dependencies.
    guild_service = GuildService(mock_guild_repository, mock_voice_channel_service, mock_bot)
    await guild_service.create_or_update_guild(1, 2, 3, 4)
    # Assert that the method on the MOCKED REPOSITORY was called
    mock_guild_repository.create_or_update_guild.assert_called_once_with(1, 2, 3, 4)