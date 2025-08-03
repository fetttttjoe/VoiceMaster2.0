from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from cogs.events import EventsCog
from database.models import AuditLogEventType, Guild


@pytest.mark.asyncio
async def test_on_ready_cleans_up_channels(mock_bot):
    """
    Tests that the on_ready event correctly identifies and purges empty channels.
    """
    guild_id = 123
    category_id = 456
    creation_channel_id = 789

    mock_creation_channel = MagicMock(spec=discord.VoiceChannel, id=creation_channel_id, members=[])
    mock_empty_channel = MagicMock(spec=discord.VoiceChannel, id=101, members=[], delete=AsyncMock())
    mock_occupied_channel = MagicMock(spec=discord.VoiceChannel, id=102, members=[MagicMock()])

    mock_category = MagicMock(spec=discord.CategoryChannel, id=category_id, voice_channels=[
        mock_creation_channel, mock_empty_channel, mock_occupied_channel
    ])

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
    mock_occupied_channel.delete.assert_not_called()
    mock_creation_channel.delete.assert_not_called()
    mock_bot.guild_service.cleanup_stale_channels.assert_called_once_with([mock_empty_channel.id])


@pytest.mark.asyncio
async def test_on_voice_state_update_routes_to_creation(mock_bot):
    """Verifies that joining the creation channel calls the creation handler."""
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, bot=False, guild=MagicMock(id=123))
    before = AsyncMock(spec=discord.VoiceState, channel=None)
    after = AsyncMock(spec=discord.VoiceState, channel=AsyncMock(spec=discord.VoiceChannel, id=456))
    guild_config = Guild(creation_channel_id=456)
    mock_bot.guild_service.get_guild_config.return_value = guild_config

    with patch.object(cog, "_handle_channel_creation") as mock_handle_create:
        await cog.on_voice_state_update(member, before, after)
        mock_handle_create.assert_called_once_with(member, guild_config)


@pytest.mark.asyncio
async def test_on_voice_state_update_routes_to_leave(mock_bot):
    """Verifies that leaving a temporary channel calls the leave handler."""
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(spec=discord.Member, bot=False, guild=MagicMock(id=123))
    before = AsyncMock(spec=discord.VoiceState, channel=AsyncMock(spec=discord.VoiceChannel, id=789))
    after = AsyncMock(spec=discord.VoiceState, channel=None)
    guild_config = Guild(creation_channel_id=456)
    mock_bot.guild_service.get_guild_config.return_value = guild_config

    with patch.object(cog, "_handle_channel_leave") as mock_handle_leave:
        await cog.on_voice_state_update(member, before, after)
        mock_handle_leave.assert_called_once_with(member, before)


@pytest.mark.asyncio
async def test_handle_channel_leave_deletes_empty_channel(mock_bot):
    """Tests that an empty temporary channel is deleted upon the last user leaving."""
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="TempChannel", members=[])
    before = AsyncMock(channel=before_channel)
    mock_bot.voice_channel_service.get_voice_channel.return_value = MagicMock(channel_id=789, owner_id=member.id)

    with patch.object(cog, "_delete_empty_channel") as mock_delete_empty_channel:
        await cog._handle_channel_leave(member, before)
        mock_delete_empty_channel.assert_called_once_with(before_channel)



@pytest.mark.asyncio
async def test_handle_channel_leave_does_not_delete_non_empty_channel(mock_bot):
    """Tests that a temporary channel is NOT deleted if other members are still present."""
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
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
    assert mock_bot.audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.USER_LEFT_OWNED_CHANNEL


@pytest.mark.asyncio
async def test_handle_channel_creation_moves_user_if_channel_exists(mock_bot):
    """Tests that a user is moved to their existing channel if they already own one."""
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(id=1, guild=MagicMock(id=123), display_name="TestUser")
    guild_config = Guild(creation_channel_id=456, voice_category_id=111)
    existing_channel_db = MagicMock(channel_id=999, name="ExistingChannel")
    existing_channel_discord = AsyncMock(spec=discord.VoiceChannel, id=999, name="ExistingChannel")
    mock_bot.get_channel.return_value = existing_channel_discord
    mock_bot.voice_channel_service.get_voice_channel_by_owner.return_value = existing_channel_db

    with patch.object(cog, "_create_and_move_user") as mock_create_and_move:
        await cog._handle_channel_creation(member, guild_config)
        mock_create_and_move.assert_not_called()

    member.move_to.assert_called_once_with(existing_channel_discord, reason="User already has a channel.")



@pytest.mark.asyncio
async def test_handle_channel_creation_cleans_up_stale_channel(mock_bot):
    """Tests that a stale DB entry is removed if the channel doesn't exist on Discord."""
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
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
    assert mock_bot.audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.STALE_CHANNEL_CLEANUP
    member.move_to.assert_not_called()
    member.guild.create_voice_channel.assert_not_called()
    mock_bot.voice_channel_service.create_voice_channel.assert_not_called()


@pytest.mark.asyncio
async def test_handle_channel_creation_fails_if_category_not_found(mock_bot):
    """Tests that channel creation is aborted if the configured category is not found."""
    cog = EventsCog(mock_bot, mock_bot.guild_service, mock_bot.voice_channel_service, mock_bot.audit_log_service)
    member = AsyncMock(id=1, guild=MagicMock())
    guild_config = Guild(creation_channel_id=456, voice_category_id=111)
    mock_bot.get_channel.return_value = None
    mock_bot.voice_channel_service.get_voice_channel_by_owner.return_value = None

    with patch.object(cog, "_create_and_move_user") as mock_create_and_move:
        await cog._handle_channel_creation(member, guild_config)
        mock_create_and_move.assert_not_called()

