# VoiceMaster2.0/cogs/events.py
import logging
import discord
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import db
from services.guild_service import GuildService
from services.voice_channel_service import VoiceChannelService
from services.audit_log_service import AuditLogService
from database.models import Guild, AuditLogEventType # New import

class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        async with db.get_session() as session:
            guild_service = GuildService(session)
            vc_service = VoiceChannelService(session)
            audit_log_service = AuditLogService(session)

            guild_config = await guild_service.get_guild_config(member.guild.id)
            if not guild_config:
                return

            assert isinstance(guild_config.creation_channel_id, int)

            # User leaves a temporary channel, check if it's empty and delete it
            if before.channel and before.channel.id != guild_config.creation_channel_id:
                owned_channel = await vc_service.get_voice_channel(before.channel.id)
                if owned_channel and len(before.channel.members) == 0:
                    try:
                        await before.channel.delete(reason="Temporary channel empty.")
                        await vc_service.delete_voice_channel(before.channel.id)
                        logging.info(f"Deleted empty temp channel {before.channel.id}")
                        await audit_log_service.log_event(
                            guild_id=member.guild.id,
                            event_type=AuditLogEventType.CHANNEL_DELETED, # Enum used
                            channel_id=before.channel.id,
                            details=f"Empty temporary channel '{before.channel.name}' deleted."
                        )
                    except discord.NotFound:
                        await vc_service.delete_voice_channel(before.channel.id)
                        await audit_log_service.log_event(
                            guild_id=member.guild.id,
                            event_type=AuditLogEventType.CHANNEL_DELETED_NOT_FOUND, # Enum used
                            channel_id=before.channel.id,
                            details=f"Temporary channel {before.channel.id} was already gone but removed from DB."
                        )
                    except Exception as e:
                        logging.error(f"Error deleting channel {before.channel.id}: {e}")
                        await audit_log_service.log_event(
                            guild_id=member.guild.id,
                            event_type=AuditLogEventType.CHANNEL_DELETE_ERROR, # Enum used
                            channel_id=before.channel.id,
                            details=f"Error deleting channel: {e}"
                        )
                # Log user leaving a temporary channel
                if owned_channel and member.id == owned_channel.owner_id:
                    await audit_log_service.log_event(
                        guild_id=member.guild.id,
                        event_type=AuditLogEventType.USER_LEFT_OWNED_CHANNEL, # Enum used
                        user_id=member.id,
                        channel_id=before.channel.id,
                        details=f"User {member.display_name} left their owned channel '{before.channel.name}'."
                    )
                elif owned_channel:
                     await audit_log_service.log_event(
                        guild_id=member.guild.id,
                        event_type=AuditLogEventType.USER_LEFT_TEMP_CHANNEL, # Enum used
                        user_id=member.id,
                        channel_id=before.channel.id,
                        details=f"User {member.display_name} left temporary channel '{before.channel.name}'."
                    )


            # User joins the "create" channel
            if after.channel and after.channel.id == guild_config.creation_channel_id:
                await self.handle_create_channel(session, member, guild_config, audit_log_service)

    async def handle_create_channel(self, session: AsyncSession, member: discord.Member, guild_config: Guild, audit_log_service: AuditLogService):
        vc_service = VoiceChannelService(session)
        # Check if user already owns a channel
        existing_channel = await vc_service.get_voice_channel_by_owner(member.id)
        if existing_channel:
            assert isinstance(existing_channel.channel_id, int)
            channel = self.bot.get_channel(existing_channel.channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                await member.move_to(channel, reason="User already has a channel.")
                await audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.USER_MOVED_TO_EXISTING_CHANNEL, # Enum used
                    user_id=member.id,
                    channel_id=existing_channel.channel_id,
                    details=f"User {member.display_name} moved to their existing channel '{channel.name}'."
                )
            else:
                await vc_service.delete_voice_channel(existing_channel.channel_id)
                await audit_log_service.log_event(
                    guild_id=member.guild.id,
                    event_type=AuditLogEventType.STALE_CHANNEL_CLEANUP, # Enum used
                    user_id=member.id,
                    channel_id=existing_channel.channel_id,
                    details=f"Stale channel {existing_channel.channel_id} (owner: {member.display_name}) removed from DB."
                )
            return

        # Get channel settings
        user_settings = await vc_service.get_user_settings(member.id)
        
        channel_name = f"{member.display_name}'s Channel"
        if user_settings and isinstance(user_settings.custom_channel_name, str):
            channel_name = user_settings.custom_channel_name

        channel_limit = 0
        if user_settings and isinstance(user_settings.custom_channel_limit, int):
            channel_limit = user_settings.custom_channel_limit

        # Create the new channel
        if guild_config.voice_category_id is None:
            logging.error(f"Voice category not configured for guild {member.guild.id}")
            await audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CONFIG_ERROR, # Enum used
                details=f"Voice category not configured for guild {member.guild.id} during channel creation attempt by {member.display_name}."
            )
            return
        
        assert isinstance(guild_config.voice_category_id, int)
        category = self.bot.get_channel(guild_config.voice_category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            logging.error(f"Category {guild_config.voice_category_id} not found for guild {member.guild.id}")
            await audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CATEGORY_NOT_FOUND, # Enum used
                details=f"Category {guild_config.voice_category_id} not found for guild {member.guild.id} during channel creation attempt by {member.display_name}."
            )
            return

        try:
            overwrites = {
                member.guild.default_role: discord.PermissionOverwrite(connect=True),
                member: discord.PermissionOverwrite(manage_channels=True, manage_roles=True, connect=True, speak=True),
            }
            new_channel = await member.guild.create_voice_channel(
                name=channel_name,
                category=category,
                user_limit=channel_limit,
                overwrites=overwrites,
                reason=f"Temporary channel for {member.display_name}"
            )
            await vc_service.create_voice_channel(new_channel.id, member.id)
            await member.move_to(new_channel)
            logging.info(f"Created temp channel {new_channel.id} for {member.id}")
            await audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CHANNEL_CREATED, # Enum used
                user_id=member.id,
                channel_id=new_channel.id,
                details=f"New temporary channel '{new_channel.name}' created by {member.display_name} (Limit: {channel_limit})."
            )
        except Exception as e:
            logging.error(f"Failed to create channel for {member.id}: {e}")
            await audit_log_service.log_event(
                guild_id=member.guild.id,
                event_type=AuditLogEventType.CHANNEL_CREATION_FAILED, # Enum used
                user_id=member.id,
                details=f"Failed to create channel for {member.display_name}: {e}"
            )

async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))