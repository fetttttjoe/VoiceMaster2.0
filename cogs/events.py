import logging
import discord
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_session
from database import crud
from database.models import Guild, UserSettings, VoiceChannel

class EventsCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        async with get_session() as session:
            guild_config = await crud.get_guild(session, member.guild.id)
            if not guild_config:
                return
            
            assert isinstance(guild_config.creation_channel_id, int)

            # User leaves a temporary channel, check if it's empty and delete it
            if before.channel and before.channel.id != guild_config.creation_channel_id:
                owned_channel = await crud.get_voice_channel(session, before.channel.id)
                if owned_channel and len(before.channel.members) == 0:
                    try:
                        await before.channel.delete(reason="Temporary channel empty.")
                        await crud.delete_voice_channel(session, before.channel.id)
                        logging.info(f"Deleted empty temp channel {before.channel.id}")
                    except discord.NotFound:
                        await crud.delete_voice_channel(session, before.channel.id)
                    except Exception as e:
                        logging.error(f"Error deleting channel {before.channel.id}: {e}")

            # User joins the "create" channel
            if after.channel and after.channel.id == guild_config.creation_channel_id:
                await self.handle_create_channel(session, member, guild_config)

    async def handle_create_channel(self, session: AsyncSession, member: discord.Member, guild_config: Guild):
        # Check if user already owns a channel
        existing_channel = await crud.get_voice_channel_by_owner(session, member.id)
        if existing_channel:
            # Add assert to help Pylance understand the type
            assert isinstance(existing_channel.channel_id, int)
            channel = self.bot.get_channel(existing_channel.channel_id)
            if channel and isinstance(channel, discord.VoiceChannel):
                await member.move_to(channel, reason="User already has a channel.")
            else:
                await crud.delete_voice_channel(session, existing_channel.channel_id)
            return

        # Get channel settings
        user_settings = await crud.get_user_settings(session, member.id)
        
        channel_name = f"{member.display_name}'s Channel"
        if user_settings and isinstance(user_settings.custom_channel_name, str):
            channel_name = user_settings.custom_channel_name

        channel_limit = 0
        if user_settings and isinstance(user_settings.custom_channel_limit, int):
            channel_limit = user_settings.custom_channel_limit

        # Create the new channel
        if guild_config.voice_category_id is None:
            logging.error(f"Voice category not configured for guild {member.guild.id}")
            return
        
        # Add assert to help Pylance understand the type
        assert isinstance(guild_config.voice_category_id, int)
        category = self.bot.get_channel(guild_config.voice_category_id)
        if not category or not isinstance(category, discord.CategoryChannel):
            logging.error(f"Category {guild_config.voice_category_id} not found for guild {member.guild.id}")
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
            await crud.create_voice_channel(session, new_channel.id, member.id)
            await member.move_to(new_channel)
            logging.info(f"Created temp channel {new_channel.id} for {member.id}")
        except Exception as e:
            logging.error(f"Failed to create channel for {member.id}: {e}")


async def setup(bot: commands.Bot):
    await bot.add_cog(EventsCog(bot))
