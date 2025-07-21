# VoiceMaster2.0/tests/cogs/test_events.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import discord
from cogs.events import EventsCog
from database.models import Guild, AuditLogEventType # Make sure AuditLogEventType is imported

@pytest.mark.asyncio
async def test_on_voice_state_update_routes_to_creation(mock_bot):
    """Verifies that joining the creation channel calls the creation handler."""
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    member = AsyncMock(spec=discord.Member, bot=False, guild=MagicMock(id=123))
    before = AsyncMock(spec=discord.VoiceState, channel=None)
    after = AsyncMock(spec=discord.VoiceState, channel=AsyncMock(spec=discord.VoiceChannel, id=456))
    guild_config = Guild(creation_channel_id=456)
    mock_bot.guild_service.get_guild_config.return_value = guild_config

    with patch.object(cog, '_handle_channel_creation') as mock_handle_create:
        await cog.on_voice_state_update(member, before, after)
        mock_handle_create.assert_called_once_with(member, guild_config)

@pytest.mark.asyncio
async def test_on_voice_state_update_routes_to_leave(mock_bot):
    """Verifies that leaving a temporary channel calls the leave handler."""
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    member = AsyncMock(spec=discord.Member, bot=False, guild=MagicMock(id=123))
    before = AsyncMock(spec=discord.VoiceState, channel=AsyncMock(spec=discord.VoiceChannel, id=789))
    after = AsyncMock(spec=discord.VoiceState, channel=None)
    guild_config = Guild(creation_channel_id=456)
    mock_bot.guild_service.get_guild_config.return_value = guild_config
    
    with patch.object(cog, '_handle_channel_leave') as mock_handle_leave:
        await cog.on_voice_state_update(member, before, after)
        mock_handle_leave.assert_called_once_with(member, before)

@pytest.mark.asyncio
async def test_handle_channel_leave_deletes_empty_channel(mock_bot):
    """Tests that an empty temporary channel is deleted upon the last user leaving."""
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="TempChannel", members=[])
    before_channel.name = "TempChannel"
    before = AsyncMock(channel=before_channel)
    mock_bot.voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=member.id)

    await cog._handle_channel_leave(member, before)

    mock_bot.voice_channel_service.get_voice_channel.assert_called_once_with(789)
    before_channel.delete.assert_called_once_with(reason="Temporary channel empty.")
    mock_bot.voice_channel_service.delete_voice_channel.assert_called_once_with(789)
    assert mock_bot.audit_log_service.log_event.call_count == 2
    mock_bot.audit_log_service.log_event.assert_any_call(
        guild_id=123,
        event_type=AuditLogEventType.USER_LEFT_OWNED_CHANNEL,
        user_id=1,
        channel_id=789,
        details="User TestUser (1) left their owned channel 'TempChannel' (789)."
    )
    mock_bot.audit_log_service.log_event.assert_any_call(
        guild_id=123,
        event_type=AuditLogEventType.CHANNEL_DELETED,
        channel_id=789,
        details="Empty temporary channel 'TempChannel' (789) deleted from Discord and database."
    )

@pytest.mark.asyncio
async def test_handle_channel_leave_does_not_delete_non_empty_channel(mock_bot):
    """Tests that a temporary channel is NOT deleted if other members are still present."""
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")
    another_member = MagicMock()
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="TempChannel", members=[another_member])
    before = AsyncMock(channel=before_channel)
    mock_bot.voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=member.id)

    await cog._handle_channel_leave(member, before)

    mock_bot.voice_channel_service.get_voice_channel.assert_called_once_with(789)
    before_channel.delete.assert_not_called()
    mock_bot.voice_channel_service.delete_voice_channel.assert_not_called()
    mock_bot.audit_log_service.log_event.assert_called_once()
    assert mock_bot.audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.USER_LEFT_OWNED_CHANNEL

@pytest.mark.asyncio
async def test_handle_channel_creation_moves_user_if_channel_exists(mock_bot):
    """Tests that a user is moved to their existing channel if they already own one."""
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")
    guild_config = Guild(creation_channel_id=456, voice_category_id=111) 
    existing_channel_db = MagicMock(channel_id=999, name="ExistingChannel")
    existing_channel_discord = AsyncMock(spec=discord.VoiceChannel, id=999, name="ExistingChannel")
    mock_bot.get_channel.return_value = existing_channel_discord 
    mock_bot.voice_channel_service.get_voice_channel_by_owner.return_value = existing_channel_db
    mock_bot.voice_channel_service.get_user_settings.return_value = None

    await cog._handle_channel_creation(member, guild_config)

    mock_bot.voice_channel_service.get_voice_channel_by_owner.assert_called_once_with(member.id)
    member.move_to.assert_called_once_with(existing_channel_discord, reason="User already has a channel.")
    mock_bot.audit_log_service.log_event.assert_called_once()
    assert mock_bot.audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.USER_MOVED_TO_EXISTING_CHANNEL
    mock_bot.voice_channel_service.delete_voice_channel.assert_not_called()
    member.guild.create_voice_channel.assert_not_called()
    mock_bot.voice_channel_service.create_voice_channel.assert_not_called()

@pytest.mark.asyncio
async def test_handle_channel_creation_cleans_up_stale_channel(mock_bot):
    """Tests that a stale DB entry is removed if the channel doesn't exist on Discord."""
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")
    guild_config = Guild(creation_channel_id=456, voice_category_id=111) 
    existing_channel_db = MagicMock(channel_id=999)
    mock_bot.get_channel.return_value = None
    mock_bot.voice_channel_service.get_voice_channel_by_owner.return_value = existing_channel_db
    mock_bot.voice_channel_service.get_user_settings.return_value = None

    await cog._handle_channel_creation(member, guild_config)

    mock_bot.voice_channel_service.get_voice_channel_by_owner.assert_called_once_with(member.id)
    mock_bot.voice_channel_service.delete_voice_channel.assert_called_once_with(existing_channel_db.channel_id)
    mock_bot.audit_log_service.log_event.assert_called_once()
    assert mock_bot.audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.STALE_CHANNEL_CLEANUP
    member.move_to.assert_not_called()
    member.guild.create_voice_channel.assert_not_called()
    mock_bot.voice_channel_service.create_voice_channel.assert_not_called()

@pytest.mark.asyncio
async def test_handle_channel_creation_fails_if_category_not_found(mock_bot):
    """Tests that channel creation is aborted if the configured category is not found."""
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    member = AsyncMock(id=1, guild=MagicMock())
    guild_config = Guild(creation_channel_id=456, voice_category_id=111)
    mock_bot.get_channel.return_value = None
    mock_bot.voice_channel_service.get_voice_channel_by_owner.return_value = None
    mock_bot.voice_channel_service.get_user_settings.return_value = None

    await cog._handle_channel_creation(member, guild_config)

    mock_bot.voice_channel_service.get_voice_channel_by_owner.assert_called_once_with(member.id)
    mock_bot.voice_channel_service.get_user_settings.assert_called_once_with(member.id)
    member.guild.create_voice_channel.assert_not_called()
    mock_bot.voice_channel_service.create_voice_channel.assert_not_called()
    mock_bot.audit_log_service.log_event.assert_called_once()
    assert mock_bot.audit_log_service.log_event.call_args.kwargs['event_type'] == AuditLogEventType.CATEGORY_NOT_FOUND
