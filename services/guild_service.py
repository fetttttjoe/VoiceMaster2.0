import logging
from typing import TYPE_CHECKING, List, Optional

from database.models import Guild, VoiceChannel
from interfaces.guild_repository import IGuildRepository
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService

if TYPE_CHECKING:
    from main import VoiceMasterBot


class GuildService(IGuildService):
    def __init__(
        self,
        guild_repository: IGuildRepository,
        voice_channel_service: IVoiceChannelService,
        bot: "VoiceMasterBot",
    ):
        self._guild_repository = guild_repository
        self._voice_channel_service = voice_channel_service
        self._bot = bot

    async def get_guild_config(self, guild_id: int) -> Optional[Guild]:
        return await self._guild_repository.get_guild_config(guild_id)

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        await self._guild_repository.create_or_update_guild(guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        return await self._guild_repository.get_all_voice_channels()

    async def get_voice_channels_by_guild(self, guild_id: int) -> List[VoiceChannel]:
        return await self._guild_repository.get_voice_channels_by_guild(guild_id)

    async def set_cleanup_on_startup(self, guild_id: int, enabled: bool) -> None:
        await self._guild_repository.set_cleanup_on_startup(guild_id, enabled)

    async def cleanup_stale_channels(self, channel_ids: List[int]) -> None:
        for channel_id in channel_ids:
            await self._voice_channel_service.delete_voice_channel(channel_id)
        logging.info(f"Successfully purged {len(channel_ids)} stale channel records from the database.")
