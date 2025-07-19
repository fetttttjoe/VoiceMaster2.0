# VoiceMaster2.0/tests/cogs/test_events.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from cogs.events import EventsCog
from database.models import Guild

@pytest.mark.asyncio
async def test_on_voice_state_update_user_joins_create_channel(mock_bot):
    cog = EventsCog(mock_bot)
    member = AsyncMock()
    member.guild.id = 123
    before = AsyncMock()
    before.channel = None
    after = AsyncMock()
    after.channel.id = 456

    guild_config = Guild(creation_channel_id=456)

    with patch('database.database.db.get_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        
        with patch('services.guild_service.GuildService.get_guild_config', return_value=guild_config):
            with patch('cogs.events.EventsCog.handle_create_channel') as mock_handle_create:
                await cog.on_voice_state_update(member, before, after)
                mock_handle_create.assert_called_once()

@pytest.mark.asyncio
async def test_on_voice_state_update_user_leaves_temp_channel(mock_bot):
    cog = EventsCog(mock_bot)
    member = AsyncMock()
    member.guild.id = 123
    
    before = AsyncMock()
    before.channel.id = 789
    before.channel.members = []
    
    after = AsyncMock()
    after.channel = None

    guild_config = Guild(creation_channel_id=456)

    with patch('database.database.db.get_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session
        mock_session.add = MagicMock() 
        
        with patch('services.guild_service.GuildService.get_guild_config', return_value=guild_config):
            with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel', return_value=MagicMock(channel_id=789, owner_id=member.id)):
                with patch('services.voice_channel_service.VoiceChannelService.delete_voice_channel') as mock_delete:
                    await cog.on_voice_state_update(member, before, after)
                    before.channel.delete.assert_called_once()
                    mock_delete.assert_called_once_with(789)