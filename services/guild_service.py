import logging
from typing import Optional, List, TYPE_CHECKING
import discord

from interfaces.guild_service import IGuildService
from interfaces.guild_repository import IGuildRepository
from interfaces.voice_channel_service import IVoiceChannelService
from database.models import Guild, VoiceChannel

if TYPE_CHECKING:
    from main import VoiceMasterBot

class GuildService(IGuildService):
    """
    Implements the business logic for guild-related operations.
    """
    def __init__(
        self,
        guild_repository: IGuildRepository,
        voice_channel_service: IVoiceChannelService,
        bot: 'VoiceMasterBot'
    ):
        self._guild_repository = guild_repository
        self._voice_channel_service = voice_channel_service
        self._bot = bot

    async def get_guild_config(self, guild_id: int) -> Optional[Guild]:
        return await self._guild_repository.get_guild(guild_id)

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        """
        Creates a new guild configuration or updates an existing one.

        This method is typically called during the bot's initial setup or whenever
        core guild settings (like the creation channel or voice category) are changed.

        Args:
            guild_id: The unique ID of the guild.
            owner_id: The ID of the guild owner.
            category_id: The ID of the voice category designated for temporary channels.
            channel_id: The ID of the "join to create" voice channel.
        """
        await self._guild_repository.create_or_update_guild(guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        """
        Retrieves a list of all active temporary voice channels managed by the bot across all guilds.

        This is primarily used for administrative purposes, such as listing all currently
        active dynamic channels.

        Returns:
            A list of `VoiceChannel` objects.
        """
        return await self._guild_repository.get_all_voice_channels()

    async def get_voice_channels_by_guild(self, guild_id: int) -> List[VoiceChannel]:
        return await self._guild_repository.get_voice_channels_by_guild(guild_id)

    async def set_cleanup_on_startup(self, guild_id: int, enabled: bool) -> None:
        """
        Sets the 'cleanup_on_startup' flag for a guild.
        """
        await self._guild_repository.update_cleanup_flag(guild_id, enabled)

    async def cleanup_guild_channels(self, guild_id: int) -> None:
        """
        Cleans up the managed voice channel category for a specific guild,
        if the feature is enabled for that guild.
        """
        guild_config = await self.get_guild_config(guild_id)
        if not guild_config or not guild_config.cleanup_on_startup:
            return
        
        if not guild_config.voice_category_id or not guild_config.creation_channel_id:
            return

        category = self._bot.get_channel(guild_config.voice_category_id)
        if not isinstance(category, discord.CategoryChannel):
            return

        logging.info(f"Running category purge for '{category.name}' in guild '{category.guild.name}'...")
        purged_count = 0
        for channel in category.voice_channels:
            if channel.id == guild_config.creation_channel_id:
                continue

            if len(channel.members) == 0:
                logging.info(f"PURGING: Empty channel '{channel.name}' ({channel.id}) found in managed category.")
                try:
                    await channel.delete(reason="Bot startup cleanup: Purging empty temporary channel.")
                    await self._voice_channel_service.delete_voice_channel(channel.id)
                    purged_count += 1
                except discord.HTTPException as e:
                    logging.error(f"Failed to purge channel {channel.id}: {e}")

        if purged_count > 0:
            logging.info(f"Category purge complete for '{category.name}'. Removed {purged_count} empty channels.")