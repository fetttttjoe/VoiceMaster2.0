import logging
from typing import TYPE_CHECKING, List, Optional, cast

from sqlalchemy.ext.asyncio import AsyncSession

from database import crud
from database.models import Guild, VoiceChannel
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService

if TYPE_CHECKING:
    from main import VoiceMasterBot


class GuildService(IGuildService):
    """
    Implements the business logic for guild-related operations.
    """

    def __init__(self, session: AsyncSession, voice_channel_service: IVoiceChannelService, bot: "VoiceMasterBot"):
        self._session = session
        self._voice_channel_service = voice_channel_service
        self._bot = bot

    async def get_guild_config(self, guild_id: int) -> Optional[Guild]:
        return cast(Optional[Guild], await crud.get_guild(self._session, guild_id))

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
        await crud.create_or_update_guild(self._session, guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        """
        Retrieves a list of all active temporary voice channels managed by the bot across all guilds.

        This is primarily used for administrative purposes, such as listing all currently
        active dynamic channels.

        Returns:
            A list of `VoiceChannel` objects.
        """
        return cast(List[VoiceChannel], await crud.get_all_voice_channels(self._session))

    async def get_voice_channels_by_guild(self, guild_id: int) -> List[VoiceChannel]:
        return cast(List[VoiceChannel], await crud.get_voice_channels_by_guild(self._session, guild_id))

    async def set_cleanup_on_startup(self, guild_id: int, enabled: bool) -> None:
        """
        Sets the 'cleanup_on_startup' flag for a guild.
        """
        await crud.update_guild_cleanup_flag(self._session, guild_id, enabled)

    async def cleanup_stale_channels(self, channel_ids: List[int]) -> None:
        """
        Deletes a list of voice channels from the database.

        This is called after the Discord channels have already been deleted.
        """
        for channel_id in channel_ids:
            await self._voice_channel_service.delete_voice_channel(channel_id)
        logging.info(f"Successfully purged {len(channel_ids)} stale channel records from the database.")
