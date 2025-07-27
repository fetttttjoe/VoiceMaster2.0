import pytest
from unittest.mock import patch, AsyncMock

from services.guild_service import GuildService
from database import crud


@pytest.mark.asyncio
async def test_get_guild_config(mock_db_session, mock_voice_channel_service, mock_bot):
    """
    Tests that get_guild_config calls get_guild on its repository.
    """
    # Instantiate the service with all required mocked dependencies.
    guild_service = GuildService(mock_db_session, mock_voice_channel_service, mock_bot)
    
    # Mock the crud function directly
    crud.get_guild = AsyncMock()

    await guild_service.get_guild_config(123)
    # Assert that the method on the MOCKED REPOSITORY was called
    crud.get_guild.assert_called_once_with(mock_db_session, 123)

@pytest.mark.asyncio
async def test_create_or_update_guild(mock_db_session, mock_voice_channel_service, mock_bot):
    """
    Tests that create_or_update_guild calls create_or_update_guild on its repository.
    """
    # Instantiate the service with all required mocked dependencies.
    guild_service = GuildService(mock_db_session, mock_voice_channel_service, mock_bot)
    
    # Mock the crud function directly
    crud.create_or_update_guild = AsyncMock()

    await guild_service.create_or_update_guild(1, 2, 3, 4)
    # Assert that the method on the MOCKED REPOSITORY was called
    crud.create_or_update_guild.assert_called_once_with(mock_db_session, 1, 2, 3, 4)