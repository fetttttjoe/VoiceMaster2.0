import logging
import discord
from discord.ext import commands
from typing import cast
from database.models import Guild, AuditLogEventType, UserSettings

# Abstractions
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from interfaces.audit_log_service import IAuditLogService
from main import VoiceMasterBot # Import your custom bot class

class EventsCog(commands.Cog):
    def __init__(
        self,
        bot: VoiceMasterBot,
        guild_service: IGuildService,
        voice_channel_service: IVoiceChannelService,
        audit_log_service: IAuditLogService,
    ):
        self.bot = bot
        self.guild_service = guild_service
        self.voice_channel_service = voice_channel_service
        self.audit_log_service = audit_log_service

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        """Routes voice state updates to appropriate handlers."""
        # Ensure that guild_service is used for getting guild config
        guild_config = await self.guild_service.get_guild_config(member.guild.id)

        if not guild_config or not isinstance(guild_config.creation_channel_id, int):
            return

        # User leaves a channel
        # Ensure that _handle_channel_leave uses the instance attributes
        if before.channel and before.channel.id != guild_config.creation_channel_id:
            await self._handle_channel_leave(member, before)

        # User joins the "create" channel
        # Ensure that _handle_channel_creation uses the instance attributes
        if after.channel and after.channel.id == guild_config.creation_channel_id:
            await self._handle_channel_creation(member, guild_config)

    async def _handle_channel_leave(self, member: discord.Member, before: discord.VoiceState):
        """Handles logic for when a user leaves a temporary voice channel."""
        # Assert that the channel is a voice channel to satisfy Pylance
        if not isinstance(before.channel, discord.VoiceChannel):
            return

        # CORRECT: Use self.voice_channel_service
        owned_channel = await self.voice_channel_service.get_voice_channel(before.channel.id)
        if not owned_channel:
            return

        is_owner = member.id == owned_channel.owner_id
        event_type = AuditLogEventType.USER_LEFT_OWNED_CHANNEL if is_owner else AuditLogEventType.USER_LEFT_TEMP_CHANNEL
        ownership_text = "their owned" if is_owner else "temporary"
        details = f"User {member.display_name} left {ownership_text} channel '{before.channel.name}'."

        # CORRECT: Use self.audit_log_service
        await self.audit_log_service.log_event(
            guild_id=member.guild.id, event_type=event_type, user_id=member.id,
            channel_id=before.channel.id, details=details
        )

        if len(before.channel.members) == 0:
            try:
                await before.channel.delete(reason="Temporary channel empty.")
                # CORRECT: Use self.voice_channel_service
                await self.voice_channel_service.delete_voice_channel(before.channel.id)
                logging.info(f"Deleted empty temp channel {before.channel.id}")
                # CORRECT: Use self.audit_log_service
                await self.audit_log_service.log_event(
                    guild_id=member.guild.id, event_type=AuditLogEventType.CHANNEL_DELETED,
                    channel_id=before.channel.id, details=f"Empty temporary channel '{before.channel.name}' deleted."
                )
            except discord.NotFound:
                # CORRECT: Use self.voice_channel_service
                await self.voice_channel_service.delete_voice_channel(before.channel.id)
                # CORRECT: Use self.audit_log_service
                await self.audit_log_service.log_event(
                    guild_id=member.guild.id, event_type=AuditLogEventType.CHANNEL_DELETED_NOT_FOUND,
                    channel_id=before.channel.id, details=f"Temporary channel {before.channel.id} was already gone but removed from DB."
                )
            except Exception as e:
                logging.error(f"Error deleting channel {before.channel.id}: {e}")
                # CORRECT: Use self.audit_log_service
                await self.audit_log_service.log_event(
                    guild_id=member.guild.id, event_type=AuditLogEventType.CHANNEL_DELETE_ERROR,
                    channel_id=before.channel.id, details=f"Error deleting channel: {e}"
                )

    async def _handle_channel_creation(self, member: discord.Member, guild_config: Guild):
        """Handles the creation of a new temporary voice channel."""
        # CORRECT: Use self.voice_channel_service
        existing_channel = await self.voice_channel_service.get_voice_channel_by_owner(member.id)
        if existing_channel and isinstance(existing_channel.channel_id, int):
            channel = self.bot.get_channel(existing_channel.channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                await member.move_to(channel, reason="User already has a channel.")
                # CORRECT: Use self.audit_log_service
                await self.audit_log_service.log_event(
                    guild_id=member.guild.id, event_type=AuditLogEventType.USER_MOVED_TO_EXISTING_CHANNEL,
                    user_id=member.id, channel_id=existing_channel.channel_id,
                    details=f"User {member.display_name} moved to their existing channel '{channel.name}'."
                )
            else:
                # CORRECT: Use self.voice_channel_service
                await self.voice_channel_service.delete_voice_channel(existing_channel.channel_id)
                # CORRECT: Use self.audit_log_service
                await self.audit_log_service.log_event(
                    guild_id=member.guild.id, event_type=AuditLogEventType.STALE_CHANNEL_CLEANUP,
                    user_id=member.id, channel_id=existing_channel.channel_id,
                    details=f"Stale channel {existing_channel.channel_id} (owner: {member.display_name}) removed from DB."
                )
            return

        # CORRECT: Use self.voice_channel_service
        user_settings: UserSettings | None = await self.voice_channel_service.get_user_settings(member.id)

        channel_name = f"{member.display_name}'s Channel"
        if user_settings and isinstance(user_settings.custom_channel_name, str):
            channel_name = user_settings.custom_channel_name

        channel_limit = 0
        if user_settings and isinstance(user_settings.custom_channel_limit, int):
            channel_limit = user_settings.custom_channel_limit

        assert isinstance(guild_config.voice_category_id, int)
        category = self.bot.get_channel(guild_config.voice_category_id)
        if not isinstance(category, discord.CategoryChannel):
            logging.error(f"Category not found for guild {member.guild.id}")
            # CORRECT: Use self.audit_log_service
            await self.audit_log_service.log_event(
                guild_id=member.guild.id, event_type=AuditLogEventType.CATEGORY_NOT_FOUND,
                details=f"Category {guild_config.voice_category_id} not found for guild."
            )
            return

        try:
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(manage_channels=True, manage_roles=True, connect=True, speak=True),
            }
            new_channel = await member.guild.create_voice_channel(
                name=channel_name, category=category, user_limit=channel_limit,
                overwrites=overwrites, reason=f"Temporary channel for {member.display_name}"
            )
            # CORRECT: Use self.voice_channel_service
            await self.voice_channel_service.create_voice_channel(new_channel.id, member.id)
            await member.move_to(new_channel)
            logging.info(f"Created temp channel {new_channel.id} for {member.id}")
            # CORRECT: Use self.audit_log_service
            await self.audit_log_service.log_event(
                guild_id=member.guild.id, event_type=AuditLogEventType.CHANNEL_CREATED,
                user_id=member.id, channel_id=new_channel.id,
                details=f"New temporary channel '{new_channel.name}' created (Limit: {channel_limit})."
            )
        except Exception as e:
            logging.error(f"Failed to create channel for {member.id}: {e}")
            # CORRECT: Use self.audit_log_service
            await self.audit_log_service.log_event(
                guild_id=member.guild.id, event_type=AuditLogEventType.CHANNEL_CREATION_FAILED,
                user_id=member.id, details=f"Failed to create channel for {member.display_name}: {e}"
            )

async def setup(bot: commands.Bot):
    """The entry point for loading the cog."""
    custom_bot = cast(VoiceMasterBot, bot)
    await bot.add_cog(
        EventsCog(
            bot=custom_bot,
            guild_service=custom_bot.guild_service,
            voice_channel_service=custom_bot.voice_channel_service,
            audit_log_service=custom_bot.audit_log_service
        )
    )