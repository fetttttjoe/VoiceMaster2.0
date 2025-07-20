from typing import Optional
from interfaces.voice_channel_service import IVoiceChannelService
from interfaces.voice_channel_repository import IVoiceChannelRepository
from interfaces.user_settings_repository import IUserSettingsRepository
from database.models import VoiceChannel, UserSettings

class VoiceChannelService(IVoiceChannelService):
    """
    Implements the business logic for voice channel and user settings operations.
    Depends on abstractions for the voice channel and user settings repositories.
    """
    def __init__(self, vc_repository: IVoiceChannelRepository, user_settings_repository: IUserSettingsRepository):
        self._vc_repository = vc_repository
        self._user_settings_repository = user_settings_repository

    async def get_voice_channel_by_owner(self, owner_id: int) -> Optional[VoiceChannel]:
        return await self._vc_repository.get_by_owner(owner_id)

    async def get_voice_channel(self, channel_id: int) -> Optional[VoiceChannel]:
        return await self._vc_repository.get_by_channel_id(channel_id)

    async def delete_voice_channel(self, channel_id: int) -> None:
        await self._vc_repository.delete(channel_id)

    async def create_voice_channel(self, channel_id: int, owner_id: int) -> None:
        await self._vc_repository.create(channel_id, owner_id)

    async def update_voice_channel_owner(self, channel_id: int, new_owner_id: int) -> None:
        await self._vc_repository.update_owner(channel_id, new_owner_id)

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        return await self._user_settings_repository.get_user_settings(user_id)

    async def update_user_channel_name(self, user_id: int, name: str) -> None:
        await self._user_settings_repository.update_channel_name(user_id, name)

    async def update_user_channel_limit(self, user_id: int, limit: int) -> None:
        await self._user_settings_repository.update_channel_limit(user_id, limit)
