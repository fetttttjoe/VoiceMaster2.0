from abc import ABC, abstractmethod
from typing import Optional

from database.models import UserSettings, VoiceChannel


class IVoiceChannelService(ABC):
    """
    Abstract interface for voice channel business logic.
    """

    @abstractmethod
    async def get_voice_channel_by_owner(self, owner_id: int) -> Optional[VoiceChannel]: ...

    @abstractmethod
    async def get_voice_channel(self, channel_id: int) -> Optional[VoiceChannel]: ...

    @abstractmethod
    async def delete_voice_channel(self, channel_id: int) -> None: ...

    @abstractmethod
    async def create_voice_channel(self, channel_id: int, owner_id: int, guild_id) -> None: ...

    @abstractmethod
    async def update_voice_channel_owner(self, channel_id: int, new_owner_id: int) -> None: ...

    @abstractmethod
    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]: ...

    @abstractmethod
    async def update_user_channel_name(self, user_id: int, name: str) -> None: ...

    @abstractmethod
    async def update_user_channel_limit(self, user_id: int, limit: int) -> None: ...
