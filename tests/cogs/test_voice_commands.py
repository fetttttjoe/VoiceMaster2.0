# VoiceMaster2.0/tests/cogs/test_voice_commands.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from discord.ext import commands
import discord
import asyncio
from typing import cast, Callable, Any

# Import the Cog from the correct path
from cogs.voice_commands import VoiceCommandsCog

##
## MOCK FIXTURES
##

@pytest.fixture
def mock_bot():
    """Fixture for a mocked Discord bot instance."""
    return AsyncMock(spec=commands.Bot)

@pytest.fixture
def mock_ctx():
    """Fixture for a mocked context (ctx) object."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.guild = AsyncMock(spec=discord.Guild)
    ctx.author = AsyncMock(spec=discord.Member)
    ctx.author.guild = ctx.guild
    ctx.guild.id = 12345
    ctx.guild.default_role = MagicMock(spec=discord.Role)
    return ctx

@pytest.fixture
def mock_member(mock_ctx):
    """Fixture for a mocked member, including a voice state."""
    member = AsyncMock(spec=discord.Member)
    member.id = 54321
    member.voice = AsyncMock()
    member.voice.channel = AsyncMock(spec=discord.VoiceChannel)
    member.voice.channel.id = 98765
    member.guild = mock_ctx.guild
    return member

##
## TEST CASES
##

@pytest.mark.asyncio
async def test_voice_command_sends_embed(mock_bot, mock_ctx):
    """Tests that the base 'voice' command sends an informational embed."""
    cog = VoiceCommandsCog(mock_bot)
    voice_command = next((cmd for cmd in cog.get_commands() if cmd.name == 'voice'), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)

    if voice_command.invoke_without_command:
        callback = cast(Callable[..., Any], voice_command.callback)
        await callback(cog, mock_ctx)
        mock_ctx.send.assert_called_once()
        assert 'embed' in mock_ctx.send.call_args.kwargs

@pytest.mark.asyncio
@patch('cogs.voice_commands.VoiceChannelService', autospec=True)
@patch('database.database.db.get_session')
async def test_lock_command(mock_get_session, MockVoiceChannelService, mock_bot, mock_member, mock_ctx):
    """Tests that the 'lock' command successfully locks the channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_service_instance = MockVoiceChannelService.return_value
    mock_service_instance.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)

    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    lock_command = voice_command.get_command('lock')
    assert lock_command is not None
    
    callback = cast(Callable[..., Any], lock_command.callback)
    await callback(cog, mock_ctx)
    
    mock_member.voice.channel.set_permissions.assert_called_once_with(mock_ctx.guild.default_role, connect=False)
    mock_ctx.send.assert_called_with("🔒 Channel locked.")

@pytest.mark.asyncio
@patch('cogs.voice_commands.VoiceChannelService', autospec=True)
@patch('database.database.db.get_session')
async def test_unlock_command(mock_get_session, MockVoiceChannelService, mock_bot, mock_member, mock_ctx):
    """Tests that the 'unlock' command successfully unlocks the channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_service_instance = MockVoiceChannelService.return_value
    mock_service_instance.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)
    
    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member

    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    unlock_command = voice_command.get_command('unlock')
    assert unlock_command is not None

    callback = cast(Callable[..., Any], unlock_command.callback)
    await callback(cog, mock_ctx)

    mock_member.voice.channel.set_permissions.assert_called_once_with(mock_ctx.guild.default_role, connect=True)
    mock_ctx.send.assert_called_with("🔓 Channel unlocked.")

@pytest.mark.asyncio
@patch('cogs.voice_commands.VoiceChannelService', autospec=True)
@patch('database.database.db.get_session')
async def test_permit_command(mock_get_session, MockVoiceChannelService, mock_bot, mock_member, mock_ctx):
    """Tests that the 'permit' command grants connect permissions."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_service_instance = MockVoiceChannelService.return_value
    mock_service_instance.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)

    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    permitted_member = AsyncMock(spec=discord.Member)

    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    permit_command = voice_command.get_command('permit')
    assert permit_command is not None

    callback = cast(Callable[..., Any], permit_command.callback)
    await callback(cog, mock_ctx, member=permitted_member)

    mock_member.voice.channel.set_permissions.assert_called_once_with(permitted_member, connect=True)
    mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
