# tests/cogs/test_events_extended.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

import discord

from cogs.events import EventsCog
from database.models import AuditLogEventType, Guild, UserSettings


@pytest.mark.asyncio
async def test_handle_channel_leave_stale_channel_cleanup(mock_bot):
    """
    Tests that a stale DB entry is cleaned up if the channel is already
    deleted from Discord when the bot tries to delete it.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)

    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))

    # Simulate a channel that is empty
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="Old Channel", members=[])
    before_channel.guild.id = 123
    before_channel.name = "Old Channel"
    before_state = AsyncMock(spec=discord.VoiceState, channel=before_channel)

    # The channel exists in our database
    mock_bot.voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=member.id)

    # Simulate that the channel is NOT FOUND when we try to delete it on Discord
    before_channel.delete.side_effect = discord.NotFound(response=MagicMock(), message="Channel not found")

    # Act
    await cog._handle_channel_leave(member, before_state)

    # Assert
    before_channel.delete.assert_called_once()
    mock_bot.voice_channel_service.delete_voice_channel.assert_called_once_with(789)
    mock_bot.audit_log_service.log_event.assert_any_call(
        guild_id=member.guild.id,
        event_type=AuditLogEventType.USER_LEFT_OWNED_CHANNEL,
        user_id=member.id,
        channel_id=789,
        details=f"User {member.display_name} ({member.id}) left their owned channel '{before_channel.name}' ({before_channel.id}).",
    )
    mock_bot.audit_log_service.log_event.assert_any_call(
        guild_id=member.guild.id,
        event_type=AuditLogEventType.CHANNEL_DELETED_NOT_FOUND,
        channel_id=789,
        details=f"Stale DB entry for channel {before_channel.id} removed.",
    )


@pytest.mark.asyncio
async def test_handle_channel_creation_no_config(mock_bot):
    """
    Tests that channel creation is gracefully handled when the bot is not configured
    for the guild.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)

    member = AsyncMock(spec=discord.Member, bot=False, guild=MagicMock(id=123))
    before_state = AsyncMock(spec=discord.VoiceState, channel=None)
    after_state = AsyncMock(spec=discord.VoiceState, channel=AsyncMock(id=456))

    # Simulate that the guild has no configuration
    mock_bot.guild_service.get_guild_config.return_value = None

    # Act
    await cog.on_voice_state_update(member, before_state, after_state)

    # Assert
    mock_bot.voice_channel_service.get_voice_channel_by_owner.assert_not_called()
    member.move_to.assert_not_called()


@pytest.mark.asyncio
async def test_on_ready_cleanup_with_no_config(mock_bot):
    """
    Tests that the on_ready cleanup gracefully skips guilds that are not configured.
    """
    mock_guild = MagicMock(spec=discord.Guild, id=123, name="Test Guild")
    mock_bot.guilds = [mock_guild]
    mock_bot.guild_service.get_guild_config.return_value = None

    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)

    await cog.on_ready()

    mock_bot.get_channel.assert_not_called()


@pytest.mark.asyncio
async def test_on_ready_cleanup_api_error(mock_bot):
    """
    Simulates a discord.HTTPException during channel deletion to ensure the error is caught and logged.
    """
    guild_id = 123
    category_id = 456
    creation_channel_id = 789

    mock_empty_channel = MagicMock(spec=discord.VoiceChannel, id=101, members=[], delete=AsyncMock())
    mock_empty_channel.delete.side_effect = discord.HTTPException(response=MagicMock(), message="API Error")
    mock_category = MagicMock(spec=discord.CategoryChannel, id=category_id, voice_channels=[mock_empty_channel])
    mock_guild = MagicMock(spec=discord.Guild, id=guild_id, name="Test Guild")
    mock_bot.guilds = [mock_guild]
    mock_bot.get_channel.return_value = mock_category
    mock_guild_config = Guild(
        id=guild_id,
        cleanup_on_startup=True,
        voice_category_id=category_id,
        creation_channel_id=creation_channel_id
    )
    mock_bot.guild_service.get_guild_config.return_value = mock_guild_config

    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)

    await cog.on_ready()

    mock_empty_channel.delete.assert_called_once()
    mock_bot.guild_service.cleanup_stale_channels.assert_not_called()


@pytest.mark.asyncio
async def test_on_voice_state_update_move_between_temp_channels(mock_bot):
    """
    Simulates a user moving from one temporary channel to another to ensure the old one is correctly deleted.
    """
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, bot=False, guild=MagicMock(id=123))
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, members=[])
    after_channel = AsyncMock(spec=discord.VoiceChannel, id=999, members=[member])
    before = AsyncMock(spec=discord.VoiceState, channel=before_channel)
    after = AsyncMock(spec=discord.VoiceState, channel=after_channel)
    guild_config = Guild(creation_channel_id=456)
    mock_bot.guild_service.get_guild_config.return_value = guild_config
    mock_bot.voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=member.id)

    with patch.object(cog, "_handle_channel_leave") as mock_handle_leave:
        await cog.on_voice_state_update(member, before, after)
        mock_handle_leave.assert_called_once_with(member, before)

