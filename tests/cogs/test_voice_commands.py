from typing import Any, Callable, cast
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest
from discord import ui
from discord.ext import commands

from cogs.voice_commands import VoiceCommandsCog
from database.models import AuditLogEventType
from utils import responses
from views.setup_view import SetupModal, SetupView


@pytest.fixture
def voice_commands_cog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service):
    """Fixture to create an instance of the VoiceCommandsCog with mocked services."""
    return VoiceCommandsCog(mock_bot, mock_guild_service, mock_voice_channel_service, mock_audit_log_service)


@pytest.mark.asyncio
async def test_voice_command_sends_embed(voice_commands_cog, mock_ctx):
    """Tests that the base 'voice' command sends an informational embed."""
    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)

    if voice_command.invoke_without_command:
        callback = cast(Callable[..., Any], voice_command.callback)
        await callback(voice_commands_cog, mock_ctx)
        mock_ctx.send.assert_called_once()
        sent_embed = mock_ctx.send.call_args.kwargs["embed"]
        assert sent_embed.title == responses.VOICE_HELP_TITLE


@pytest.mark.asyncio
@patch("database.database.db.get_session")
async def test_lock_command(mock_get_session, voice_commands_cog, mock_member, mock_ctx, mock_voice_channel_service, mock_audit_log_service):
    """Tests that the 'lock' command successfully locks the channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)
    mock_ctx.author = mock_member

    voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
    assert isinstance(voice_command, commands.Group)
    lock_command = voice_command.get_command("lock")
    assert lock_command is not None

    callback = cast(Callable[..., Any], lock_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_member.voice.channel.set_permissions.assert_called_once_with(mock_ctx.guild.default_role, connect=False)
    mock_ctx.send.assert_called_with(responses.CHANNEL_LOCKED, ephemeral=True)
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.CHANNEL_LOCKED


@pytest.mark.asyncio
@patch("database.database.db.get_session")
async def test_unlock_command(mock_get_session, voice_commands_cog, mock_member, mock_ctx, mock_voice_channel_service, mock_audit_log_service):
    """Tests that the 'unlock' command successfully unlocks the channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)
    mock_ctx.author = mock_member

    voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
    assert isinstance(voice_command, commands.Group)
    unlock_command = voice_command.get_command("unlock")
    assert unlock_command is not None

    callback = cast(Callable[..., Any], unlock_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_member.voice.channel.set_permissions.assert_called_once_with(mock_ctx.guild.default_role, connect=True)
    mock_ctx.send.assert_called_with(responses.CHANNEL_UNLOCKED, ephemeral=True)
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.CHANNEL_UNLOCKED


@pytest.mark.asyncio
@patch("database.database.db.get_session")
async def test_permit_command(mock_get_session, voice_commands_cog, mock_member, mock_ctx, mock_voice_channel_service, mock_audit_log_service):
    """Tests that the 'permit' command grants connect permissions."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = MagicMock(channel_id=mock_member.voice.channel.id)
    mock_ctx.author = mock_member
    permitted_member = AsyncMock(spec=discord.Member)
    permitted_member.mention = "<@12345>"

    voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
    assert isinstance(voice_command, commands.Group)
    permit_command = voice_command.get_command("permit")
    assert permit_command is not None

    callback = cast(Callable[..., Any], permit_command.callback)
    await callback(voice_commands_cog, mock_ctx, member=permitted_member)

    mock_member.voice.channel.set_permissions.assert_called_once_with(permitted_member, connect=True)
    mock_ctx.send.assert_called_with(responses.PERMIT_SUCCESS.format(member_mention=permitted_member.mention), ephemeral=True)
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.CHANNEL_PERMIT


@pytest.mark.asyncio
@patch("database.database.db.get_session")
async def test_claim_command(mock_get_session, voice_commands_cog, mock_member, mock_ctx, mock_voice_channel_service, mock_audit_log_service):
    """Tests that a user can claim an abandoned channel."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_voice_channel_service.get_voice_channel.return_value = MagicMock(owner_id=999)
    mock_ctx.author = mock_member
    mock_member.voice.channel.members = []

    with patch("discord.Guild.get_member", return_value=None):
        voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
        assert isinstance(voice_command, commands.Group)
        claim_command = voice_command.get_command("claim")
        assert claim_command is not None

        callback = cast(Callable[..., Any], claim_command.callback)
        await callback(voice_commands_cog, mock_ctx)

        mock_voice_channel_service.update_voice_channel_owner.assert_called_once_with(mock_member.voice.channel.id, mock_member.id)
        mock_member.voice.channel.set_permissions.assert_called_once_with(mock_member, manage_channels=True, manage_roles=True)
        mock_ctx.send.assert_called_with(responses.CLAIM_SUCCESS.format(author_mention=mock_member.mention), ephemeral=True)
        mock_audit_log_service.log_event.assert_called_once()
        assert mock_audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.CHANNEL_CLAIMED


@pytest.mark.asyncio
@patch("database.database.db.get_session")
async def test_name_command(mock_get_session, voice_commands_cog, mock_member, mock_ctx, mock_voice_channel_service, mock_audit_log_service):
    """Tests updating a user's future channel name."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = None
    mock_ctx.author = mock_member
    new_name = "My Awesome Channel"

    voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
    assert isinstance(voice_command, commands.Group)
    name_command = voice_command.get_command("name")
    assert name_command is not None

    callback = cast(Callable[..., Any], name_command.callback)
    await callback(voice_commands_cog, mock_ctx, new_name=new_name)

    mock_voice_channel_service.update_user_channel_name.assert_called_once_with(mock_member.id, new_name)
    mock_ctx.send.assert_called_with(responses.NAME_SUCCESS.format(new_name=new_name), ephemeral=True)
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.USER_DEFAULT_NAME_SET


@pytest.mark.asyncio
@patch("database.database.db.get_session")
async def test_limit_command(mock_get_session, voice_commands_cog, mock_member, mock_ctx, mock_voice_channel_service, mock_audit_log_service):
    """Tests updating a user's future channel limit."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_voice_channel_service.get_voice_channel_by_owner.return_value = None
    mock_ctx.author = mock_member
    new_limit = 5

    voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
    assert isinstance(voice_command, commands.Group)
    limit_command = voice_command.get_command("limit")
    assert limit_command is not None

    callback = cast(Callable[..., Any], limit_command.callback)
    await callback(voice_commands_cog, mock_ctx, new_limit=new_limit)

    mock_voice_channel_service.update_user_channel_limit.assert_called_once_with(mock_member.id, new_limit)
    mock_ctx.send.assert_called_with(responses.LIMIT_SUCCESS.format(limit_str=new_limit), ephemeral=True)
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.USER_DEFAULT_LIMIT_SET


@pytest.mark.asyncio
@patch("database.database.db.get_session")
async def test_setup_command(mock_get_session, voice_commands_cog, mock_ctx, mock_guild_service, mock_audit_log_service):
    """Tests the entire multi-step setup process using the new View and Modal flow."""
    mock_get_session.return_value.__aenter__.return_value.add = AsyncMock()
    mock_category = AsyncMock(spec=discord.CategoryChannel, id=777, name="Temp Channels")
    mock_ctx.guild.create_category.return_value = mock_category
    mock_ctx.guild.create_voice_channel.return_value = AsyncMock(spec=discord.VoiceChannel, id=888, name="Join to Create")

    voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
    assert isinstance(voice_command, commands.Group)
    setup_command = voice_command.get_command("setup")
    assert setup_command is not None
    callback = cast(Callable[..., Any], setup_command.callback)

    await callback(voice_commands_cog, mock_ctx)

    sent_view = mock_ctx.send.call_args.kwargs["view"]
    mock_ctx.send.assert_called_once_with(responses.SETUP_PROMPT, view=sent_view)
    assert isinstance(sent_view, SetupView)

    button = sent_view.children[0]
    assert isinstance(button, ui.Button)

    mock_button_interaction = AsyncMock(spec=discord.Interaction)
    mock_button_interaction.response = AsyncMock()
    await button.callback(mock_button_interaction)

    mock_button_interaction.response.send_modal.assert_called_once()
    sent_modal = mock_button_interaction.response.send_modal.call_args.args[0]
    assert isinstance(sent_modal, SetupModal)

    sent_modal.category_name = MagicMock(spec=ui.TextInput)
    sent_modal.channel_name = MagicMock(spec=ui.TextInput)
    sent_modal.category_name.value = "Temp Channels"
    sent_modal.channel_name.value = "Join to Create"

    mock_modal_interaction = AsyncMock(spec=discord.Interaction)
    mock_modal_interaction.guild = mock_ctx.guild
    mock_modal_interaction.user = mock_ctx.author
    mock_modal_interaction.response = AsyncMock()

    await sent_modal.on_submit(mock_modal_interaction)

    mock_ctx.guild.create_category.assert_called_once_with("Temp Channels")
    mock_ctx.guild.create_voice_channel.assert_called_once_with(name="Join to Create", category=mock_category)
    mock_guild_service.create_or_update_guild.assert_called_once()
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.BOT_SETUP
    mock_modal_interaction.response.send_message.assert_called_once()


@pytest.mark.asyncio
async def test_edit_command_no_subcommand(voice_commands_cog, mock_ctx):
    """Tests that the edit command prompts for a subcommand if none is given."""
    voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
    assert isinstance(voice_command, commands.Group)
    edit_command = voice_command.get_command("edit")
    assert edit_command is not None

    callback = cast(Callable[..., Any], edit_command.callback)
    await callback(voice_commands_cog, mock_ctx)
    mock_ctx.send.assert_called_with(responses.EDIT_PROMPT)


@pytest.mark.asyncio
@patch("database.database.db.get_session")
async def test_list_command(mock_get_session, voice_commands_cog, mock_ctx, mock_guild_service, mock_audit_log_service, mock_bot):
    """Tests the list command for active channels."""
    mock_get_session.return_value.__aenter__.return_value.add = MagicMock()
    mock_guild_service.get_voice_channels_by_guild.return_value = [
        MagicMock(channel_id=1, owner_id=10),
        MagicMock(channel_id=2, owner_id=20),
    ]
    mock_ctx.guild.get_channel.return_value = AsyncMock(spec=discord.VoiceChannel, name="Channel1", mention="<#1>", guild=mock_ctx.guild)
    mock_bot.get_user.side_effect = [
        AsyncMock(spec=discord.User, mention="<@10>"),
        AsyncMock(spec=discord.User, mention="<@20>"),
    ]

    voice_command = next(cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice")
    assert isinstance(voice_command, commands.Group)
    list_command = voice_command.get_command("list")
    assert list_command is not None

    callback = cast(Callable[..., Any], list_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_guild_service.get_voice_channels_by_guild.assert_called_once_with(mock_ctx.guild.id)
    mock_ctx.send.assert_called_once()
    sent_embed = mock_ctx.send.call_args.kwargs["embed"]
    assert sent_embed.title == responses.LIST_TITLE
    mock_audit_log_service.log_event.assert_called_once()
    assert mock_audit_log_service.log_event.call_args.kwargs["event_type"] == AuditLogEventType.LIST_CHANNELS


@pytest.mark.asyncio
async def test_config_command_no_config(voice_commands_cog, mock_ctx, mock_guild_service):
    """Tests that the config command sends an error message if the bot is not set up."""
    mock_guild_service.get_guild_config.return_value = None

    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    config_command = voice_command.get_command("config")
    assert config_command is not None

    callback = cast(Callable[..., Any], config_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(responses.BOT_NOT_SETUP.format(prefix=mock_ctx.prefix), ephemeral=True)


@pytest.mark.asyncio
async def test_edit_rename_command_no_config(voice_commands_cog, mock_ctx, mock_guild_service):
    """Tests that the edit_rename command sends an error message if the bot is not set up."""
    mock_guild_service.get_guild_config.return_value = None

    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    edit_command = voice_command.get_command("edit")
    assert edit_command is not None and isinstance(edit_command, commands.Group)
    rename_command = edit_command.get_command("rename")
    assert rename_command is not None

    callback = cast(Callable[..., Any], rename_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(responses.BOT_NOT_SETUP, ephemeral=True)


@pytest.mark.asyncio
async def test_edit_select_command_no_config(voice_commands_cog, mock_ctx, mock_guild_service):
    """Tests that the edit_select command sends an error message if the bot is not set up."""
    mock_guild_service.get_guild_config.return_value = None

    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    edit_command = voice_command.get_command("edit")
    assert edit_command is not None and isinstance(edit_command, commands.Group)
    select_command = edit_command.get_command("select")
    assert select_command is not None

    callback = cast(Callable[..., Any], select_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(responses.BOT_NOT_SETUP, ephemeral=True)


@pytest.mark.asyncio
async def test_edit_select_command_no_voice_channels(voice_commands_cog, mock_ctx, mock_guild_service):
    """Tests that the edit_select command sends an error message if there are no voice channels."""
    mock_guild_service.get_guild_config.return_value = MagicMock()
    mock_ctx.guild.voice_channels = []

    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    edit_command = voice_command.get_command("edit")
    assert edit_command is not None and isinstance(edit_command, commands.Group)
    select_command = edit_command.get_command("select")
    assert select_command is not None

    callback = cast(Callable[..., Any], select_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(responses.EDIT_SELECT_NO_CHANNELS, ephemeral=True)


@pytest.mark.asyncio
async def test_edit_select_command_no_categories(voice_commands_cog, mock_ctx, mock_guild_service):
    """Tests that the edit_select command sends an error message if there are no categories."""
    mock_guild_service.get_guild_config.return_value = MagicMock()
    mock_ctx.guild.voice_channels = [MagicMock(spec=discord.VoiceChannel, category=MagicMock())]
    mock_ctx.guild.categories = []

    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    edit_command = voice_command.get_command("edit")
    assert edit_command is not None and isinstance(edit_command, commands.Group)
    select_command = edit_command.get_command("select")
    assert select_command is not None

    callback = cast(Callable[..., Any], select_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(responses.EDIT_SELECT_NO_CATEGORIES, ephemeral=True)


@pytest.mark.asyncio
async def test_list_channels_no_channels(voice_commands_cog, mock_ctx, mock_guild_service):
    """Tests that the list command sends a message when there are no active channels."""
    mock_guild_service.get_voice_channels_by_guild.return_value = []

    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    list_channels_command = voice_command.get_command("list")
    assert list_channels_command is not None

    callback = cast(Callable[..., Any], list_channels_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(responses.LIST_NO_CHANNELS, ephemeral=True)


@pytest.mark.asyncio
async def test_claim_command_not_temp_channel(voice_commands_cog, mock_ctx, mock_member, mock_voice_channel_service):
    """Tests that the claim command sends an error message if the channel is not a temporary channel."""
    mock_voice_channel_service.get_voice_channel.return_value = None
    mock_ctx.author = mock_member

    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    claim_command = voice_command.get_command("claim")
    assert claim_command is not None

    callback = cast(Callable[..., Any], claim_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(responses.CLAIM_NOT_TEMP_CHANNEL, ephemeral=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("name", ["a", "a" * 101])
async def test_name_command_invalid_length(voice_commands_cog, mock_ctx, name):
    """Tests that the name command sends an error message if the name is too short or too long."""
    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    name_command = voice_command.get_command("name")
    assert name_command is not None

    callback = cast(Callable[..., Any], name_command.callback)
    await callback(voice_commands_cog, mock_ctx, new_name=name)

    mock_ctx.send.assert_called_once_with(responses.NAME_LENGTH_ERROR, ephemeral=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("limit", [-1, 100])
async def test_limit_command_invalid_limit(voice_commands_cog, mock_ctx, limit):
    """Tests that the limit command sends an error message if the limit is out of range."""
    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    limit_command = voice_command.get_command("limit")
    assert limit_command is not None

    callback = cast(Callable[..., Any], limit_command.callback)
    await callback(voice_commands_cog, mock_ctx, new_limit=limit)

    mock_ctx.send.assert_called_once_with(responses.LIMIT_RANGE_ERROR, ephemeral=True)


@pytest.mark.asyncio
async def test_auditlog_command_no_logs(voice_commands_cog, mock_ctx, mock_audit_log_service):
    """Tests that the auditlog command sends a message when there are no logs."""
    mock_audit_log_service.get_latest_logs.return_value = []

    voice_command = next((cmd for cmd in voice_commands_cog.get_commands() if cmd.name == "voice"), None)
    assert voice_command is not None and isinstance(voice_command, commands.Group)
    auditlog_command = voice_command.get_command("auditlog")
    assert auditlog_command is not None

    callback = cast(Callable[..., Any], auditlog_command.callback)
    await callback(voice_commands_cog, mock_ctx)

    mock_ctx.send.assert_called_once_with(responses.AUDIT_LOG_NO_ENTRIES, ephemeral=True)
