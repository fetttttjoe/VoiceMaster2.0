import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from discord.ext import commands
from cogs.voice_commands import VoiceCommandsCog
import discord

@pytest.mark.asyncio
async def test_voice_command_sends_embed(mock_bot, mock_ctx):
    cog = VoiceCommandsCog(mock_bot)
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert voice_command is not None
    await voice_command.callback(cog, mock_ctx) # type: ignore
    
    mock_ctx.send.assert_called_once()
    assert 'embed' in mock_ctx.send.call_args[1]

@pytest.mark.asyncio
async def test_lock_command_no_voice_channel(mock_bot, mock_member, mock_ctx):
    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    mock_member.voice = None
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    lock_command = voice_command.get_command('lock')
    assert lock_command is not None
    await lock_command.callback(cog, mock_ctx) # type: ignore
    
    mock_ctx.send.assert_called_with("You are not in a voice channel.")

@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_lock_command_locks_channel(mock_get_session, mock_bot, mock_member, mock_ctx):
    mock_db_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_db_session
    mock_db_session.add = MagicMock() 
    
    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    
    voice_state = mock_member.voice
    voice_state.channel.id = 12345
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    lock_command = voice_command.get_command('lock')
    assert lock_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', new_callable=AsyncMock) as mock_get_owner:
        mock_get_owner.return_value = MagicMock(channel_id=12345)
        await lock_command.callback(cog, mock_ctx) # type: ignore
    
    voice_state.channel.set_permissions.assert_called_once_with(mock_ctx.guild.default_role, connect=False)
    mock_ctx.send.assert_called_with("🔒 Channel locked.")

@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_unlock_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    mock_db_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_db_session
    # Fix: Ensure mock_db_session.add is a synchonous MagicMock to prevent RuntimeWarning
    mock_db_session.add = MagicMock() 
    
    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    
    voice_state = mock_member.voice
    voice_state.channel.id = 12345
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    unlock_command = voice_command.get_command('unlock')
    assert unlock_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', new_callable=AsyncMock) as mock_get_owner:
        mock_get_owner.return_value = MagicMock(channel_id=12345)
        await unlock_command.callback(cog, mock_ctx) # type: ignore
    
    voice_state.channel.set_permissions.assert_called_once_with(mock_ctx.guild.default_role, connect=True)
    mock_ctx.send.assert_called_with("🔓 Channel unlocked.")

@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_permit_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    mock_db_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_db_session
    mock_db_session.add = MagicMock() 
    
    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    
    permitted_member = AsyncMock(spec=discord.Member)
    
    voice_state = mock_member.voice
    voice_state.channel.id = 12345
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    permit_command = voice_command.get_command('permit')
    assert permit_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', new_callable=AsyncMock) as mock_get_owner:
        mock_get_owner.return_value = MagicMock(channel_id=12345)
        await permit_command.callback(cog, mock_ctx, permitted_member) # type: ignore
    
    voice_state.channel.set_permissions.assert_called_once_with(permitted_member, connect=True)
    mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_claim_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    mock_db_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_db_session
    mock_db_session.add = MagicMock() 
    
    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    
    voice_state = mock_member.voice
    voice_state.channel.id = 12345
    voice_state.channel.members = []
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    claim_command = voice_command.get_command('claim')
    assert claim_command is not None
    
    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel', new_callable=AsyncMock) as mock_get_voice_channel:
        mock_get_voice_channel.return_value = MagicMock(channel_id=12345, owner_id=999)
        
        with patch('discord.Guild.get_member', new_callable=MagicMock) as mock_get_member:
            mock_get_member.return_value = None
            
            with patch('services.voice_channel_service.VoiceChannelService.update_voice_channel_owner') as mock_update_owner:
                await claim_command.callback(cog, mock_ctx) # type: ignore
                mock_update_owner.assert_called_once_with(12345, mock_member.id)

    voice_state.channel.set_permissions.assert_called_once_with(mock_member, manage_channels=True, manage_roles=True)
    mock_ctx.send.assert_called_once()