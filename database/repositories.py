from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from database import crud
from database.models import Guild, VoiceChannel, UserSettings, AuditLogEntry, AuditLogEventType

# Abstractions
from interfaces.guild_repository import IGuildRepository
from interfaces.voice_channel_repository import IVoiceChannelRepository
from interfaces.user_settings_repository import IUserSettingsRepository
from interfaces.audit_log_repository import IAuditLogRepository


class GuildRepository(IGuildRepository):
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        return await crud.get_guild(self.db, guild_id)

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        await crud.create_or_update_guild(self.db, guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        # Explicitly convert the Sequence to a List
        return list(await crud.get_all_voice_channels(self.db))


class VoiceChannelRepository(IVoiceChannelRepository):
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_by_owner(self, owner_id: int) -> Optional[VoiceChannel]:
        return await crud.get_voice_channel_by_owner(self.db, owner_id)

    async def get_by_channel_id(self, channel_id: int) -> Optional[VoiceChannel]:
        return await crud.get_voice_channel(self.db, channel_id)

    async def create(self, channel_id: int, owner_id: int) -> None:
        await crud.create_voice_channel(self.db, channel_id, owner_id)

    async def delete(self, channel_id: int) -> None:
        await crud.delete_voice_channel(self.db, channel_id)

    async def update_owner(self, channel_id: int, new_owner_id: int) -> None:
        await crud.update_voice_channel_owner(self.db, channel_id, new_owner_id)


class UserSettingsRepository(IUserSettingsRepository):
    def __init__(self, session: AsyncSession):
        self.db = session

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        return await crud.get_user_settings(self.db, user_id)

    async def update_channel_name(self, user_id: int, name: str) -> None:
        await crud.update_user_channel_name(self.db, user_id, name)

    async def update_channel_limit(self, user_id: int, limit: int) -> None:
        await crud.update_user_channel_limit(self.db, user_id, limit)


class AuditLogRepository(IAuditLogRepository):
    def __init__(self, session: AsyncSession):
        self.db = session

    async def create_entry(
        self,
        guild_id: int,
        event_type: AuditLogEventType,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        await crud.create_audit_log_entry(
            self.db, guild_id, event_type, user_id, channel_id, details
        )

    async def get_latest_entries(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]:
        # Explicitly convert the Sequence to a List
        return list(await crud.get_latest_audit_log_entries(self.db, guild_id, limit))
