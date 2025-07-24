# tests/views/test_voice_commands_views.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
from database.models import Guild

from views.voice_commands_views import RenameView, SelectView, ConfigView

@pytest.mark.asyncio
async def test_rename_view_rename_channel(mock_ctx):
    """
    Tests that the RenameView correctly handles a channel rename operation.
    """
    view = RenameView(mock_ctx)
    mock_interaction = AsyncMock(spec=discord.Interaction)
    
    with patch.object(view, '_perform_rename') as mock_perform_rename:
        await view.rename_channel_button.callback(mock_interaction)
        mock_perform_rename.assert_called_once_with(mock_interaction, 'channel')

@pytest.mark.asyncio
async def test_rename_view_rename_category(mock_ctx):
    """
    Tests that the RenameView correctly handles a category rename operation.
    """
    view = RenameView(mock_ctx)
    mock_interaction = AsyncMock(spec=discord.Interaction)

    with patch.object(view, '_perform_rename') as mock_perform_rename:
        await view.rename_category_button.callback(mock_interaction)
        mock_perform_rename.assert_called_once_with(mock_interaction, 'category')

@pytest.mark.asyncio
async def test_select_view_channel_selection(mock_ctx):
    """
    Tests that the SelectView correctly handles a channel selection.
    """
    view = SelectView(mock_ctx, voice_channels=[MagicMock()], categories=[MagicMock()])
    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.data = {'values': ['12345']}

    with patch.object(view, '_update_selection') as mock_update_selection:
        await view.channel_select_callback(mock_interaction)
        mock_update_selection.assert_called_once_with(mock_interaction, 'channel')

@pytest.mark.asyncio
async def test_select_view_category_selection(mock_ctx):
    """
    Tests that the SelectView correctly handles a category selection.
    """
    view = SelectView(mock_ctx, voice_channels=[MagicMock()], categories=[MagicMock()])
    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.data = {'values': ['67890']}

    with patch.object(view, '_update_selection') as mock_update_selection:
        await view.category_select_callback(mock_interaction)
        mock_update_selection.assert_called_once_with(mock_interaction, 'category')


@pytest.mark.asyncio
async def test_config_view_enable_cleanup(mock_ctx):
    """
    Tests that clicking the 'Enable Cleanup' button calls the correct service method.
    """
    # Arrange
    mock_guild_config = Guild(cleanup_on_startup=False) # Start with it disabled
    view = ConfigView(mock_ctx, mock_guild_config)
    
    # Get the "Enable" button
    enable_button = next(child for child in view.children if child.custom_id == "enable_cleanup")
    
    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()

    # Act
    await enable_button.callback(mock_interaction)

    # Assert
    mock_ctx.bot.guild_service.set_cleanup_on_startup.assert_called_once_with(mock_ctx.guild.id, True)
    mock_interaction.response.edit_message.assert_called_once()


@pytest.mark.asyncio
async def test_config_view_disable_cleanup(mock_ctx):
    """
    Tests that clicking the 'Disable Cleanup' button calls the correct service method.
    """
    # Arrange
    mock_guild_config = Guild(cleanup_on_startup=True) # Start with it enabled
    view = ConfigView(mock_ctx, mock_guild_config)
    
    # Get the "Disable" button
    disable_button = next(child for child in view.children if child.custom_id == "disable_cleanup")
    
    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()

    # Act
    await disable_button.callback(mock_interaction)

    # Assert
    mock_ctx.bot.guild_service.set_cleanup_on_startup.assert_called_once_with(mock_ctx.guild.id, False)
    mock_interaction.response.edit_message.assert_called_once()