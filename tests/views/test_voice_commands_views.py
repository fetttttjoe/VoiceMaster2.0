# tests/views/test_voice_commands_views.py
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import ui

from database.models import Guild
from views.voice_commands_views import AuthorOnlyView, ConfigView, RenameView, SelectView


@pytest.mark.asyncio
async def test_interaction_check_author_is_allowed(mock_ctx):
    """
    Tests that the original author is allowed to interact.
    """
    view = AuthorOnlyView(mock_ctx)
    mock_interaction = AsyncMock()
    mock_interaction.user.id = mock_ctx.author.id

    assert await view.interaction_check(mock_interaction) is True


@pytest.mark.asyncio
async def test_interaction_check_other_user_is_denied(mock_ctx):
    """
    Tests that a user other than the author is denied interaction.
    """
    view = AuthorOnlyView(mock_ctx)
    mock_interaction = AsyncMock()
    mock_interaction.user.id = 9999  # A different user ID

    assert await view.interaction_check(mock_interaction) is False
    mock_interaction.response.send_message.assert_called_once_with(
        "You are not authorized to interact with this component.", ephemeral=True
    )


@pytest.mark.asyncio
async def test_on_timeout_disables_components(mock_ctx):
    """
    Tests that on_timeout correctly disables all components.
    """
    view = AuthorOnlyView(mock_ctx, timeout=0.1)
    view.message = AsyncMock()

    # Add some components to the view
    button = ui.Button(label="Test")
    select = ui.Select(options=[discord.SelectOption(label="A")])
    view.add_item(button)
    view.add_item(select)

    # Mock disable_components to check if it's called
    view.disable_components = AsyncMock()

    await view.on_timeout()

    view.disable_components.assert_called_once()


@pytest.mark.asyncio
async def test_disable_components_disables_items_and_edits_message(mock_ctx):
    """
    Tests that disable_components disables all items and edits the message.
    """
    view = AuthorOnlyView(mock_ctx)
    view.message = AsyncMock()

    # Add components
    button = ui.Button(label="Click Me")
    select = ui.Select(placeholder="Choose...")
    view.add_item(button)
    view.add_item(select)

    await view.disable_components()

    # Assert that all components are disabled
    for item in view.children:
        assert item.disabled is True

    # Assert that the message was edited with the updated view
    view.message.edit.assert_called_once_with(view=view)


@pytest.mark.asyncio
async def test_rename_view_perform_rename_success(mock_ctx):
    """
    Tests the internal _perform_rename logic for a successful channel rename.
    """
    # Arrange
    view = RenameView(mock_ctx)
    mock_interaction = AsyncMock(spec=discord.Interaction)
    # Correctly mock the response attribute to be awaitable
    mock_interaction.response = AsyncMock()
    mock_interaction.followup = AsyncMock()

    # Simulate bot.wait_for to return a message with the new name
    new_name = "New Cool Name"
    mock_message = MagicMock(spec=discord.Message)
    mock_message.content = new_name
    # The mock_ctx fixture already provides a bot, so we can attach wait_for to it
    mock_ctx.bot.wait_for = AsyncMock(return_value=mock_message)

    # Mock the guild config and the channel to be renamed
    mock_guild_config = Guild(creation_channel_id=12345)
    # The view gets the service from the bot on mock_ctx
    mock_ctx.bot.guild_service.get_guild_config.return_value = mock_guild_config

    mock_channel = AsyncMock(spec=discord.VoiceChannel)
    mock_channel.name = "Old Name"
    mock_ctx.guild.get_channel.return_value = mock_channel

    # Act
    await view._perform_rename(mock_interaction, "channel")

    # Assert
    mock_interaction.response.send_message.assert_called_once()
    mock_channel.edit.assert_called_once_with(name=new_name)
    mock_ctx.bot.audit_log_service.log_event.assert_called_once()
    mock_ctx.send.assert_called_once()


@pytest.mark.asyncio
async def test_rename_view_rename_channel(mock_ctx):
    """
    Tests that the RenameView correctly handles a channel rename operation.
    """
    view = RenameView(mock_ctx)
    mock_interaction = AsyncMock(spec=discord.Interaction)

    with patch.object(view, "_perform_rename") as mock_perform_rename:
        await view.rename_channel_button.callback(mock_interaction)
        mock_perform_rename.assert_called_once_with(mock_interaction, "channel")


@pytest.mark.asyncio
async def test_rename_view_rename_category(mock_ctx):
    """
    Tests that the RenameView correctly handles a category rename operation.
    """
    view = RenameView(mock_ctx)
    mock_interaction = AsyncMock(spec=discord.Interaction)

    with patch.object(view, "_perform_rename") as mock_perform_rename:
        await view.rename_category_button.callback(mock_interaction)
        mock_perform_rename.assert_called_once_with(mock_interaction, "category")


