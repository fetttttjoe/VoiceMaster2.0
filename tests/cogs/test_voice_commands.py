# VoiceMaster2.0/tests/cogs/test_voice_commands.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from discord.ext import commands
import discord
import asyncio
from typing import cast, Callable, Any

# Import the Cog from the correct path
from cogs.voice_commands import VoiceCommandsCog

# Import Abstractions for proper type hinting of mocks
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from interfaces.audit_log_service import IAuditLogService
from database.models import AuditLogEventType # For audit log events


##
## MOCK FIXTURES
##

@pytest.fixture
def mock_bot():
    """Fixture for a mocked Discord bot instance."""
    # Removed spec=commands.Bot to allow dynamic attribute assignment for custom services
    return AsyncMock()

@pytest.fixture
def mock_ctx(mock_bot): # Pass mock_bot as a fixture to mock_ctx
    """Fixture for a mocked context (ctx) object."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.bot = mock_bot # Assign the mocked bot here
    ctx.guild = AsyncMock(spec=discord.Guild)
    ctx.author = AsyncMock(spec=discord.Member)
    ctx.author.guild = ctx.guild
    ctx.guild.id = 12345
    ctx.guild.default_role = MagicMock(spec=discord.Role)
    ctx.prefix = "."
    # No need to mock ctx.bot.get_channel or get_user here directly,
    # as mock_bot fixture itself will have these if needed.
    return ctx

@pytest.fixture
def mock_member(mock_ctx):
    """Fixture for a mocked member, including a voice state."""
    member = AsyncMock(spec=discord.Member)
    member.id = 54321
    member.display_name = "TestUser" # Added for audit logs
    member.mention = "<@54321>" # Added for audit logs
    member.voice = AsyncMock()
    member.voice.channel = AsyncMock(spec=discord.VoiceChannel)
    member.voice.channel.id = 98765
    member.voice.channel.name = "TestChannel" # Added for audit logs
    member.voice.channel.user_limit = 0 # Added for limit command
    member.guild = mock_ctx.guild
    return member

##
## TEST CASES
##

@pytest.mark.asyncio
async def test_voice_command_sends_embed(mock_bot, mock_ctx):
    """Tests that the base 'voice' command sends an informational embed."""
    # Create dummy mocks for services, as this test doesn't directly interact with them
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator or bot-level service access)
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    voice_command = next((cmd for cmd in cog.get_commands() if cmd.name == 'voice'), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)

    if voice_command.invoke_without_command:
        callback = cast(Callable[..., Any], voice_command.callback)
        await callback(cog, mock_ctx)
        mock_ctx.send.assert_called_once()
        assert 'embed' in mock_ctx.send.call_args.kwargs

@pytest.mark.asyncio
@patch('database.database.db.get_session') # Keep this if db.get_session is still directly used by the decorator
async def test_lock_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    """Tests that the 'lock' command successfully locks the channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()

    # Create mocks for the services and pass them to the cog constructor
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator or bot-level service access)
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    # Set return values directly on the *injected* mock_voice_channel_service instance
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    mock_ctx.author = mock_member
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    lock_command = voice_command.get_command('lock')
    assert lock_command is not None
    
    callback = cast(Callable[..., Any], lock_command.callback)
    await callback(cog, mock_ctx)
    
    mock_member.voice.channel.set_permissions.assert_called_once_with(mock_ctx.guild.default_role, connect=False)
    mock_ctx.send.assert_called_with("🔒 Channel locked.", ephemeral=True)
    # Assert on the *injected* mock_audit_log_service
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.CHANNEL_LOCKED

@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_unlock_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    """Tests that the 'unlock' command successfully unlocks the channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    
    # Create mocks for the services and pass them to the cog
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator)
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    # Set return values directly on the *injected* mock_voice_channel_service instance
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)
    
    cog = VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    mock_ctx.author = mock_member

    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    unlock_command = voice_command.get_command('unlock')
    assert unlock_command is not None

    callback = cast(Callable[..., Any], unlock_command.callback)
    await callback(cog, mock_ctx)

    mock_member.voice.channel.set_permissions.assert_called_once_with(mock_ctx.guild.default_role, connect=True)
    mock_ctx.send.assert_called_with("🔓 Channel unlocked.", ephemeral=True)
    # Assert on the *injected* mock_audit_log_service
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.CHANNEL_UNLOCKED


@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_permit_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    """Tests that the 'permit' command grants connect permissions."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    
    # Create mocks for the services and pass them to the cog
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator)
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    # Set return values directly on the *injected* mock_voice_channel_service instance
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    mock_ctx.author = mock_member
    permitted_member = AsyncMock(spec=discord.Member)
    permitted_member.mention = "<@12345>" # Added for audit log


    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    permit_command = voice_command.get_command('permit')
    assert permit_command is not None

    callback = cast(Callable[..., Any], permit_command.callback)
    await callback(cog, mock_ctx, member=permitted_member)

    mock_member.voice.channel.set_permissions.assert_called_once_with(permitted_member, connect=True)
    mock_ctx.send.assert_called_once()
    # Assert on the *injected* mock_audit_log_service
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.CHANNEL_PERMIT


