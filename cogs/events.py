# VoiceMaster2.0/cogs/events.py
import logging
import discord
from discord.ext import commands
from typing import cast, Optional
import asyncio
from collections import OrderedDict 

# Import necessary models
from database.models import Guild, AuditLogEventType, UserSettings

# Abstractions for dependency injection
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from interfaces.audit_log_service import IAuditLogService
from main import VoiceMasterBot  # Import your custom bot class for type hinting
# Import for safe DB value comparison
from utils.db_helpers import is_db_value_equal


class EventsCog(commands.Cog):
    """
    Handles Discord gateway events, primarily focusing on voice state updates
    to manage temporary voice channels.
    """

    def __init__(
        self,
        bot: VoiceMasterBot,
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
        self._user_locks = OrderedDict()
        self.MAX_LOCKS = 10000  # Max number of user locks to keep in memory

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """
        Routes voice state updates to appropriate handlers based on channel changes.

        This listener is triggered whenever a member's voice state changes,
        e.g., joining, leaving, muting, deafening, etc. It specifically checks
        for channel changes to manage temporary voice channels.

        Args:
            member: The `discord.Member` whose voice state changed.
            before: The `discord.VoiceState` before the change.
            after: The `discord.VoiceState` after the change.
        """
        # Ignore bot users to prevent self-triggering loops or unwanted actions.
        if member.bot:
            logging.info(f"DEBUG: Ignoring bot user {member.id}")
            return

        # Ensure the member is in a guild context.
        if not member.guild:
            logging.warning(
                f"Voice state update for member {member.id} not in a guild.")
            return

        logging.info(
            f"DEBUG: Voice state update for user {member.id} in guild {member.guild.id}")
        logging.info(
            f"DEBUG: Before channel: {before.channel.id if before.channel else 'None'}")
        logging.info(
            f"DEBUG: After channel: {after.channel.id if after.channel else 'None'}")

        # Retrieve the guild configuration to identify the creation channel.
        guild_config = await self._guild_service.get_guild_config(member.guild.id)
        logging.info(
            f"DEBUG: Guild config retrieved: {guild_config.creation_channel_id if guild_config else 'None'}")

        # If no guild configuration exists or the creation channel ID is invalid,
        # the bot is not set up for this guild, so we ignore the event.
        if not guild_config or not isinstance(guild_config.creation_channel_id, int):
            logging.info(
                f"DEBUG: Ignoring voice state update in guild {member.guild.id}: Bot not configured or invalid creation channel ID.")
            return

        # At this point, guild_config is not None, and guild_config.creation_channel_id is an int.
        # We can safely cast it to help Pylance.
        creation_channel_id = cast(int, guild_config.creation_channel_id)
        logging.info(f"DEBUG: Creation channel ID: {creation_channel_id}")

        # --- Handle User Leaving a Voice Channel ---
        # Check if the user was in a channel BEFORE this update and is now in a different one or none.
        # We also ensure it's not the creation channel, as leaving that has a different flow.
        # Added type guard for Pylance
        if before.channel and isinstance(before.channel, discord.VoiceChannel):
            # Cast before.channel to discord.VoiceChannel after the check to reassure Pylance.
            channel_before = cast(discord.VoiceChannel, before.channel)
            logging.info(
                f"DEBUG: User left channel {channel_before.id}. Comparing with creation channel {creation_channel_id}.")
            if not is_db_value_equal(channel_before.id, creation_channel_id):
                logging.info(
                    f"DEBUG: Calling _handle_channel_leave for channel {channel_before.id}")
                await self._handle_channel_leave(member, before)
            else:
                logging.info(
                    f"DEBUG: User left creation channel. Not calling _handle_channel_leave.")

        # --- Handle User Joining the "Create" Channel ---
        # Check if the user is now in a channel AFTER this update and that channel is the creation channel.
        # Added type guard for Pylance
        if after.channel and isinstance(after.channel, discord.VoiceChannel):
            logging.info(
                f"DEBUG: User joined channel {after.channel.id}. Comparing with creation channel {creation_channel_id}.")
            if is_db_value_equal(after.channel.id, creation_channel_id):
                logging.info(
                    f"DEBUG: Calling _handle_channel_creation for channel {after.channel.id}")
                if member.id not in self._user_locks:
                    if len(self._user_locks) >= self.MAX_LOCKS:
                        self._user_locks.popitem(last=False)
                    self._user_locks[member.id] = asyncio.Lock()
                else:
                    self._user_locks.move_to_end(member.id)

                lock = self._user_locks[member.id]
                async with lock:
                    await self._handle_channel_creation(member, guild_config)
            else:
                logging.info(
                    f"DEBUG: User joined non-creation channel. Not calling _handle_channel_creation.")

    async def _handle_channel_leave(self, member: discord.Member, before: discord.VoiceState):
        """
        Handles logic for when a user leaves a temporary voice channel.

        This includes checking if the channel becomes empty and should be deleted,
        or if ownership changes.

        Args:
            member: The `discord.Member` who left the channel.
            before: The `discord.VoiceState` from before the update, containing the channel.
        """
        logging.info(
            f"DEBUG: _handle_channel_leave called for user {member.id}, channel {before.channel.id if before.channel else 'None'}")
        # Ensure the channel the user left is indeed a Discord VoiceChannel object
        # to access its properties safely (e.g., .members, .delete).
        if not isinstance(before.channel, discord.VoiceChannel):
            # Safely get the channel ID for logging if it exists, otherwise use "None"
            channel_id_str = str(
                before.channel.id) if before.channel else "None"
            logging.warning(
                f"Member {member.id} left a non-voice channel {channel_id_str} unexpectedly.")
            return

        # Attempt to retrieve the voice channel from the database.
        # This determines if it's a bot-managed temporary channel.
        owned_channel = await self._voice_channel_service.get_voice_channel(before.channel.id)
        logging.info(
            f"DEBUG: Owned channel DB entry for {before.channel.id}: {owned_channel.channel_id if owned_channel else 'None'}")
        if not owned_channel:
            # If the channel is not in our database, it's not a temporary channel we manage.
            logging.debug(
                f"Ignoring leave event for non-managed channel {before.channel.id}.")
            return

        # Determine if the user leaving is the actual owner of the temporary channel.
        is_owner = is_db_value_equal(
            member.id, owned_channel.owner_id)  # Using db_helpers here
        logging.info(
            f"DEBUG: User {member.id} is_owner: {is_owner} for channel {owned_channel.channel_id} (DB Owner: {owned_channel.owner_id})")

        # Define audit log event type and details based on ownership.
        event_type = AuditLogEventType.USER_LEFT_OWNED_CHANNEL if is_owner else AuditLogEventType.USER_LEFT_TEMP_CHANNEL
        ownership_text = "their owned" if is_owner else "temporary"
        details = (
            f"User {member.display_name} ({member.id}) left {ownership_text} channel "
            f"'{before.channel.name}' ({before.channel.id})."
        )

        # Log the user leaving event.
        await self._audit_log_service.log_event(
            guild_id=member.guild.id,
            event_type=event_type,
            user_id=member.id,
            channel_id=before.channel.id,
            details=details
        )

        # Check if the channel is now empty after the user left.
        # `len(before.channel.members)` accurately reflects members *currently* in the channel.
        logging.info(
            f"DEBUG: Members in channel {before.channel.id}: {len(before.channel.members)}")
        if len(before.channel.members) == 0:
            logging.info(
                f"Temporary channel {before.channel.id} is now empty. Attempting deletion.")
            try:
                # Delete the Discord voice channel.
                await before.channel.delete(reason="Temporary channel empty.")
                # Delete the channel entry from our database.
                await self._voice_channel_service.delete_voice_channel(before.channel.id)
                logging.info(
                    f"Successfully deleted empty temp channel {before.channel.id}.")

                # Log the channel deletion event.
                await self._audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.CHANNEL_DELETED,
                    channel_id=before.channel.id,
                    details=(
                        f"Empty temporary channel '{before.channel.name}' ({before.channel.id}) "
                        f"deleted from Discord and database."
                    )
                )
            except discord.NotFound:
                # If the channel was already deleted from Discord (e.g., manually),
                # we just need to clean up our database entry.
                logging.warning(
                    f"Discord channel {before.channel.id} not found but present in DB. Cleaning up DB entry.")
                await self._voice_channel_service.delete_voice_channel(before.channel.id)
                await self._audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.CHANNEL_DELETED_NOT_FOUND,
                    channel_id=before.channel.id,
                    details=(
                        f"Temporary channel {before.channel.id} was already gone from Discord "
                        f"but its entry was removed from the database."
                    )
                )
            except Exception as e:
                # Catch any other unexpected errors during channel deletion.
                logging.error(
                    f"Error deleting channel {before.channel.id} in guild {member.guild.id}: {e}", exc_info=True)
                await self._audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.CHANNEL_DELETE_ERROR,
                    channel_id=before.channel.id,
                    details=f"An unexpected error occurred while deleting channel {before.channel.id}: {e}"
                )

    async def _handle_channel_creation(self, member: discord.Member, guild_config: Guild):
        """
        Handles the creation of a new temporary voice channel when a user joins
        the designated "join to create" channel.

        Args:
            member: The `discord.Member` who joined the creation channel.
            guild_config: The `Guild` configuration object for the member's guild.
        """
        logging.info(
            f"DEBUG: _handle_channel_creation called for user {member.id}")
        # 1. Check if the user already owns an existing temporary channel.
        existing_channel = await self._voice_channel_service.get_voice_channel_by_owner(member.id)
        logging.info(
            f"DEBUG: Existing channel DB entry for {member.id}: {existing_channel.channel_id if existing_channel else 'None'}")

        # Ensure existing_channel is not None and its channel_id is an integer.
        if existing_channel and isinstance(existing_channel.channel_id, int):
            # If a DB entry exists, try to fetch the actual Discord channel.
            channel = self._bot.get_channel(existing_channel.channel_id)
            logging.info(
                f"DEBUG: Discord channel object for existing channel {existing_channel.channel_id}: {channel.id if channel else 'None'}")

            if channel and isinstance(channel, discord.VoiceChannel):
                # If the Discord channel still exists, move the user to their existing channel.
                logging.info(
                    f"User {member.id} already owns channel {existing_channel.channel_id}. Moving them there.")
                await member.move_to(channel, reason="User already has a channel.")
                await self._audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.USER_MOVED_TO_EXISTING_CHANNEL,
                    user_id=member.id,
                    channel_id=existing_channel.channel_id,
                    details=(
                        f"User {member.display_name} ({member.id}) moved to their existing "
                        f"channel '{channel.name}' ({existing_channel.channel_id})."
                    )
                )
            else:
                # If the Discord channel does not exist but a DB entry does, it's stale.
                # Remove the stale entry from the database.
                logging.warning(
                    f"Stale channel entry {existing_channel.channel_id} found for user {member.id}. Removing.")
                await self._voice_channel_service.delete_voice_channel(existing_channel.channel_id)
                await self._audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.STALE_CHANNEL_CLEANUP,
                    user_id=member.id,
                    channel_id=existing_channel.channel_id,
                    details=(
                        f"Stale channel {existing_channel.channel_id} (owner: {member.display_name} - {member.id}) "
                        f"removed from database as Discord channel was not found."
                    )
                )
            # In either case (moved or cleaned up stale), no new channel needs to be created.
            return

        # 2. Determine the new channel's name and limit based on user settings or guild defaults.
        # UserSettings is Optional, explicitly cast to ensure non-None access or handle None.
        user_settings: Optional[UserSettings] = await self._voice_channel_service.get_user_settings(member.id)
        logging.info(
            f"DEBUG: User settings for {member.id}: {user_settings.custom_channel_name if user_settings else 'None'}")

        # Initialize channel name with user's display name as default.
        channel_name = f"{member.display_name}'s Channel"
        if user_settings and isinstance(user_settings.custom_channel_name, str):
            channel_name = user_settings.custom_channel_name
        logging.info(f"DEBUG: Determined channel name: {channel_name}")

        # Initialize channel limit with 0 (unlimited) as default.
        channel_limit = 0
        if user_settings and isinstance(user_settings.custom_channel_limit, int):
            channel_limit = user_settings.custom_channel_limit
        logging.info(f"DEBUG: Determined channel limit: {channel_limit}")

        # 3. Validate and retrieve the voice channel category.
        # Ensure `voice_category_id` is an integer before attempting to cast.
        if not isinstance(guild_config.voice_category_id, int):
            logging.error(
                f"Guild {member.guild.id} has invalid voice_category_id: {guild_config.voice_category_id}.")
            await self._audit_log_service.log_event(
                guild_id=member.guild.id, event_type=AuditLogEventType.CONFIG_ERROR,
                details=f"Invalid voice category ID configured: {guild_config.voice_category_id}."
            )
            return

        category = self._bot.get_channel(guild_config.voice_category_id)
        logging.info(
            f"DEBUG: Fetched category object: {category.id if category else 'None'}")
        # Ensure the fetched category is indeed a `CategoryChannel` type.
        if not isinstance(category, discord.CategoryChannel):
            logging.error(
                f"Configured category (ID: {guild_config.voice_category_id}) not found or is not a category in guild {member.guild.id}.")
            await self._audit_log_service.log_event(
                guild_id=member.guild.id, event_type=AuditLogEventType.CATEGORY_NOT_FOUND,
                details=f"Configured voice category {guild_config.voice_category_id} not found or invalid for guild {member.guild.id}."
            )
            return

        # 4. Attempt to create the new voice channel.
        try:
            # Define permission overwrites for the new channel.
            # Default role: Can connect (True)
            # Owner: Full management permissions (manage_channels, manage_roles, connect, speak)
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(manage_channels=True, manage_roles=True, connect=True, speak=True),
            }

            logging.info(
                f"DEBUG: Attempting to create Discord voice channel with name '{channel_name}', limit {channel_limit}, category {category.id}")
            # Create the Discord voice channel.
            new_channel = await member.guild.create_voice_channel(
                name=channel_name,
                category=category,
                user_limit=channel_limit,
                overwrites=overwrites,
                reason=f"Temporary channel for {member.display_name}"
            )
            logging.info(f"DEBUG: Discord channel created: {new_channel.id}")

            # Store the new channel's information in the database.
            await self._voice_channel_service.create_voice_channel(new_channel.id, member.id)
            logging.info(
                f"DEBUG: Database entry created for channel {new_channel.id}")

            # Move the user to their newly created channel.
            await member.move_to(new_channel)
            logging.info(
                f"DEBUG: User {member.id} moved to new channel {new_channel.id}")

            logging.info(
                f"Created temporary channel {new_channel.id} for user {member.id} in guild {member.guild.id}.")

            # Log the successful channel creation event.
            await self._audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CHANNEL_CREATED,
                user_id=member.id,
                channel_id=new_channel.id,
                details=(
                    f"New temporary channel '{new_channel.name}' ({new_channel.id}) created "
                    f"for {member.display_name} ({member.id}) with limit: {channel_limit}."
                )
            )
        except Exception as e:
            # Catch and log any other unexpected errors during channel creation (e.g., Discord API errors, permission issues).
            logging.error(
                f"Failed to create temporary channel for user {member.id} in guild {member.guild.id}: {e}", exc_info=True)
            await self._audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CHANNEL_CREATION_FAILED,
                user_id=member.id,
                details=f"Failed to create channel for {member.display_name} ({member.id}): {e}"
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
            audit_log_service=custom_bot.audit_log_service
        )
    )