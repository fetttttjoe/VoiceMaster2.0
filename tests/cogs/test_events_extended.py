# tests/cogs/test_events_extended.py
import pytest
from unittest.mock import AsyncMock, MagicMock
import discord

from cogs.events import EventsCog
from database.models import AuditLogEventType


@pytest.mark.asyncio
async def test_handle_channel_leave_stale_channel_cleanup(mock_bot):
    """
    Tests that a stale DB entry is cleaned up if the channel is already
    deleted from Discord when the bot tries to delete it.
    """
    # Arrange
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    
    member = AsyncMock(spec=discord.Member, id=1, guild=MagicMock(id=123))
    
    # Simulate a channel that is empty
    before_channel = AsyncMock(spec=discord.VoiceChannel, id=789, name="Old Channel", members=[])
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
        event_type=AuditLogEventType.CHANNEL_DELETED_NOT_FOUND,
        channel_id=789,
        details=f"Temporary channel {before_channel.id} was already gone from Discord but its entry was removed from the database."
    )

@pytest.mark.asyncio
async def test_handle_channel_creation_no_config(mock_bot):
    """
    Tests that channel creation is gracefully handled when the bot is not configured
    for the guild.
    """
    # Arrange
    cog = EventsCog(
        mock_bot, 
        mock_bot.guild_service, 
        mock_bot.voice_channel_service, 
        mock_bot.audit_log_service
    )
    
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