@pytest.mark.asyncio
async def test_on_voice_state_update_rapid_join_leave(mock_bot):
    """
    Simulates a user joining and leaving the creation channel quickly to test the user lock mechanism.
    """
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, bot=False, guild=MagicMock(id=123))
    creation_channel = AsyncMock(spec=discord.VoiceChannel, id=456)
    before = AsyncMock(spec=discord.VoiceState, channel=None)
    after = AsyncMock(spec=discord.VoiceState, channel=creation_channel)
    guild_config = Guild(creation_channel_id=456)
    mock_bot.guild_service.get_guild_config.return_value = guild_config

    with patch.object(cog, "_handle_channel_creation") as mock_handle_create:
        await cog.on_voice_state_update(member, before, after)
        mock_handle_create.assert_called_once_with(member, guild_config)

    before_leave = AsyncMock(spec=discord.VoiceState, channel=creation_channel)
    after_leave = AsyncMock(spec=discord.VoiceState, channel=None)

    with patch.object(cog, "_handle_channel_leave") as mock_handle_leave:
        await cog.on_voice_state_update(member, before_leave, after_leave)
        mock_handle_leave.assert_not_called()

@pytest.mark.asyncio
async def test_on_voice_state_update_bot_user(mock_bot):
    """
    Tests that voice state updates from bots are ignored.
    """
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, bot=True)
    before = AsyncMock(spec=discord.VoiceState, channel=None)
    after = AsyncMock(spec=discord.VoiceState, channel=AsyncMock())

    await cog.on_voice_state_update(member, before, after)

    mock_bot.guild_service.get_guild_config.assert_not_called()

@pytest.mark.asyncio
async def test_handle_channel_leave_non_owner(mock_bot):
    """
    Tests that the correct audit log is created when a non-owner leaves a temporary channel.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)

    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))
    owner = AsyncMock(spec=discord.Member, id=2)
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="Temp Channel", members=[owner])
    before_state = AsyncMock(spec=discord.VoiceState, channel=before_channel)

    mock_bot.voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=owner.id)

    # Act
    await cog._handle_channel_leave(member, before_state)

    # Assert
    mock_bot.audit_log_service.log_event.assert_called_once_with(
        guild_id=member.guild.id,
        event_type=AuditLogEventType.USER_LEFT_TEMP_CHANNEL,
        user_id=member.id,
        channel_id=789,
        details=f"User {member.display_name} ({member.id}) left temporary channel '{before_channel.name}' ({before_channel.id}).",
    )

@pytest.mark.asyncio
async def test_handle_channel_creation_existing_channel_stale(mock_bot):
    """
    Tests that a stale channel in the DB is cleaned up if the user tries to create a new one.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))
    guild_config = Guild(creation_channel_id=456, voice_category_id=789)
    
    # User has an existing channel in the DB, but it's not on Discord
    mock_bot.voice_channel_service.get_voice_channel_by_owner.return_value = MagicMock(channel_id=999)
    mock_bot.get_channel.return_value = None

    # Act
    await cog._handle_channel_creation(member, guild_config)

    # Assert
    mock_bot.voice_channel_service.delete_voice_channel.assert_called_once_with(999)
    mock_bot.audit_log_service.log_event.assert_called_once_with(
        guild_id=member.guild.id,
        event_type=AuditLogEventType.STALE_CHANNEL_CLEANUP,
        user_id=member.id,
        channel_id=999,
        details=f"Stale channel 999 (owner: {member.display_name} - {member.id}) removed from database as Discord channel was not found.",
    )

@pytest.mark.asyncio
async def test_handle_channel_creation_category_not_found(mock_bot):
    """
    Tests that an audit log is created if the configured voice category is not found.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))
    guild_config = Guild(creation_channel_id=456, voice_category_id=789)
    
    mock_bot.voice_channel_service.get_voice_channel_by_owner.return_value = None
    mock_bot.get_channel.return_value = None

    # Act
    await cog._handle_channel_creation(member, guild_config)

    # Assert
    mock_bot.audit_log_service.log_event.assert_called_once_with(
        guild_id=member.guild.id,
        event_type=AuditLogEventType.CATEGORY_NOT_FOUND,
        details=f"Configured voice category {guild_config.voice_category_id} not found or invalid for guild {member.guild.id}.",
    )

@pytest.mark.asyncio
async def test_create_and_move_user_creation_fails(mock_bot):
    """
    Tests that an audit log is created if channel creation fails.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))
    category = AsyncMock(spec=discord.CategoryChannel)
    
    member.guild.create_voice_channel.side_effect = Exception("Test Exception")

    # Act
    await cog._create_and_move_user(member, category, "Test Channel", 0)

    # Assert
    mock_bot.audit_log_service.log_event.assert_called_once_with(
        guild_id=member.guild.id,
        event_type=AuditLogEventType.CHANNEL_CREATION_FAILED,
        user_id=member.id,
        details="Failed to create channel: Test Exception",
    )

