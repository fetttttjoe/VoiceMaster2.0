# VoiceMaster2.0/cogs/events.py
import asyncio
import logging
from collections import OrderedDict
from typing import cast

import discord
from discord.ext import commands

from bot_instance import VoiceMasterBot
from config import settings
from database.models import AuditLogEventType, Guild
from interfaces.audit_log_service import IAuditLogService
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService

# Import for safe DB value comparison
from utils.db_helpers import is_db_value_equal


class EventsCog(commands.Cog):
    """
    Handles Discord gateway events, primarily focusing on voice state updates
    to manage temporary voice channels.
    """

    def __init__(
        self,
        bot: "VoiceMasterBot",
        guild_service: IGuildService,
        voice_channel_service: IVoiceChannelService,
        audit_log_service: IAuditLogService,
    ):
        """
        Initializes the EventsCog with the bot instance and necessary services.

        Args:
            bot: The custom VoiceMasterBot instance.
            guild_service: Service for guild-related operations.
            voice_channel_service: Service for voice channel management.
            audit_log_service: Service for logging audit events.
        """
        self._bot = bot
        self._guild_service = guild_service
        self._voice_channel_service = voice_channel_service
        self._audit_log_service = audit_log_service
        self.MAX_LOCKS = settings.MAX_LOCKS  # Max number of user locks to keep in memory
        self._user_locks: OrderedDict[int, asyncio.Lock] = OrderedDict()  # Store user-specific locks to prevent rapid channel creation

    @commands.Cog.listener()
    async def on_ready(self):
        """
        Event listener that runs when the bot is ready.
        This is used to perform startup tasks like channel cleanup.
        """
        logging.info(f"{self._bot.user} has connected to Discord!")
        logging.info("Running startup channel cleanup...")
        await self._cleanup_stale_channels_on_startup()

    async def _cleanup_stale_channels_on_startup(self):
        """
        Cleans up stale temporary voice channels on bot startup.
        """
        for guild in self._bot.guilds:
            guild_config = await self._guild_service.get_guild_config(guild.id)
            if not guild_config or is_db_value_equal(guild_config.cleanup_on_startup, False):
                continue

            if guild_config.voice_category_id is None or guild_config.creation_channel_id is None:
                continue

            category = self._bot.get_channel(cast(int, guild_config.voice_category_id))
            if not isinstance(category, discord.CategoryChannel):
                logging.warning(f"Category with ID {guild_config.voice_category_id} not found for guild {guild.name}.")
                continue

            logging.info(f"Running category purge for '{category.name}' in guild '{guild.name}'...")
            purged_channels_db = []
            purged_count_api = 0
            for channel in category.voice_channels:
                if channel.id == guild_config.creation_channel_id:
                    continue

                if len(channel.members) == 0:
                    logging.info(f"PURGING: Empty channel '{channel.name}' ({channel.id}) found.")
                    try:
                        await channel.delete(reason="Bot startup cleanup: Purging empty temporary channel.")
                        purged_channels_db.append(channel.id)
                        purged_count_api += 1
                    except discord.HTTPException as e:
                        logging.error(f"Failed to purge channel {channel.id} via API: {e}")

            if purged_channels_db:
                await self._guild_service.cleanup_stale_channels(purged_channels_db)

            if purged_count_api > 0:
                logging.info(f"Category purge complete for '{category.name}'. Removed {purged_count_api} empty channels.")

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """
        Routes voice state updates to appropriate handlers based on channel changes.
        """
        if member.bot:
            return

        if not member.guild:
            return

        logging.info(f"DEBUG: Voice state update for user {member.id} in guild {member.guild.id}")
        logging.info(f"DEBUG: Before channel: {before.channel.id if before.channel else 'None'}")
        logging.info(f"DEBUG: After channel: {after.channel.id if after.channel else 'None'}")

        guild_config = await self._guild_service.get_guild_config(member.guild.id)
        if not guild_config or not isinstance(guild_config.creation_channel_id, int):
            return

        before_channel_id = before.channel.id if before.channel else None
        after_channel_id = after.channel.id if after.channel else None

        if before_channel_id != after_channel_id:
            if before.channel:
                await self._handle_user_leave(member, before, guild_config)
            if after.channel:
                await self._handle_user_join(member, after, guild_config)

    async def _handle_user_leave(self, member: discord.Member, before: discord.VoiceState, guild_config: Guild):
        """
        Handles the logic for when a user leaves a voice channel.
        """
        if before.channel and before.channel.id != guild_config.creation_channel_id:
            await self._handle_channel_leave(member, before)

    async def _handle_user_join(self, member: discord.Member, after: discord.VoiceState, guild_config: Guild):
        """
        Handles the logic for when a user joins a voice channel.
        """
        if after.channel and after.channel.id == guild_config.creation_channel_id:
            if member.id not in self._user_locks:
                if len(self._user_locks) >= self.MAX_LOCKS:
                    self._user_locks.popitem(last=False)
                self._user_locks[member.id] = asyncio.Lock()
            else:
                self._user_locks.move_to_end(member.id)

            lock = self._user_locks[member.id]
            async with lock:
                await self._handle_channel_creation(member, guild_config)

    async def _handle_channel_leave(self, member: discord.Member, before: discord.VoiceState):
        logging.info(f"DEBUG: _handle_channel_leave called for user {member.id}, channel {before.channel.id if before.channel else 'None'}")
        if not isinstance(before.channel, discord.VoiceChannel):
            return

        owned_channel = await self._voice_channel_service.get_voice_channel(before.channel.id)
        if not owned_channel:
            return

        is_owner = is_db_value_equal(member.id, owned_channel.owner_id)
        event_type = AuditLogEventType.USER_LEFT_OWNED_CHANNEL if is_owner else AuditLogEventType.USER_LEFT_TEMP_CHANNEL
        ownership_text = "their owned" if is_owner else "temporary"
        details = f"User {member.display_name} ({member.id}) left {ownership_text} channel '{before.channel.name}' ({before.channel.id})."

        await self._audit_log_service.log_event(
            guild_id=member.guild.id, event_type=event_type, user_id=member.id, channel_id=before.channel.id, details=details
        )

        if len(before.channel.members) == 0:
            await self._delete_empty_channel(before.channel)

    async def _delete_empty_channel(self, channel: discord.VoiceChannel):
        logging.info(f"DEBUG: Deleting empty channel {channel.id}")
        try:
            await channel.delete(reason="Temporary channel empty.")
            await self._voice_channel_service.delete_voice_channel(channel.id)
            await self._audit_log_service.log_event(
                guild_id=channel.guild.id,
                event_type=AuditLogEventType.CHANNEL_DELETED,
                channel_id=channel.id,
                details=f"Empty temporary channel '{channel.name}' ({channel.id}) deleted.",
            )
        except discord.NotFound:
            await self._voice_channel_service.delete_voice_channel(channel.id)
            await self._audit_log_service.log_event(
                guild_id=channel.guild.id,
                event_type=AuditLogEventType.CHANNEL_DELETED_NOT_FOUND,
                channel_id=channel.id,
                details=f"Stale DB entry for channel {channel.id} removed.",
            )
        except Exception as e:
            logging.error(f"Error deleting channel {channel.id}: {e}", exc_info=True)
            await self._audit_log_service.log_event(
                guild_id=channel.guild.id,
                event_type=AuditLogEventType.CHANNEL_DELETE_ERROR,
                channel_id=channel.id,
                details=f"Error deleting channel: {e}",
            )

    async def _handle_channel_creation(self, member: discord.Member, guild_config: Guild):
        logging.info(f"DEBUG: _handle_channel_creation called for user {member.id}")
        existing_channel = await self._voice_channel_service.get_voice_channel_by_owner(member.id)
        if existing_channel and isinstance(existing_channel.channel_id, int):
            channel = self._bot.get_channel(existing_channel.channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                await member.move_to(channel, reason="User already has a channel.")
                await self._audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.USER_MOVED_TO_EXISTING_CHANNEL,
                    user_id=member.id,
                    channel_id=existing_channel.channel_id,
                    details=f"User {member.display_name} ({member.id}) moved to their existing channel '{channel.name}' ({existing_channel.channel_id}).",
                )
            else:
                await self._voice_channel_service.delete_voice_channel(existing_channel.channel_id)
                await self._audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.STALE_CHANNEL_CLEANUP,
                    user_id=member.id,
                    channel_id=existing_channel.channel_id,
                    details=f"Stale channel {existing_channel.channel_id} (owner: {member.display_name} - {member.id}) removed from database as Discord channel was not found.",
                )
            return

        channel_name, channel_limit = await self._get_new_channel_config(member)
        if not isinstance(guild_config.voice_category_id, int):
            await self._audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CONFIG_ERROR,
                details=f"Invalid voice category ID configured: {guild_config.voice_category_id}.",
            )
            return

        category = self._bot.get_channel(guild_config.voice_category_id)
        if not isinstance(category, discord.CategoryChannel):
            await self._audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CATEGORY_NOT_FOUND,
                details=f"Configured voice category {guild_config.voice_category_id} not found or invalid for guild {member.guild.id}.",
            )
            return

        await self._create_and_move_user(member, category, channel_name, channel_limit)

    async def _get_new_channel_config(self, member: discord.Member) -> tuple[str, int]:
        user_settings = await self._voice_channel_service.get_user_settings(member.id)
        channel_name = f"{member.display_name}'s Channel"
        if user_settings and isinstance(user_settings.custom_channel_name, str):
            channel_name = user_settings.custom_channel_name
        channel_limit = 0
        if user_settings and isinstance(user_settings.custom_channel_limit, int):
            channel_limit = user_settings.custom_channel_limit
        return channel_name, channel_limit

    async def _create_and_move_user(self, member: discord.Member, category: discord.CategoryChannel, name: str, limit: int):
        try:
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(manage_channels=True, manage_roles=True, connect=True, speak=True),
            } # type: ignore
            new_channel = await member.guild.create_voice_channel(
                name=name, category=category, user_limit=limit, overwrites=cast(dict, overwrites), reason=f"Temporary channel for {member.display_name}"
            )
            await self._voice_channel_service.create_voice_channel(new_channel.id, member.id, member.guild.id)
            await member.move_to(new_channel)
            await self._audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CHANNEL_CREATED,
                user_id=member.id,
                channel_id=new_channel.id,
                details=f"New channel '{name}' created with limit: {limit}.",
            )
        except Exception as e:
            logging.error(f"Failed to create channel for {member.id}: {e}", exc_info=True)
            await self._audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CHANNEL_CREATION_FAILED,
                user_id=member.id,
                details=f"Failed to create channel: {e}",
            )

async def setup(bot: commands.Bot):
    """
    The entry point for loading the EventsCog into the bot.

    This function is called by Discord.py when loading extensions.
    It ensures that the cog receives the necessary service dependencies
    from the custom bot instance.

    Args:
        bot: The `commands.Bot` instance, which is cast to `VoiceMasterBot`
             to access custom service attributes.
    """
    # Cast the generic commands.Bot to our specific VoiceMasterBot type
    # to access the services that are attached during bot initialization.
    custom_bot = cast(VoiceMasterBot, bot)
    await bot.add_cog(
        EventsCog(
            bot=custom_bot,
            guild_service=custom_bot.guild_service,
            voice_channel_service=custom_bot.voice_channel_service,
            audit_log_service=custom_bot.audit_log_service,
        )
    )
