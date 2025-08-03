from typing import Optional

from database.models import UserSettings, VoiceChannel
from interfaces.voice_channel_repository import IVoiceChannelRepository
from interfaces.voice_channel_service import IVoiceChannelService


class VoiceChannelService(IVoiceChannelService):
    def __init__(self, voice_channel_repository: IVoiceChannelRepository):
        self._voice_channel_repository = voice_channel_repository

    async def get_voice_channel_by_owner(self, owner_id: int) -> Optional[VoiceChannel]:
        return await self._voice_channel_repository.get_voice_channel_by_owner(owner_id)

    async def get_voice_channel(self, channel_id: int) -> Optional[VoiceChannel]:
        return await self._voice_channel_repository.get_voice_channel(channel_id)

    async def delete_voice_channel(self, channel_id: int) -> None:
        await self._voice_channel_repository.delete_voice_channel(channel_id)

    async def create_voice_channel(self, channel_id: int, owner_id: int, guild_id: int) -> None:
        await self._voice_channel_repository.create_voice_channel(channel_id, owner_id, guild_id)

    async def update_voice_channel_owner(self, channel_id: int, new_owner_id: int) -> None:
        await self._voice_channel_repository.update_voice_channel_owner(channel_id, new_owner_id)

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        return await self._voice_channel_repository.get_user_settings(user_id)

    async def update_user_channel_name(self, user_id: int, name: str) -> None:
        await self._voice_channel_repository.update_user_channel_name(user_id, name)

    async def update_user_channel_limit(self, user_id: int, limit: int) -> None:
        await self._voice_channel_repository.update_user_channel_limit(user_id, limit)
