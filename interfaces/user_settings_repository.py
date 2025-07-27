from abc import ABC, abstractmethod
from typing import Optional

from database.models import UserSettings


class IUserSettingsRepository(ABC):
    """
    Abstract interface for user settings data operations.
    """

    @abstractmethod
    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]: ...

    @abstractmethod
    async def update_channel_name(self, user_id: int, name: str) -> None: ...

    @abstractmethod
    async def update_channel_limit(self, user_id: int, limit: int) -> None: ...
