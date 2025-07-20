# VoiceMaster2.0/tests/cogs/test_events.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import discord
from cogs.events import EventsCog
from database.models import Guild, AuditLogEventType # Make sure AuditLogEventType is imported
from datetime import datetime # Needed for mocking datetime.now() if used

# Abstractions for type hinting mocks
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from interfaces.audit_log_service import IAuditLogService


@pytest.mark.asyncio
async def test_on_voice_state_update_routes_to_creation(mock_bot):
    """Verifies that joining the creation channel calls the creation handler."""
    # Create mocks for the services required by EventsCog
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)
    
    # Assign services to mock_bot to simulate dependency injection in the bot instance
    # This is important because the bot's setup() function likely assigns these.
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    # Pass the mocks to the EventsCog constructor
    cog = EventsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    member = AsyncMock()
    member.guild.id = 123
    before = AsyncMock(channel=None)
    after = AsyncMock(channel=MagicMock(id=456))

    guild_config = Guild(creation_channel_id=456)

    # Mock the get_guild_config call on the injected service instance
    mock_guild_service.get_guild_config.return_value = guild_config

    with patch.object(cog, '_handle_channel_creation') as mock_handle_create:
        await cog.on_voice_state_update(member, before, after)
        # Verify the internal handler was called with correct arguments
        mock_handle_create.assert_called_once_with(member, guild_config)


@pytest.mark.asyncio
async def test_on_voice_state_update_routes_to_leave(mock_bot):
    """Verifies that leaving a temporary channel calls the leave handler."""
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    cog = EventsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    member = AsyncMock()
    member.guild.id = 123
    before = AsyncMock(channel=MagicMock(id=789))
    after = AsyncMock(channel=None)

    # creation_channel_id is different from the channel being left
    guild_config = Guild(creation_channel_id=456)

    # Mock the get_guild_config call on the injected service instance
    mock_guild_service.get_guild_config.return_value = guild_config
    with patch.object(cog, '_handle_channel_leave') as mock_handle_leave:
        await cog.on_voice_state_update(member, before, after)
        # Verify the internal handler was called with correct arguments
        mock_handle_leave.assert_called_once_with(member, before)


@pytest.mark.asyncio
async def test_handle_channel_leave_deletes_empty_channel(mock_bot):
    """Tests that an empty temporary channel is deleted upon the last user leaving."""
    # Create mocks for the services required by EventsCog
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot for calls originating from decorators/bot itself
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    cog = EventsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")

    # The channel being left is empty. Explicitly set spec=discord.VoiceChannel.
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="TempChannel", members=[])
    before = AsyncMock(channel=before_channel)

    # Directly set return values on the *injected* mock service instance
    mock_voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=member.id)

    # Call the method
    await cog._handle_channel_leave(member, before)

    # Assertions on the *injected* mock instances directly
    mock_voice_channel_service.get_voice_channel.assert_called_once_with(789)
    before_channel.delete.assert_called_once_with(reason="Temporary channel empty.")
    mock_voice_channel_service.delete_voice_channel.assert_called_once_with(789)
    
    # Verify audit log was called twice for USER_LEFT_OWNED_CHANNEL and CHANNEL_DELETED
    assert mock_audit_log_service.log_event.call_count == 2
    assert mock_audit_log_service.log_event.call_args_list[0].kwargs['event_type'] == AuditLogEventType.USER_LEFT_OWNED_CHANNEL
    assert mock_audit_log_service.log_event.call_args_list[1].kwargs['event_type'] == AuditLogEventType.CHANNEL_DELETED


@pytest.mark.asyncio
async def test_handle_channel_leave_does_not_delete_non_empty_channel(mock_bot):
    """Tests that a temporary channel is NOT deleted if other members are still present."""
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    cog = EventsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")

    # The channel still has another member in it. Explicitly set spec=discord.VoiceChannel.
    another_member = MagicMock()
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="TempChannel", members=[another_member])
    before = AsyncMock(channel=before_channel)

    # Directly set return values on the *injected* mock service instance
    mock_voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=member.id)

    # Call the method
    await cog._handle_channel_leave(member, before)

    # Assertions
    mock_voice_channel_service.get_voice_channel.assert_called_once_with(789)
    before_channel.delete.assert_not_called() # Ensure delete was NOT called
    mock_voice_channel_service.delete_voice_channel.assert_not_called() # Ensure delete_voice_channel was NOT called
    
    # Verify audit log was called once for USER_LEFT_OWNED_CHANNEL
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.USER_LEFT_OWNED_CHANNEL