@pytest.mark.asyncio
async def test_select_view_update_selection_success(mock_ctx):
    """
    Tests the internal _update_selection logic for a successful channel selection.
    """
    # Arrange
    view = SelectView(mock_ctx, voice_channels=[MagicMock()], categories=[MagicMock()])
    mock_interaction = AsyncMock(spec=discord.Interaction)
    # Correctly mock response and followup to be awaitable
    mock_interaction.response = AsyncMock()
    mock_interaction.followup = AsyncMock()
    new_channel_id = "54321"
    mock_interaction.data = {"values": [new_channel_id]}

    # Mock the guild config
    mock_guild_config = Guild(creation_channel_id=12345, voice_category_id=67890)
    mock_ctx.bot.guild_service.get_guild_config.return_value = mock_guild_config

    # Act
    await view._update_selection(mock_interaction, "channel")

    # Assert
    # Check that the guild was updated with the new channel id
    mock_ctx.bot.guild_service.create_or_update_guild.assert_called_once_with(
        mock_ctx.guild.id,
        mock_ctx.guild.owner_id,
        mock_guild_config.voice_category_id,
        int(new_channel_id),
    )
    # Check that the audit log was updated
    mock_ctx.bot.audit_log_service.log_event.assert_called_once()
    # Check that the interaction was followed up
    mock_interaction.followup.send.assert_called_once()


@pytest.mark.asyncio
async def test_select_view_channel_selection(mock_ctx):
    """
    Tests that the SelectView correctly handles a channel selection.
    """
    view = SelectView(mock_ctx, voice_channels=[MagicMock()], categories=[MagicMock()])
    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.data = {"values": ["12345"]}

    with patch.object(view, "_update_selection") as mock_update_selection:
        await view.channel_select_callback(mock_interaction)
        mock_update_selection.assert_called_once_with(mock_interaction, "channel")


@pytest.mark.asyncio
async def test_select_view_category_selection(mock_ctx):
    """
    Tests that the SelectView correctly handles a category selection.
    """
    view = SelectView(mock_ctx, voice_channels=[MagicMock()], categories=[MagicMock()])
    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.data = {"values": ["67890"]}

    with patch.object(view, "_update_selection") as mock_update_selection:
        await view.category_select_callback(mock_interaction)
        mock_update_selection.assert_called_once_with(mock_interaction, "category")


@pytest.mark.asyncio
async def test_config_view_enable_cleanup(mock_ctx):
    """
    Tests that clicking the 'Enable Cleanup' button calls the correct service method.
    """
    # Arrange
    # Create a mock for the guild_service that will be used by the view
    mock_guild_service = AsyncMock()
    # When get_guild_config is called, return a new mock config object
    mock_guild_service.get_guild_config.return_value = Guild(cleanup_on_startup=True)

    # Assign the mock service to the bot
    mock_ctx.bot.guild_service = mock_guild_service

    mock_guild_config = Guild(cleanup_on_startup=False)  # Start with it disabled
    view = ConfigView(mock_ctx, mock_guild_config)

    # Get the "Enable" button
    enable_button = view.enable_cleanup_button

    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.guild = mock_ctx.guild
    mock_interaction.user = mock_ctx.author

    # Act
    await enable_button.callback(mock_interaction)

    # Assert
    # Check that the service method was called correctly
    mock_guild_service.set_cleanup_on_startup.assert_called_once_with(mock_ctx.guild.id, True)
    # Check that the message was edited
    mock_interaction.response.edit_message.assert_called_once()


@pytest.mark.asyncio
async def test_config_view_disable_cleanup(mock_ctx):
    """
    Tests that clicking the 'Disable Cleanup' button calls the correct service method.
    """
    # Arrange
    # Create a mock for the guild_service that will be used by the view
    mock_guild_service = AsyncMock()
    # When get_guild_config is called, return a new mock config object
    mock_guild_service.get_guild_config.return_value = Guild(cleanup_on_startup=False)

    # Assign the mock service to the bot
    mock_ctx.bot.guild_service = mock_guild_service

    mock_guild_config = Guild(cleanup_on_startup=True)  # Start with it enabled
    view = ConfigView(mock_ctx, mock_guild_config)

    # Get the "Disable" button
    disable_button = view.disable_cleanup_button

    mock_interaction = AsyncMock(spec=discord.Interaction)
    mock_interaction.response = AsyncMock()
    mock_interaction.guild = mock_ctx.guild
    mock_interaction.user = mock_ctx.author

    # Act
    await disable_button.callback(mock_interaction)

    # Assert
    # Check that the service method was called correctly
    mock_guild_service.set_cleanup_on_startup.assert_called_once_with(mock_ctx.guild.id, False)
    # Check that the message was edited
    mock_interaction.response.edit_message.assert_called_once()

