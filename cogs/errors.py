# VoiceMaster2.0/cogs/errors.py
import logging  # Import logging for unhandled errors

from discord.ext import commands

from utils.checks import VoiceChannelCheckError  # Custom exception for voice channel checks


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

        # If a command has its own local `on_error` handler, this global handler
        # should not process that specific command's errors to avoid double handling.
        if hasattr(ctx.command, "on_error"):
            return

        # Unwrap the error to get the original exception that caused the `CommandError`.
        # This is important because Discord.py often wraps exceptions (e.g., CheckFailure, CommandInvokeError).
        original_error = getattr(error, "original", error)

        # --- Handle Custom Check Failures ---
        # Prioritize handling custom check exceptions defined in `utils.checks.py`.
        if isinstance(original_error, VoiceChannelCheckError):
            # Send the specific error message from our custom check to the user.
            # Messages are ephemeral and self-deleting for cleanliness.
            return await ctx.send(
                f"⚠️ {original_error}",
                ephemeral=True,
                delete_after=10,
            )

        # --- Handle Other Common Discord.py Command Errors ---
        if isinstance(original_error, commands.CommandNotFound):
            # Silently ignore commands that don't exist. This prevents the bot
            # from spamming error messages for every non-existent command typed in a guild.
            return
        elif isinstance(original_error, commands.MissingPermissions):
            # Handle cases where the user lacks required Discord permissions.
            missing_perms = ", ".join(original_error.missing_permissions).replace("_", " ").title()
            return await ctx.send(
                f"🚫 You don't have the required permissions (`{missing_perms}`) to use this command.",
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.NoPrivateMessage):
            # Handle commands that are restricted to guild channels only.
            return await ctx.send(
                "This command cannot be used in private messages.",
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.UserInputError):
            # Catch general errors related to incorrect user input (e.g., bad argument types).
            return await ctx.send(
                f"🤔 Invalid input: {original_error}. Please check your arguments.",
                ephemeral=True,
                delete_after=10,
            )
        elif isinstance(original_error, commands.CheckFailure):
            # A generic catch-all for any other `commands.CheckFailure` that isn't
            # specifically handled by our custom exceptions (e.g., `commands.has_role`).
            return await ctx.send("You do not meet the requirements to run this command.", ephemeral=True, delete_after=10)

        # --- Log and Respond to Unhandled Errors ---
        # For any other unhandled exceptions, log the full traceback for debugging.
        command_name = ctx.command.name if ctx.command else "unknown"
        logging.error(
            f"An unhandled error occurred in command '{command_name}' (Guild ID: {ctx.guild.id if ctx.guild else 'N/A'}):",
            exc_info=original_error,
        )

        # Send a generic error message to the user, indicating that the issue has been logged.
        await ctx.send(
            "An unexpected error occurred. This has been logged for review. Please try again later.",
            ephemeral=True,
            delete_after=10,
        )

        # Send a generic error message to the user, indicating that the issue has been logged.
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
