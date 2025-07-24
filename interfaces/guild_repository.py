from abc import ABC, abstractmethod
from typing import Optional, List
from database.models import Guild, VoiceChannel

class IGuildRepository(ABC):
    """
    Abstract interface for guild-related data operations.
    """
    @abstractmethod
    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        ...

    @abstractmethod
    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        ...

    @abstractmethod
    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        ...

    @abstractmethod
    async def get_voice_channels_by_guild(self, guild_id: int) -> List[VoiceChannel]:
        ...
    
    @abstractmethod
    async def update_cleanup_flag(self, guild_id: int, enabled: bool) -> None:
        ...