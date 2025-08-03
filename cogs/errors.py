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
        if hasattr(ctx.command, "on_error"):
            return

        original_error = getattr(error, "original", error)

        if isinstance(original_error, VoiceChannelCheckError):
            return await ctx.send(
                f"{responses.ERROR_PREFIX} {original_error}",
                ephemeral=True,
                delete_after=10,
            )

        if isinstance(original_error, commands.CommandNotFound):
            return
        elif isinstance(original_error, commands.MissingPermissions):
            missing_perms = ", ".join(original_error.missing_permissions).replace("_", " ").title()
            return await ctx.send(
                responses.MISSING_PERMISSIONS.format(perms=missing_perms),
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.NoPrivateMessage):
            return await ctx.send(
                responses.NO_PRIVATE_MESSAGE,
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.UserInputError):
            return await ctx.send(
                responses.USER_INPUT_ERROR.format(error=original_error),
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.CheckFailure):
            return await ctx.send(responses.CHECK_FAILURE, ephemeral=True, delete_after=10)
        elif isinstance(original_error, discord.Forbidden):
            return await ctx.send(
                responses.FORBIDDEN_ERROR,
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, discord.HTTPException):
            return await ctx.send(
                responses.HTTP_EXCEPTION,
                ephemeral=True,
                delete_after=10,
            )

        command_name = ctx.command.name if ctx.command else "unknown"
        logging.error(
            f"An unhandled error occurred in command '{command_name}' (Guild ID: {ctx.guild.id if ctx.guild else 'N/A'}):",
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

    This function is called by Discord.py when loading extensions.

    Args:
        bot: The `commands.Bot` instance.
    """
    await bot.add_cog(ErrorHandlerCog(bot))
