# VoiceMaster2.0/services/audit_decorator.py
import inspect
import discord
from functools import wraps
from typing import Callable, Any

from discord.ext.commands import Context

from database.database import db
from database.models import AuditLogEventType
from services.audit_log_service import AuditLogService
from utils.formatters import format_template

def audit_log(event_type: AuditLogEventType, details_template: str) -> Callable:
    """
    A decorator to automatically log an audit event after a command runs.

    Args:
        event_type: The type of event to log.
        details_template: A string template for the log details.
                          Placeholders can access arguments of the decorated function.
                          e.g., "User {ctx.author.name} used the command."
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            # Execute the original command logic first
            result = await func(*args, **kwargs)

            # --- After execution, perform the logging ---
            
            # Bind the arguments passed to the function to their names
            sig = inspect.signature(func)
            bound_args = sig.bind(*args, **kwargs)
            bound_args.apply_defaults()
            
            # The context (ctx) is essential for logging
            ctx = bound_args.arguments.get('ctx')
            
            # Ensure ctx and ctx.guild are valid before proceeding.
            if not isinstance(ctx, Context) or not ctx.guild:
                return result

            # Determine the channel ID from the context if possible
            channel_id = None
            # The author in a guild command context is always a Member, which has a voice state.
            if isinstance(ctx.author, discord.Member) and ctx.author.voice and ctx.author.voice.channel:
                channel_id = ctx.author.voice.channel.id
            elif ctx.channel:
                channel_id = ctx.channel.id

            # Format the details message using the command's arguments
            details = format_template(details_template, **bound_args.arguments)

            async with db.get_session() as session:
                audit_service = AuditLogService(session)
                await audit_service.log_event(
                    guild_id=ctx.guild.id,
                    event_type=event_type,
                    user_id=ctx.author.id,
                    channel_id=channel_id,
                    details=details
                )
            
            return result
        return wrapper
    return decorator
