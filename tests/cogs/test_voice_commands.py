# VoiceMaster2.0/tests/cogs/test_voice_commands.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from discord.ext import commands
from cogs.voice_commands import VoiceCommandsCog
import discord
from typing import cast, Callable, Any


@pytest.mark.asyncio
async def test_voice_command_sends_embed(mock_bot, mock_ctx):
    cog = VoiceCommandsCog(mock_bot)
    voice_command = next(cmd for cmd in cog.get_commands()
                         if cmd.name == 'voice')
    assert voice_command is not None

    callback = cast(Callable[..., Any], voice_command.callback)
    await callback(cog, mock_ctx)

    mock_ctx.send.assert_called_once()
    assert 'embed' in mock_ctx.send.call_args[1]


@pytest.mark.asyncio
async def test_lock_command_no_voice_channel(mock_bot, mock_member, mock_ctx):
    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    mock_member.voice = None

    voice_command = next(cmd for cmd in cog.get_commands()
                         if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    lock_command = voice_command.get_command('lock')
    assert lock_command is not None

    callback = cast(Callable[..., Any], lock_command.callback)
    await callback(cog, mock_ctx)

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

    voice_command = next(cmd for cmd in cog.get_commands()
                         if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    lock_command = voice_command.get_command('lock')
    assert lock_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', new_callable=AsyncMock) as mock_get_owner:
        mock_get_owner.return_value = MagicMock(channel_id=12345)
        callback = cast(Callable[..., Any], lock_command.callback)
        await callback(cog, mock_ctx)

    voice_state.channel.set_permissions.assert_called_once_with(
        mock_ctx.guild.default_role, connect=False)
    mock_ctx.send.assert_called_with("🔒 Channel locked.")


@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_unlock_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    mock_db_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_db_session
    mock_db_session.add = MagicMock()

    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member

    voice_state = mock_member.voice
    voice_state.channel.id = 12345

    voice_command = next(cmd for cmd in cog.get_commands()
                         if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    unlock_command = voice_command.get_command('unlock')
    assert unlock_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', new_callable=AsyncMock) as mock_get_owner:
        mock_get_owner.return_value = MagicMock(channel_id=12345)
        callback = cast(Callable[..., Any], unlock_command.callback)
        await callback(cog, mock_ctx)

    voice_state.channel.set_permissions.assert_called_once_with(
        mock_ctx.guild.default_role, connect=True)
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

    voice_command = next(cmd for cmd in cog.get_commands()
                         if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    permit_command = voice_command.get_command('permit')
    assert permit_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', new_callable=AsyncMock) as mock_get_owner:
        mock_get_owner.return_value = MagicMock(channel_id=12345)
        callback = cast(Callable[..., Any], permit_command.callback)
        await callback(cog, mock_ctx, permitted_member)

    voice_state.channel.set_permissions.assert_called_once_with(
        permitted_member, connect=True)
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

    voice_command = next(cmd for cmd in cog.get_commands()
                         if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    claim_command = voice_command.get_command('claim')
    assert claim_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel', new_callable=AsyncMock) as mock_get_voice_channel:
        mock_get_voice_channel.return_value = MagicMock(
            channel_id=12345, owner_id=999)

        with patch('discord.Guild.get_member', new_callable=MagicMock) as mock_get_member:
            mock_get_member.return_value = None

            with patch('services.voice_channel_service.VoiceChannelService.update_voice_channel_owner') as mock_update_owner:
                callback = cast(Callable[..., Any], claim_command.callback)
                await callback(cog, mock_ctx)
                mock_update_owner.assert_called_once_with(
                    12345, mock_member.id)

    voice_state.channel.set_permissions.assert_called_once_with(
        mock_member, manage_channels=True, manage_roles=True)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_name_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    mock_db_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_db_session
    mock_db_session.add = MagicMock()

    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member

    new_name = "Test Channel"

    voice_command = next(cmd for cmd in cog.get_commands()
                         if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    name_command = voice_command.get_command('name')
    assert name_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.update_user_channel_name') as mock_update_name, \
            patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', return_value=None):  # Simulate no current channel
        callback = cast(Callable[..., Any], name_command.callback)
        await callback(cog, mock_ctx, new_name=new_name)

    mock_update_name.assert_called_once_with(mock_member.id, new_name)
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_limit_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    mock_db_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_db_session
    mock_db_session.add = MagicMock()

    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member

    new_limit = 5

    voice_command = next(cmd for cmd in cog.get_commands()
                         if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    limit_command = voice_command.get_command('limit')
    assert limit_command is not None

    with patch('services.voice_channel_service.VoiceChannelService.update_user_channel_limit') as mock_update_limit, \
            patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', return_value=None):  # Simulate no current channel
        callback = cast(Callable[..., Any], limit_command.callback)
        await callback(cog, mock_ctx, new_limit=new_limit)

    mock_update_limit.assert_called_once_with(mock_member.id, new_limit)
    mock_ctx.send.assert_called_once()