@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_claim_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    """Tests that a user can claim an abandoned channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    
    # Create mocks for the services and pass them to the cog
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator)
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    # Set return values directly on the *injected* mock_voice_channel_service instance
    mock_voice_channel_service.get_voice_channel.return_value = MagicMock(owner_id=999) # Set initial owner
    mock_voice_channel_service.update_voice_channel_owner.return_value = None # This is a simple update, no specific return needed


    cog = VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    mock_ctx.author = mock_member
    mock_member.voice.channel.members = [] # Ensure channel is empty for claim logic

    with patch('discord.Guild.get_member', return_value=None): # Mock get_member if needed by the bot
        voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
        assert isinstance(voice_command, commands.Group)
        claim_command = voice_command.get_command('claim')
        assert claim_command is not None

        callback = cast(Callable[..., Any], claim_command.callback)
        await callback(cog, mock_ctx)

        mock_voice_channel_service.update_voice_channel_owner.assert_called_once_with(mock_member.voice.channel.id, mock_member.id)
        mock_member.voice.channel.set_permissions.assert_called_once_with(mock_member, manage_channels=True, manage_roles=True)
        mock_ctx.send.assert_called_once()
        # Assert on the *injected* mock_audit_log_service
        mock_audit_log_service.log_event.assert_called_once()
        assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.CHANNEL_CLAIMED


@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_name_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    """Tests updating a user's future channel name."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    
    # Create mocks for the services and pass them to the cog
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator)
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    # Set return values directly on the *injected* mock_voice_channel_service instance
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = None # Simulate no existing owned channel
    mock_voice_channel_service.update_user_channel_name.return_value = None # This is a simple update, no specific return needed

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    mock_ctx.author = mock_member
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    name_command = voice_command.get_command('name')
    assert name_command is not None

    callback = cast(Callable[..., Any], name_command.callback)
    await callback(cog, mock_ctx, new_name="My Awesome Channel")
    
    mock_voice_channel_service.update_user_channel_name.assert_called_once_with(mock_member.id, "My Awesome Channel")
    mock_ctx.send.assert_called_once()
    # Assert on the *injected* mock_audit_log_service
    mock_audit_log_service.log_event.assert_called_once() # Verify audit log was called
    # Check that the correct event type was logged
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.USER_DEFAULT_NAME_SET


