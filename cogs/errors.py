import logging

import discord
from discord.ext import commands

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
                f"⚠️ {original_error}",
                ephemeral=True,
                delete_after=10,
            )

        if isinstance(original_error, commands.CommandNotFound):
            return
        elif isinstance(original_error, commands.MissingPermissions):
            missing_perms = ", ".join(original_error.missing_permissions).replace("_", " ").title()
            return await ctx.send(
                f"🚫 You don't have the required permissions (`{missing_perms}`) to use this command.",
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.NoPrivateMessage):
            return await ctx.send(
                "This command cannot be used in private messages.",
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.UserInputError):
            return await ctx.send(
                f"🤔 Invalid input: {original_error}. Please check your arguments.",
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.CheckFailure):
            return await ctx.send("You do not meet the requirements to run this command.", ephemeral=True, delete_after=10)
        elif isinstance(original_error, discord.Forbidden):
            return await ctx.send(
                "🚫 I don't have the required permissions to perform this action. Please check my role and channel permissions.",
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, discord.HTTPException):
            return await ctx.send(
                "An error occurred while communicating with Discord. Please try again later.",
                ephemeral=True,
                delete_after=10,
            )

        command_name = ctx.command.name if ctx.command else "unknown"
        logging.error(
            f"An unhandled error occurred in command '{command_name}' (Guild ID: {ctx.guild.id if ctx.guild else 'N/A'}):",
            exc_info=original_error,
        )

        await ctx.send(
            "An unexpected error occurred. This has been logged for review. Please try again later.",
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
