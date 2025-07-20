import inspect
import discord
from functools import wraps
from typing import Callable, Any, cast

from discord.ext.commands import Context
from database.models import AuditLogEventType
from utils.formatters import format_template
from main import VoiceMasterBot # Import the custom bot class for type hinting

def audit_log(event_type: AuditLogEventType, details_template: str) -> Callable:
    """
    A decorator to automatically log an audit event after a command runs.
    It retrieves the AuditLogService from the bot instance.
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
            
            ctx = bound_args.arguments.get('ctx')
            
            if not isinstance(ctx, Context) or not ctx.guild:
                return result

            # Cast ctx.bot to our custom bot class to inform Pylance about the service attributes
            bot_instance = cast(VoiceMasterBot, ctx.bot)
            audit_service = bot_instance.audit_log_service

            channel_id = None
            if isinstance(ctx.author, discord.Member) and ctx.author.voice and ctx.author.voice.channel:
                channel_id = ctx.author.voice.channel.id
            elif ctx.channel:
                channel_id = ctx.channel.id

            # Format the details message using the command's arguments
            details = format_template(details_template, **bound_args.arguments)

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
