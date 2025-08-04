import logging

import discord
from discord.ext import commands

from utils import responses
from utils.checks import VoiceChannelCheckError


class ErrorHandlerCog(commands.Cog):
    """
    A global error handler for the bot's commands.

    This cog centralizes error handling, providing user-friendly messages for common
    command errors (e.g., missing permissions, command not found) and logging
    unexpected errors for debugging.
    """

    def __init__(self, bot: commands.Bot):
        """
        Initializes the ErrorHandlerCog.

        Args:
            bot: The Discord bot instance.
        """
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        """
        Global error handler for all commands.

        This method is automatically called by Discord.py when a command
        encounters an error. It attempts to provide specific feedback
        to the user for known error types, and a generic message for
        unhandled exceptions, which are also logged.

        Args:
            ctx: The `commands.Context` object representing the invocation context.
            error: The `commands.CommandError` instance that was raised.
        """
        # Skip handling if the command defines its own error handler
        if hasattr(ctx.command, "on_error"):
            return

        original_error = getattr(error, "original", error)

        # Pattern-match the error type for cleaner dispatch
        match original_error:
            case VoiceChannelCheckError() as e:
                await ctx.send(
                    f"{responses.ERROR_PREFIX} {e}",
                    ephemeral=True,
                    delete_after=10,
                )
                return

            case commands.CommandNotFound():
                return

            case commands.MissingPermissions(missing_permissions=perms):
                missing = ", ".join(perms).replace("_", " ").title()
                await ctx.send(
                    responses.MISSING_PERMISSIONS.format(perms=missing),
                    ephemeral=True,
                    delete_after=10,
                )
                return

            case commands.NoPrivateMessage():
                await ctx.send(
                    responses.NO_PRIVATE_MESSAGE,
                    ephemeral=True,
                    delete_after=10,
                )
                return

            case commands.UserInputError() as e:
                await ctx.send(
                    responses.USER_INPUT_ERROR.format(error=e),
                    ephemeral=True,
                    delete_after=10,
                )
                return

            case commands.CheckFailure():
                await ctx.send(
                    responses.CHECK_FAILURE,
                    ephemeral=True,
                    delete_after=10,
                )
                return

            case discord.Forbidden():
                await ctx.send(
                    responses.FORBIDDEN_ERROR,
                    ephemeral=True,
                    delete_after=10,
                )
                return

            case discord.HTTPException():
                await ctx.send(
                    responses.HTTP_EXCEPTION,
                    ephemeral=True,
                    delete_after=10,
                )
                return

            case _:
                cmd_name = ctx.command.name if ctx.command else "unknown"
                guild_id = ctx.guild.id if ctx.guild else 'N/A'
                logging.error(
                    f"Unhandled error in command '{cmd_name}' (Guild ID: {guild_id}):",
                    exc_info=original_error,
                )
                await ctx.send(
                    responses.UNHANDLED_EXCEPTION,
                    ephemeral=True,
                    delete_after=10,
                )


async def setup(bot: commands.Bot):
    """
    The entry point for loading the ErrorHandlerCog into the bot.

    Args:
        bot: The `commands.Bot` instance.
    """
    await bot.add_cog(ErrorHandlerCog(bot))
