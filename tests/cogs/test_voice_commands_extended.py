# tests/cogs/test_voice_commands_extended.py
from unittest.mock import AsyncMock, MagicMock

import pytest

from cogs.voice_commands import VoiceCommandsCog
from database.models import Guild
from views.voice_commands_views import ConfigView, RenameView, SelectView


@pytest.mark.asyncio
async def test_config_command_not_setup(mock_bot, mock_ctx):
    """
    Tests that the 'config' command shows a "not set up" message if the bot
    has not been configured for the guild yet.
    """
    # Arrange
    mock_guild_service = AsyncMock()
    mock_guild_service.get_guild_config.return_value = None
    mock_bot.guild_service = mock_guild_service

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, AsyncMock(), AsyncMock())

    # Act
    mock_ctx.prefix = "."
    await cog.config.callback(cog, mock_ctx)

    # Assert
    mock_ctx.send.assert_called_once_with("The bot has not been set up yet. Run `.voice setup` first.", ephemeral=True)


@pytest.mark.asyncio
async def test_config_command_success(mock_bot, mock_ctx):
    """
    Tests that the 'config' command successfully displays the config view
    when the bot is properly set up.
    """
    # Arrange
    mock_guild_config = Guild(id=123, cleanup_on_startup=True)
    mock_guild_service = AsyncMock()
    mock_guild_service.get_guild_config.return_value = mock_guild_config
    mock_bot.guild_service = mock_guild_service

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, AsyncMock(), AsyncMock())

    # Act
    await cog.config.callback(cog, mock_ctx)

    # Assert
    mock_ctx.send.assert_called_once()
    assert isinstance(mock_ctx.send.call_args.kwargs["view"], ConfigView)
    assert "VoiceMaster Config" in mock_ctx.send.call_args.kwargs["embed"].title


@pytest.mark.asyncio
async def test_edit_rename_command_not_setup(mock_bot, mock_ctx):
    """
    Tests that the 'edit rename' command shows a "not set up" message if the
    bot has not been configured.
    """
    # Arrange
    mock_guild_service = AsyncMock()
    mock_guild_service.get_guild_config.return_value = None
    mock_bot.guild_service = mock_guild_service

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, AsyncMock(), AsyncMock())

    # Act
    await cog.edit_rename.callback(cog, mock_ctx)

    # Assert
    mock_ctx.send.assert_called_once_with("The bot has not been set up yet. Run `.voice setup` first.", ephemeral=True)


@pytest.mark.asyncio
async def test_edit_rename_command_success(mock_bot, mock_ctx):
    """
    Tests that the 'edit rename' command successfully shows the rename view.
    """
    # Arrange
    mock_guild_config = Guild(id=123)
    mock_guild_service = AsyncMock()
    mock_guild_service.get_guild_config.return_value = mock_guild_config
    mock_bot.guild_service = mock_guild_service

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, AsyncMock(), AsyncMock())

    # Act
    await cog.edit_rename.callback(cog, mock_ctx)

    # Assert
    mock_ctx.send.assert_called_once()
    assert isinstance(mock_ctx.send.call_args.kwargs["view"], RenameView)


@pytest.mark.asyncio
async def test_edit_select_command_not_setup(mock_bot, mock_ctx):
    """
    Tests that the 'edit select' command shows a "not set up" message if the
    bot has not been configured.
    """
    # Arrange
    mock_guild_service = AsyncMock()
    mock_guild_service.get_guild_config.return_value = None
    mock_bot.guild_service = mock_guild_service

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, AsyncMock(), AsyncMock())

    # Act
    await cog.edit_select.callback(cog, mock_ctx)

    # Assert
    mock_ctx.send.assert_called_once_with("The bot has not been set up yet. Run `.voice setup` first.", ephemeral=True)


@pytest.mark.asyncio
async def test_edit_select_command_success(mock_bot, mock_ctx):
    """
    Tests that the 'edit select' command successfully shows the select view.
    """
    # Arrange
    mock_guild_config = Guild(id=123)
    mock_guild_service = AsyncMock()
    mock_guild_service.get_guild_config.return_value = mock_guild_config
    mock_bot.guild_service = mock_guild_service

    # Mock guild attributes needed for the command
    mock_ctx.guild.voice_channels = [MagicMock(category=True)]
    mock_ctx.guild.categories = [MagicMock()]
    mock_ctx.guild.owner_id = 456

    cog = VoiceCommandsCog(mock_bot, mock_guild_service, AsyncMock(), AsyncMock())

    # Act
    await cog.edit_select.callback(cog, mock_ctx)

    # Assert
    mock_ctx.send.assert_called_once()
    assert isinstance(mock_ctx.send.call_args.kwargs["view"], SelectView)
