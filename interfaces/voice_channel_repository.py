from abc import ABC, abstractmethod
from typing import Optional
from database.models import VoiceChannel

class IVoiceChannelRepository(ABC):
    """
    Abstract interface for voice channel data operations.
    """
    @abstractmethod
    async def get_by_owner(self, owner_id: int) -> Optional[VoiceChannel]:
        ...

    @abstractmethod
    async def get_by_channel_id(self, channel_id: int) -> Optional[VoiceChannel]:
        ...

    @abstractmethod
    async def create(self, channel_id: int, owner_id: int, guild_id: int) -> None:
        ...

    @abstractmethod
    async def delete(self, channel_id: int) -> None:
        ...

    @abstractmethod
    async def update_owner(self, channel_id: int, new_owner_id: int) -> None:
        ...