@pytest.mark.asyncio
async def test_handle_user_join_non_creation_channel(mock_bot):
    """
    Tests that channel creation is not triggered when a user joins a non-creation channel.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))
    guild_config = Guild(creation_channel_id=456)
    after_channel = AsyncMock(spec=discord.VoiceChannel, id=789) # Not the creation channel
    after_state = AsyncMock(spec=discord.VoiceState, channel=after_channel)

    # Act
    await cog._handle_user_join(member, after_state, guild_config)

    # Assert
    member.guild.create_voice_channel.assert_not_called()

@pytest.mark.asyncio
async def test_handle_channel_creation_existing_channel_valid(mock_bot):
    """
    Tests that a user is moved to their existing channel if it's valid.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))
    guild_config = Guild(creation_channel_id=456, voice_category_id=789)
    existing_channel = AsyncMock(spec=discord.VoiceChannel, id=999, name="Existing Channel")
    
    mock_bot.voice_channel_service.get_voice_channel_by_owner.return_value = MagicMock(channel_id=999)
    mock_bot.get_channel.return_value = existing_channel

    # Act
    await cog._handle_channel_creation(member, guild_config)

    # Assert
    member.move_to.assert_called_once_with(existing_channel, reason="User already has a channel.")
    mock_bot.audit_log_service.log_event.assert_called_once_with(
        guild_id=member.guild.id,
        event_type=AuditLogEventType.USER_MOVED_TO_EXISTING_CHANNEL,
        user_id=member.id,
        channel_id=999,
        details=f"User {member.display_name} ({member.id}) moved to their existing channel '{existing_channel.name}' (999).",
    )

@pytest.mark.asyncio
async def test_cleanup_stale_channels_on_startup_invalid_category(mock_bot):
    """
    Tests that cleanup skips if the configured category is not a CategoryChannel.
    """
    # Arrange
    guild_id = 123
    category_id = 456
    creation_channel_id = 789

    # Simulate get_channel returning a TextChannel instead of a CategoryChannel
    mock_category = MagicMock(spec=discord.TextChannel, id=category_id)
    mock_guild = MagicMock(spec=discord.Guild, id=guild_id, name="Test Guild")
    mock_bot.guilds = [mock_guild]
    mock_bot.get_channel.return_value = mock_category
    mock_guild_config = Guild(
        id=guild_id,
        cleanup_on_startup=True,
        voice_category_id=category_id,
        creation_channel_id=creation_channel_id
    )
    mock_bot.guild_service.get_guild_config.return_value = mock_guild_config

    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)

    # Act
    await cog._cleanup_stale_channels_on_startup()

    # Assert
    # No channels should be deleted if the category is invalid
    mock_bot.guild_service.cleanup_stale_channels.assert_not_called()

@pytest.mark.asyncio
async def test_get_new_channel_config_with_user_settings(mock_bot):
    """
    Tests that the new channel configuration is correctly retrieved when a user has custom settings.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, id=1, display_name="Test User")
    user_settings = UserSettings(custom_channel_name="Custom Name", custom_channel_limit=5)
    
    mock_bot.voice_channel_service.get_user_settings.return_value = user_settings

    # Act
    channel_name, channel_limit = await cog._get_new_channel_config(member)

    # Assert
    assert channel_name == "Custom Name"
    assert channel_limit == 5

@pytest.mark.asyncio
async def test_get_new_channel_config_no_user_settings(mock_bot):
    """
    Tests that the new channel configuration defaults correctly when a user has no custom settings.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, id=1, display_name="Test User")
    
    mock_bot.voice_channel_service.get_user_settings.return_value = None

    # Act
    channel_name, channel_limit = await cog._get_new_channel_config(member)

    # Assert
    assert channel_name == "Test User's Channel"
    assert channel_limit == 0

@pytest.mark.asyncio
async def test_handle_channel_leave_last_user(mock_bot):
    """
    Tests that a channel is deleted when the last user leaves.
    """
    # Arrange
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="Temp Channel", members=[])
    before_state = AsyncMock(spec=discord.VoiceState, channel=before_channel)

    mock_bot.voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=member.id)

    with patch.object(cog, "_delete_empty_channel") as mock_delete_empty_channel:
        # Act
        await cog._handle_channel_leave(member, before_state)

        # Assert
        mock_delete_empty_channel.assert_called_once_with(before_channel)

@pytest.mark.asyncio
async def test_cleanup_stale_channels_on_startup_no_ids(mock_bot):
    """
    Tests that cleanup skips if the guild has no voice_category_id or creation_channel_id.
    """
    # Arrange
    guild_id = 123
    mock_guild = MagicMock(spec=discord.Guild, id=guild_id, name="Test Guild")
    mock_bot.guilds = [mock_guild]
    mock_guild_config = Guild(
        id=guild_id,
        cleanup_on_startup=True,
        voice_category_id=None,
        creation_channel_id=None
    )
    mock_bot.guild_service.get_guild_config.return_value = mock_guild_config

    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)

    # Act
    await cog._cleanup_stale_channels_on_startup()

    # Assert
    mock_bot.get_channel.assert_not_called()