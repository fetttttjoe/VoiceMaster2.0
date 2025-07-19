# VoiceMaster2.0/tests/cogs/test_events.py
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import discord
from cogs.events import EventsCog
from database.models import Guild


@pytest.mark.asyncio
async def test_on_voice_state_update_routes_to_creation(mock_bot):
    """Verifies that joining the creation channel calls the creation handler."""
    cog = EventsCog(mock_bot)
    member = AsyncMock()
    member.guild.id = 123
    before = AsyncMock(channel=None)
    after = AsyncMock(channel=MagicMock(id=456))

    guild_config = Guild(creation_channel_id=456)

    with patch('database.database.db.get_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        with patch('services.guild_service.GuildService.get_guild_config', return_value=guild_config):
            with patch.object(cog, '_handle_channel_creation') as mock_handle_create:
                await cog.on_voice_state_update(member, before, after)
                mock_handle_create.assert_called_once()


@pytest.mark.asyncio
async def test_on_voice_state_update_routes_to_leave(mock_bot):
    """Verifies that leaving a temporary channel calls the leave handler."""
    cog = EventsCog(mock_bot)
    member = AsyncMock()
    member.guild.id = 123
    before = AsyncMock(channel=MagicMock(id=789))
    after = AsyncMock(channel=None)

    # creation_channel_id is different from the channel being left
    guild_config = Guild(creation_channel_id=456)

    with patch('database.database.db.get_session') as mock_get_session:
        mock_session = AsyncMock()
        mock_get_session.return_value.__aenter__.return_value = mock_session

        with patch('services.guild_service.GuildService.get_guild_config', return_value=guild_config):
            with patch.object(cog, '_handle_channel_leave') as mock_handle_leave:
                await cog.on_voice_state_update(member, before, after)
                mock_handle_leave.assert_called_once()


@pytest.mark.asyncio
async def test_handle_channel_leave_deletes_empty_channel(mock_bot):
    """Tests that an empty temporary channel is deleted upon the last user leaving."""
    cog = EventsCog(mock_bot)
    member = AsyncMock(id=1, guild=MagicMock(id=123))

    # The channel being left is empty
    before_channel = AsyncMock(id=789, members=[])
    before = AsyncMock(channel=before_channel)

    mock_session = AsyncMock(add=MagicMock())

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel', return_value=MagicMock(channel_id=789, owner_id=member.id)) as mock_get_vc, \
            patch('services.voice_channel_service.VoiceChannelService.delete_voice_channel') as mock_delete_vc, \
            patch('services.audit_log_service.AuditLogService.log_event'):

        # type: ignore test
        await cog._handle_channel_leave(mock_session, member, before)

        mock_get_vc.assert_called_once_with(789)
        before_channel.delete.assert_called_once()
        mock_delete_vc.assert_called_once_with(789)


@pytest.mark.asyncio
async def test_handle_channel_leave_does_not_delete_non_empty_channel(mock_bot):
    """Tests that a temporary channel is NOT deleted if other members are still present."""
    cog = EventsCog(mock_bot)
    member = AsyncMock(id=1, guild=MagicMock(id=123))

    # The channel still has another member in it
    another_member = MagicMock()
    before_channel = AsyncMock(id=789, members=[another_member])
    before = AsyncMock(channel=before_channel)

    mock_session = AsyncMock(add=MagicMock())

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel', return_value=MagicMock(channel_id=789, owner_id=member.id)), \
            patch('services.audit_log_service.AuditLogService.log_event'):

        # type: ignore test
        await cog._handle_channel_leave(mock_session, member, before)

        # Ensure delete was NOT called
        before_channel.delete.assert_not_called()


@pytest.mark.asyncio
async def test_handle_channel_creation_moves_user_if_channel_exists(mock_bot):
    """Tests that a user is moved to their existing channel if they already own one."""
    cog = EventsCog(mock_bot)
    member = AsyncMock(id=1)
    guild_config = Guild(creation_channel_id=456)
    mock_session = AsyncMock()

    # Mock the existing channel that the user owns
    existing_channel_db = MagicMock(channel_id=999)
    existing_channel_discord = AsyncMock(spec=discord.VoiceChannel)
    mock_bot.get_channel.return_value = existing_channel_discord

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', return_value=existing_channel_db) as mock_get_owner, \
            patch('services.audit_log_service.AuditLogService.log_event') as mock_log:

        # type: ignore
        await cog._handle_channel_creation(mock_session, member, guild_config)

        mock_get_owner.assert_called_once_with(member.id)
        member.move_to.assert_called_once_with(
            existing_channel_discord, reason="User already has a channel.")
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_handle_channel_creation_cleans_up_stale_channel(mock_bot):
    """Tests that a stale DB entry is removed if the channel doesn't exist on Discord."""
    cog = EventsCog(mock_bot)
    member = AsyncMock(id=1)
    guild_config = Guild(creation_channel_id=456)
    mock_session = AsyncMock()

    # Mock a channel that exists in the DB but not on Discord
    existing_channel_db = MagicMock(channel_id=999)
    mock_bot.get_channel.return_value = None  # Simulate channel not found

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', return_value=existing_channel_db), \
            patch('services.voice_channel_service.VoiceChannelService.delete_voice_channel') as mock_delete_vc, \
            patch('services.audit_log_service.AuditLogService.log_event') as mock_log:

        # type: ignore
        await cog._handle_channel_creation(mock_session, member, guild_config)

        mock_delete_vc.assert_called_once_with(existing_channel_db.channel_id)
        mock_log.assert_called_once()


@pytest.mark.asyncio
async def test_handle_channel_creation_fails_if_category_not_found(mock_bot):
    """Tests that channel creation is aborted if the configured category is not found."""
    cog = EventsCog(mock_bot)
    member = AsyncMock(id=1, guild=MagicMock())
    guild_config = Guild(creation_channel_id=456, voice_category_id=111)
    mock_session = AsyncMock()

    # Simulate category not being found
    mock_bot.get_channel.return_value = None

    with patch('services.voice_channel_service.VoiceChannelService.get_voice_channel_by_owner', return_value=None), \
            patch('services.voice_channel_service.VoiceChannelService.get_user_settings', return_value=None), \
            patch('services.audit_log_service.AuditLogService.log_event') as mock_log:

        # type: ignore
        await cog._handle_channel_creation(mock_session, member, guild_config)

        # Ensure no channel was created
        member.guild.create_voice_channel.assert_not_called()
        mock_log.assert_called_once()