@patch('cogs.voice_commands.VoiceChannelService', autospec=True)
@patch('database.database.db.get_session')
async def test_claim_command(mock_get_session, MockVoiceChannelService, mock_bot, mock_member, mock_ctx):
    """Tests that a user can claim an abandoned channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_service_instance = MockVoiceChannelService.return_value
    mock_service_instance.get_voice_channel.return_value = MagicMock(owner_id=999)

    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    mock_member.voice.channel.members = []

    with patch('discord.Guild.get_member', return_value=None):
        voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
        assert isinstance(voice_command, commands.Group)
        claim_command = voice_command.get_command('claim')
        assert claim_command is not None

        callback = cast(Callable[..., Any], claim_command.callback)
        await callback(cog, mock_ctx)

        mock_service_instance.update_voice_channel_owner.assert_called_once_with(mock_member.voice.channel.id, mock_member.id)
        mock_member.voice.channel.set_permissions.assert_called_once_with(mock_member, manage_channels=True, manage_roles=True)
        mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
@patch('cogs.voice_commands.VoiceChannelService', autospec=True)
@patch('database.database.db.get_session')
async def test_name_command(mock_get_session, MockVoiceChannelService, mock_bot, mock_member, mock_ctx):
    """Tests updating a user's future channel name."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_service_instance = MockVoiceChannelService.return_value
    mock_service_instance.get_voice_channel_by_owner.return_value = None

    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    name_command = voice_command.get_command('name')
    assert name_command is not None

    callback = cast(Callable[..., Any], name_command.callback)
    await callback(cog, mock_ctx, new_name="My Awesome Channel")
    
    mock_service_instance.update_user_channel_name.assert_called_once_with(mock_member.id, "My Awesome Channel")
    mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
@patch('cogs.voice_commands.VoiceChannelService', autospec=True)
@patch('database.database.db.get_session')
async def test_limit_command(mock_get_session, MockVoiceChannelService, mock_bot, mock_member, mock_ctx):
    """Tests updating a user's future channel limit."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_service_instance = MockVoiceChannelService.return_value
    mock_service_instance.get_voice_channel_by_owner.return_value = None

    cog = VoiceCommandsCog(mock_bot)
    mock_ctx.author = mock_member
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    limit_command = voice_command.get_command('limit')
    assert limit_command is not None

    callback = cast(Callable[..., Any], limit_command.callback)
    await callback(cog, mock_ctx, new_limit=5)

    mock_service_instance.update_user_channel_limit.assert_called_once_with(mock_member.id, 5)
    mock_ctx.send.assert_called_once()

@pytest.mark.asyncio
@patch('cogs.voice_commands.AuditLogService', autospec=True)
@patch('cogs.voice_commands.GuildService', autospec=True)
@patch('database.database.db.get_session')
async def test_setup_command(mock_get_session, MockGuildService, MockAuditLogService, mock_bot, mock_ctx):
    """Tests the entire multi-step setup process."""
    mock_get_session.return_value.__aenter__.return_value.add = AsyncMock()
    
    mock_guild_service_instance = MockGuildService.return_value
    mock_guild_service_instance.create_or_update_guild = AsyncMock()
    
    mock_audit_log_service_instance = MockAuditLogService.return_value
    mock_audit_log_service_instance.log_event = AsyncMock()

    cog = VoiceCommandsCog(mock_bot)

    # FIX: Use asyncio.Future to create awaitable side effects
    def create_future(result):
        future = asyncio.Future()
        future.set_result(result)
        return future

    mock_bot.wait_for.side_effect = [
        create_future(MagicMock(spec=discord.Message, content="Temp Channels")),
        create_future(MagicMock(spec=discord.Message, content="Join to Create"))
    ]
    
    mock_category = AsyncMock(spec=discord.CategoryChannel)
    mock_ctx.guild.create_category.return_value = mock_category
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    setup_command = voice_command.get_command('setup')
    assert setup_command is not None

    callback = cast(Callable[..., Any], setup_command.callback)
    await callback(cog, mock_ctx)

    mock_ctx.guild.create_category.assert_called_once_with(name="Temp Channels")
    mock_ctx.guild.create_voice_channel.assert_called_once_with(name="Join to Create", category=mock_category)
    mock_guild_service_instance.create_or_update_guild.assert_called_once()
    mock_audit_log_service_instance.log_event.assert_called_once()
    assert mock_ctx.send.call_count >= 3

@pytest.mark.asyncio
async def test_edit_command_no_subcommand(mock_bot, mock_ctx):
    """Tests that the edit command prompts for a subcommand if none is given."""
    cog = VoiceCommandsCog(mock_bot)
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    edit_command = voice_command.get_command('edit')
    assert edit_command is not None
    
    callback = cast(Callable[..., Any], edit_command.callback)
    await callback(cog, mock_ctx)
    mock_ctx.send.assert_called_with("Please specify what you want to edit. Use `.voice edit rename` or `.voice edit select`.")

@pytest.mark.asyncio
@patch('cogs.voice_commands.GuildService', autospec=True)
@patch('database.database.db.get_session')
async def test_list_command(mock_get_session, MockGuildService, mock_bot, mock_ctx):
    """Tests the list command for active channels."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_service_instance = MockGuildService.return_value
    mock_service_instance.get_all_voice_channels.return_value = [
        AsyncMock(channel_id=1, owner_id=10),
        AsyncMock(channel_id=2, owner_id=20)
    ]

    cog = VoiceCommandsCog(mock_bot)
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    list_command = voice_command.get_command('list')
    assert list_command is not None

    callback = cast(Callable[..., Any], list_command.callback)
    await callback(cog, mock_ctx)

    mock_ctx.send.assert_called_once()
    assert 'embed' in mock_ctx.send.call_args.kwargs