@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_limit_command(mock_get_session, mock_bot, mock_member, mock_ctx):
    """Tests updating a user's future channel limit."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    
    # Create mocks for the services and pass them to the cog
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator)
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    # Set return values directly on the *injected* mock_voice_channel_service instance
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = None # Simulate no existing owned channel
    mock_voice_channel_service.update_user_channel_limit.return_value = None # This is a simple update, no specific return needed

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    mock_ctx.author = mock_member
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    limit_command = voice_command.get_command('limit')
    assert limit_command is not None

    callback = cast(Callable[..., Any], limit_command.callback)
    await callback(cog, mock_ctx, new_limit=5)

    mock_voice_channel_service.update_user_channel_limit.assert_called_once_with(mock_member.id, 5)
    mock_ctx.send.assert_called_once()
    # Assert on the *injected* mock_audit_log_service
    mock_audit_log_service.log_event.assert_called_once() # Verify audit log was called
    # Check that the correct event type was logged
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.USER_DEFAULT_LIMIT_SET


@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_setup_command(mock_get_session, mock_bot, mock_ctx):
    """Tests the entire multi-step setup process."""
    mock_get_session.return_value.__aenter__.return_value.add = AsyncMock()
    
    # Create actual mocks for the services that will be injected
    mock_guild_service_instance = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService) # Still need to pass this, even if not directly used by setup
    mock_audit_log_service_instance = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator and other bot interactions)
    mock_bot.guild_service = mock_guild_service_instance
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service_instance

    # Pass the mock instances to the cog constructor
    cog = VoiceCommandsCog(mock_bot, mock_guild_service_instance, mock_voice_channel_service, mock_audit_log_service_instance)

    # Mock bot.wait_for calls for user input during setup
    mock_bot.wait_for.side_effect = [
        AsyncMock(spec=discord.Message, content="Temp Channels"), # Response for category name
        AsyncMock(spec=discord.Message, content="Join to Create") # Response for creation channel name
    ]
    
    # Mock return values for discord.py interactions
    mock_category = AsyncMock(spec=discord.CategoryChannel, id=777) # Give it an ID
    mock_ctx.guild.create_category.return_value = mock_category
    mock_ctx.guild.create_voice_channel.return_value = AsyncMock(spec=discord.VoiceChannel, id=888) # Give it an ID

    # Mock the return value for the guild service's create_or_update_guild
    mock_guild_service_instance.create_or_update_guild.return_value = MagicMock(
        guild_id=mock_ctx.guild.id,
        voice_category_id=mock_category.id,
        creation_channel_id=888 # The ID of the created voice channel
    )
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    setup_command = voice_command.get_command('setup')
    assert setup_command is not None

    callback = cast(Callable[..., Any], setup_command.callback)
    await callback(cog, mock_ctx)

    # Assertions on mock Discord interactions
    mock_ctx.guild.create_category.assert_called_once_with(name="Temp Channels")
    mock_ctx.guild.create_voice_channel.assert_called_once_with(name="Join to Create", category=mock_category)
    
    # Assertions on injected service mocks
    mock_guild_service_instance.create_or_update_guild.assert_called_once()
    mock_audit_log_service_instance.log_event.assert_called_once()
    
    # Assertions on ctx.send messages
    assert mock_ctx.send.call_count >= 3
    assert mock_audit_log_service_instance.log_event.call_args.kwargs['event_type'] == AuditLogEventType.BOT_SETUP


@pytest.mark.asyncio
async def test_edit_command_no_subcommand(mock_bot, mock_ctx):
    """Tests that the edit command prompts for a subcommand if none is given."""
    # Create dummy mocks for services
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator)
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    edit_command = voice_command.get_command('edit')
    assert edit_command is not None
    
    callback = cast(Callable[..., Any], edit_command.callback)
    await callback(cog, mock_ctx)
    mock_ctx.send.assert_called_with("Please specify what you want to edit. Use `.voice edit rename` or `.voice edit select`.")

@pytest.mark.asyncio
@patch('database.database.db.get_session')
async def test_list_command(mock_get_session, mock_bot, mock_ctx):
    """Tests the list command for active channels."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    
    # Create actual mocks for the services that will be injected
    mock_guild_service_instance = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot (crucial for audit_decorator)
    mock_bot.guild_service = mock_guild_service_instance
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    # Set return value on the *injected* mock_guild_service_instance
    mock_guild_service_instance.get_all_voice_channels.return_value = [
        MagicMock(channel_id=1, owner_id=10),
        MagicMock(channel_id=2, owner_id=20)
    ]
    # Mock bot.get_channel and bot.get_user for the list command's internal logic
    mock_ctx.guild.get_channel.return_value = AsyncMock(spec=discord.VoiceChannel, name="Channel1", mention="<#1>", guild=mock_ctx.guild)
    mock_bot.get_user.side_effect = [AsyncMock(spec=discord.User, mention="<@10>"), AsyncMock(spec=discord.User, mention="<@20>")]


    cog = VoiceCommandsCog(mock_bot, mock_guild_service_instance, mock_voice_channel_service, mock_audit_log_service)
    
    voice_command = next(cmd for cmd in cog.get_commands() if cmd.name == 'voice')
    assert isinstance(voice_command, commands.Group)
    list_command = voice_command.get_command('list')
    assert list_command is not None

    callback = cast(Callable[..., Any], list_command.callback)
    await callback(cog, mock_ctx)

    mock_ctx.send.assert_called_once()
    assert 'embed' in mock_ctx.send.call_args.kwargs
    # Assert on the *injected* mock_audit_log_service
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.LIST_CHANNELS