@pytest.mark.asyncio
async def test_handle_channel_creation_moves_user_if_channel_exists(mock_bot):
    """Tests that a user is moved to their existing channel if they already own one."""
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    cog = EventsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")
    # Ensure voice_category_id is provided in guild_config to allow the flow to proceed
    guild_config = Guild(creation_channel_id=456, voice_category_id=111) 

    # Mock the existing channel that the user owns (DB entry)
    existing_channel_db = MagicMock(channel_id=999, name="ExistingChannel")
    # Mock the Discord channel object
    existing_channel_discord = AsyncMock(spec=discord.VoiceChannel, id=999, name="ExistingChannel")
    # Ensure bot.get_channel returns the mocked Discord channel
    mock_bot.get_channel.return_value = existing_channel_discord 

    # Set return values on the *injected* mock service instances
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = existing_channel_db
    mock_voice_channel_service.get_user_settings.return_value = None # Ensure new channel creation path is not taken

    # Call the method
    await cog._handle_channel_creation(member, guild_config)

    # Assertions
    mock_voice_channel_service.get_voice_channel_by_owner.assert_called_once_with(member.id)
    member.move_to.assert_called_once_with(
        existing_channel_discord, reason="User already has a channel.")
    
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.USER_MOVED_TO_EXISTING_CHANNEL

    # Ensure other paths' service calls were not made
    mock_voice_channel_service.delete_voice_channel.assert_not_called()
    member.guild.create_voice_channel.assert_not_called()
    mock_voice_channel_service.create_voice_channel.assert_not_called()


@pytest.mark.asyncio
async def test_handle_channel_creation_cleans_up_stale_channel(mock_bot):
    """Tests that a stale DB entry is removed if the channel doesn't exist on Discord."""
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    cog = EventsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")
    # Ensure voice_category_id is provided
    guild_config = Guild(creation_channel_id=456, voice_category_id=111) 

    # Mock a channel that exists in the DB but not on Discord
    existing_channel_db = MagicMock(channel_id=999)
    mock_bot.get_channel.return_value = None  # Simulate Discord channel not found

    # Set return values on the *injected* mock service instances
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = existing_channel_db
    mock_voice_channel_service.get_user_settings.return_value = None # Ensure new channel creation path is not taken

    # Call the method
    await cog._handle_channel_creation(member, guild_config)

    # Assertions
    mock_voice_channel_service.get_voice_channel_by_owner.assert_called_once_with(member.id)
    mock_voice_channel_service.delete_voice_channel.assert_called_once_with(existing_channel_db.channel_id)
    
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.STALE_CHANNEL_CLEANUP

    # Ensure other paths' service calls were not made
    member.move_to.assert_not_called()
    member.guild.create_voice_channel.assert_not_called()
    mock_voice_channel_service.create_voice_channel.assert_not_called()


@pytest.mark.asyncio
async def test_handle_channel_creation_fails_if_category_not_found(mock_bot):
    """Tests that channel creation is aborted if the configured category is not found."""
    mock_guild_service = AsyncMock(spec=IGuildService)
    mock_voice_channel_service = AsyncMock(spec=IVoiceChannelService)
    mock_audit_log_service = AsyncMock(spec=IAuditLogService)

    # Assign services to mock_bot
    mock_bot.guild_service = mock_guild_service
    mock_bot.voice_channel_service = mock_voice_channel_service
    mock_bot.audit_log_service = mock_audit_log_service

    cog = EventsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)
    member = AsyncMock(id=1, guild=MagicMock())
    guild_config = Guild(creation_channel_id=456, voice_category_id=111)

    # Simulate category not being found by bot.get_channel
    mock_bot.get_channel.return_value = None

    # Set return values on the *injected* mock service instances
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = None # No existing channel
    mock_voice_channel_service.get_user_settings.return_value = None # No custom settings

    # Call the method
    await cog._handle_channel_creation(member, guild_config)

    # Assertions
    mock_voice_channel_service.get_voice_channel_by_owner.assert_called_once_with(member.id)
    mock_voice_channel_service.get_user_settings.assert_called_once_with(member.id)

    # Ensure no channel was created on Discord or in DB
    member.guild.create_voice_channel.assert_not_called()
    mock_voice_channel_service.create_voice_channel.assert_not_called()

    # Verify audit log was called for CATEGORY_NOT_FOUND
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.CATEGORY_NOT_FOUND