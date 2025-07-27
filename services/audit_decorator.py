import inspect
from functools import wraps
from typing import Any, Callable, cast

import discord
from discord.ext.commands import Context

from database.models import AuditLogEventType
from main import VoiceMasterBot  # Import the custom bot class for type hinting
from utils.formatters import format_template


def audit_log(event_type: AuditLogEventType, details_template: str) -> Callable:
    """
    A decorator to automatically log an audit event after a command successfully executes.

    This decorator is designed to be applied to asynchronous Discord.py command functions.
    It captures the command's context (`ctx`) and its arguments, uses them to format
    a detailed log message based on a provided template, and then logs the event
    to the `AuditLogService` obtained from the bot instance.

    Args:
        event_type: The type of audit event to log, chosen from `AuditLogEventType`.
        details_template: A f-string-like template for the `details` field of the audit log.
                          It can use placeholders like `{ctx.author.display_name}`,
                          `{member.mention}`, or any argument name of the decorated function.

    Returns:
        A Callable that wraps the original command function, adding audit logging functionality.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Execute the original command logic first.
            # This ensures that the command's primary function is performed
            # before any logging, and its result is captured.
            result = await func(*args, **kwargs)

            # --- After successful command execution, perform the audit logging ---

            # Use `inspect.signature` to bind the passed arguments to their parameter names.
            # This allows easy access to argument values by name (e.g., `bound_args.arguments['ctx']`).
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()  # Apply default values for missing arguments

            # Extract the `ctx` (Context) object from the bound arguments.
            # The decorator expects `ctx` to be present as the first argument in commands.
            ctx = bound_args.arguments.get("ctx")

            # If `ctx` is not a valid Discord `Context` or if there's no guild (e.g., DM channel),
            # then audit logging is not applicable for this event, so we return early.
            if not isinstance(ctx, Context) or not ctx.guild:
                return result

            # Safely cast `ctx.bot` to `VoiceMasterBot` to inform type checkers
            # that our custom bot instance has `guild_service`, `voice_channel_service`,
            # and `audit_log_service` attributes.
            bot_instance = cast(VoiceMasterBot, ctx.bot)
            audit_service = bot_instance.audit_log_service

            # Determine the relevant channel ID for the log entry.
            # Prioritize the voice channel if the user is in one, otherwise use the text channel.
            channel_id = None
            if isinstance(ctx.author, discord.Member) and ctx.author.voice and ctx.author.voice.channel:
                channel_id = ctx.author.voice.channel.id
            elif ctx.channel:
                channel_id = ctx.channel.id

            # Format the `details` message for the audit log using the provided template
            # and the command's bound arguments. The `format_template` utility handles
            # nested attribute access and gracefully manages missing data.
            details = format_template(details_template, **bound_args.arguments)

            # Log the event using the `AuditLogService`.
            await audit_service.log_event(
                guild_id=ctx.guild.id,
                event_type=event_type,
                user_id=ctx.author.id,
                channel_id=channel_id,
                details=details,
            )

            return result

        return wrapper

    return decorator
