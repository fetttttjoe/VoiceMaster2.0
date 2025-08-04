import logging
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from cogs.errors import ErrorHandlerCog
from utils import responses
from utils.checks import VoiceChannelCheckError


def make_ctx():
    """Helper to create a mock Context with send coroutine."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.command = AsyncMock(spec=commands.Command)
    ctx.command.name = "test_command"
    ctx.send = AsyncMock()
    ctx.guild = None
    return ctx


@pytest.mark.asyncio
async def test_handles_voice_channel_check_error():
    bot = MagicMock()
    cog = ErrorHandlerCog(bot)
    ctx = make_ctx()
    error = VoiceChannelCheckError("You must join")

    await cog.on_command_error(ctx, commands.CommandInvokeError(error))

    ctx.send.assert_awaited_once_with(
        f"{responses.ERROR_PREFIX} You must join",
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_handles_missing_permissions():
    bot = MagicMock()
    cog = ErrorHandlerCog(bot)
    ctx = make_ctx()
    error = commands.MissingPermissions(missing_permissions=["manage_channels"])

    await cog.on_command_error(ctx, error)

    ctx.send.assert_awaited_once_with(
        responses.MISSING_PERMISSIONS.format(perms="Manage Channels"),
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_handles_no_private_message():
    bot = MagicMock()
    cog = ErrorHandlerCog(bot)
    ctx = make_ctx()
    error = commands.NoPrivateMessage()

    await cog.on_command_error(ctx, error)

    ctx.send.assert_awaited_once_with(
        responses.NO_PRIVATE_MESSAGE,
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_handles_user_input_error():
    bot = MagicMock()
    cog = ErrorHandlerCog(bot)
    ctx = make_ctx()
    error = commands.UserInputError("bad input")

    await cog.on_command_error(ctx, error)

    ctx.send.assert_awaited_once_with(
        responses.USER_INPUT_ERROR.format(error=error),
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_handles_check_failure():
    bot = MagicMock()
    cog = ErrorHandlerCog(bot)
    ctx = make_ctx()
    error = commands.CheckFailure()

    await cog.on_command_error(ctx, error)

    ctx.send.assert_awaited_once_with(
        responses.CHECK_FAILURE,
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_handles_forbidden_error():
    bot = MagicMock()
    cog = ErrorHandlerCog(bot)
    ctx = make_ctx()
    underlying = discord.Forbidden(response=AsyncMock(), message="forbidden")

    await cog.on_command_error(ctx, commands.CommandInvokeError(underlying))

    ctx.send.assert_awaited_once_with(
        responses.FORBIDDEN_ERROR,
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_handles_http_exception():
    bot = MagicMock()
    cog = ErrorHandlerCog(bot)
    ctx = make_ctx()
    underlying = discord.HTTPException(response=AsyncMock(), message="http error")

    await cog.on_command_error(ctx, commands.CommandInvokeError(underlying))

    ctx.send.assert_awaited_once_with(
        responses.HTTP_EXCEPTION,
        ephemeral=True,
        delete_after=10,
    )


@pytest.mark.asyncio
async def test_handles_unhandled_exception_and_logs(caplog):
    caplog.set_level(logging.ERROR)
    bot = MagicMock()
    cog = ErrorHandlerCog(bot)
    ctx = make_ctx()
    err = Exception("oopsie")

    await cog.on_command_error(ctx, commands.CommandInvokeError(err))

    assert "Unhandled error in command" in caplog.text
    ctx.send.assert_awaited_once_with(
        responses.UNHANDLED_EXCEPTION,
        ephemeral=True,
        delete_after=10,
    )
