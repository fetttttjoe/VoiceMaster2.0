# tests/cogs/test_errors.py
from unittest.mock import AsyncMock

import discord
import pytest
from discord.ext import commands

from cogs.errors import ErrorHandlerCog
from utils.checks import VoiceChannelCheckError


@pytest.fixture
def mock_bot():
    """Fixture for a mocked Discord bot instance."""
    return AsyncMock(spec=commands.Bot)


@pytest.fixture
def mock_ctx():
    """Fixture for a mocked context object."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.command = AsyncMock(spec=commands.Command)
    ctx.command.name = "test_command"
    ctx.send = AsyncMock()
    return ctx


@pytest.mark.asyncio
async def test_on_command_error_handles_voice_channel_check_error(mock_bot, mock_ctx):
    """Tests that VoiceChannelCheckError is handled correctly."""
    cog = ErrorHandlerCog(mock_bot)
    error = VoiceChannelCheckError("You must be in a voice channel.")
    await cog.on_command_error(mock_ctx, error)
    mock_ctx.send.assert_called_once_with(
        "⚠️ You must be in a voice channel.",
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_on_command_error_handles_missing_permissions(mock_bot, mock_ctx):
    """Tests that MissingPermissions is handled correctly."""
    cog = ErrorHandlerCog(mock_bot)
    error = commands.MissingPermissions(["manage_channels"])
    await cog.on_command_error(mock_ctx, error)
    mock_ctx.send.assert_called_once_with(
        "🚫 You don't have the required permissions (`Manage Channels`) to use this command.",
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_on_command_error_handles_discord_forbidden(mock_bot, mock_ctx):
    """Tests that discord.Forbidden is handled correctly."""
    cog = ErrorHandlerCog(mock_bot)
    error = discord.Forbidden(response=AsyncMock(), message="Missing Permissions")
    await cog.on_command_error(mock_ctx, commands.CommandInvokeError(error))
    mock_ctx.send.assert_called_once_with(
        "🚫 I don't have the required permissions to perform this action. Please check my role and channel permissions.",
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_on_command_error_handles_unhandled_error(mock_bot, mock_ctx):
    """Tests that a generic error message is sent for unhandled exceptions."""
    cog = ErrorHandlerCog(mock_bot)
    error = Exception("Some random error")
    await cog.on_command_error(mock_ctx, error)
    mock_ctx.send.assert_called_once_with(
        "An unexpected error occurred. This has been logged for review. Please try again later.",
        ephemeral=True,
        delete_after=10,
    )
