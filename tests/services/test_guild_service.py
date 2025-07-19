import pytest
from unittest.mock import patch, AsyncMock
from services.guild_service import GuildService

@pytest.mark.asyncio
async def test_get_guild_config(mock_db_session):
    with patch('database.crud.get_guild', new_callable=AsyncMock) as mock_get_guild:
        guild_service = GuildService(mock_db_session)
        await guild_service.get_guild_config(123)
        mock_get_guild.assert_called_once_with(mock_db_session, 123)

@pytest.mark.asyncio
async def test_create_or_update_guild(mock_db_session):
    with patch('database.crud.create_or_update_guild', new_callable=AsyncMock) as mock_create_or_update_guild:
        guild_service = GuildService(mock_db_session)
        await guild_service.create_or_update_guild(1, 2, 3, 4)
        mock_create_or_update_guild.assert_called_once_with(mock_db_session, 1, 2, 3, 4)