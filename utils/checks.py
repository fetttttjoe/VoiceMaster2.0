# VoiceMaster2.0/utils/checks.py
from typing import cast  # Used for explicit type casting to help Pylance/type checkers

import discord
from discord.ext import commands
from discord.ext.commands import Context

from interfaces.voice_channel_service import IVoiceChannelService  # Import the service interface for type hinting
from main import VoiceMasterBot  # Import the custom bot class for type hinting
from utils.db_helpers import is_db_value_equal  # Custom helper for safe database value comparison

# --- Custom Exception Classes for Command Checks ---


class VoiceChannelCheckError(commands.CheckFailure):
    """Base exception for all custom voice channel related command check failures."""

    pass


class NotInVoiceChannel(VoiceChannelCheckError):
    """
    Exception raised when a command requires the user to be in a voice channel,
    but they are not.
    """

    def __init__(self, message="You are not in a voice channel."):
        super().__init__(message)


class NotChannelOwner(VoiceChannelCheckError):
    """
    Exception raised when a command requires the user to own the voice channel
    they are currently in, but they do not.
    """

    def __init__(self, message="You do not own this voice channel."):
        super().__init__(message)


# --- Custom Command Check Decorators ---


def is_in_voice_channel():
    """
    A command check that ensures the user invoking the command is currently in a voice channel.

    If the user is not in a voice channel, it raises a `NotInVoiceChannel` exception,
    which can be caught by the bot's global error handler.
    """

    async def predicate(ctx: Context) -> bool:
        # Ensure ctx.author is a Discord Member and has a voice state with an active channel.
        # This prevents AttributeError if a command is used in DM or by a webhook, or if
        # the user is not in a voice channel.
        if not isinstance(ctx.author, discord.Member) or not ctx.author.voice or not ctx.author.voice.channel:
            raise NotInVoiceChannel()
        return True

    return commands.check(predicate)  # Register the predicate as a command check


def is_channel_owner():
    """
    A command check that ensures the user invoking the command is the owner of
    the temporary voice channel they are currently in.

    This check implicitly includes `is_in_voice_channel` as it first verifies
    the user's voice state. It then queries the database via the `VoiceChannelService`
    to confirm ownership.

    If the user is not in a voice channel, `NotInVoiceChannel` is raised.
    If they are in a voice channel but don't own it (or it's not a temporary bot channel),
    `NotChannelOwner` is raised.
    """

    async def predicate(ctx: Context) -> bool:
        # First, ensure the user is in a voice channel. This also handles non-member contexts.
        if not isinstance(ctx.author, discord.Member) or not ctx.author.voice or not ctx.author.voice.channel:
            raise NotInVoiceChannel()

        # Safely cast ctx.bot to our custom VoiceMasterBot class
        # to access its attached services through type hints.
        bot = cast(VoiceMasterBot, ctx.bot)
        # Retrieve the voice channel service instance from the bot.
        vc_service: IVoiceChannelService = bot.voice_channel_service

        # Attempt to retrieve the voice channel from the database using its Discord channel ID.
        # This will return None if it's not a bot-managed temporary channel.
        vc = await vc_service.get_voice_channel(ctx.author.voice.channel.id)

        # Check if the channel is registered as a temporary channel AND if the user is its owner.
        # The `is_db_value_equal` helper ensures a robust and type-safe comparison,
        # especially important when dealing with SQLAlchemy attributes that might be None.
        if vc is None or not is_db_value_equal(vc.owner_id, ctx.author.id):
            raise NotChannelOwner()

        return True

    return commands.check(predicate)  # Register the predicate as a command check
