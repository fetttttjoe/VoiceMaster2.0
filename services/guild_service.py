from typing import Optional, List
from interfaces.guild_service import IGuildService
from interfaces.guild_repository import IGuildRepository
from database.models import Guild, VoiceChannel

class GuildService(IGuildService):
    """
    Implements the business logic for guild-related operations.
    Depends on an abstraction for the guild repository.
    """
    def __init__(self, guild_repository: IGuildRepository):
        self._guild_repository = guild_repository

    async def get_guild_config(self, guild_id: int) -> Optional[Guild]:
        return await self._guild_repository.get_guild(guild_id)

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        await self._guild_repository.create_or_update_guild(guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        return await self._guild_repository.get_all_voice_channels()
