# tests/views/test_voice_commands_views.py
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from views.voice_commands_views import RenameView, SelectView

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
