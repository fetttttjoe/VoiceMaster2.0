from typing import Optional

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UserSettings, VoiceChannel
from interfaces.voice_channel_repository import IVoiceChannelRepository


class VoiceChannelRepository(IVoiceChannelRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_voice_channel_by_owner(self, owner_id: int) -> Optional[VoiceChannel]:
        result = await self._session.execute(select(VoiceChannel).where(VoiceChannel.owner_id == owner_id))
        return result.scalar_one_or_none()

    async def get_voice_channel(self, channel_id: int) -> Optional[VoiceChannel]:
        result = await self._session.execute(select(VoiceChannel).where(VoiceChannel.channel_id == channel_id))
        return result.scalar_one_or_none()

    async def delete_voice_channel(self, channel_id: int) -> None:
        stmt = delete(VoiceChannel).where(VoiceChannel.channel_id == channel_id)
        await self._session.execute(stmt)
        await self._session.commit()

    async def create_voice_channel(self, channel_id: int, owner_id: int, guild_id: int) -> None:
        self._session.add(VoiceChannel(channel_id=channel_id, owner_id=owner_id, guild_id=guild_id))
        await self._session.commit()

    async def update_voice_channel_owner(self, channel_id: int, new_owner_id: int) -> None:
        stmt = update(VoiceChannel).where(VoiceChannel.channel_id == channel_id).values(owner_id=new_owner_id)
        await self._session.execute(stmt)
        await self._session.commit()

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        result = await self._session.execute(select(UserSettings).where(UserSettings.user_id == user_id))
        return result.scalar_one_or_none()

    async def update_user_channel_name(self, user_id: int, name: str) -> None:
        settings = await self.get_user_settings(user_id)
        if settings:
            stmt = update(UserSettings).where(UserSettings.user_id == user_id).values(custom_channel_name=name)
            await self._session.execute(stmt)
        else:
            self._session.add(UserSettings(user_id=user_id, custom_channel_name=name))
        await self._session.commit()

    async def update_user_channel_limit(self, user_id: int, limit: int) -> None:
        settings = await self.get_user_settings(user_id)
        if settings:
            stmt = update(UserSettings).where(UserSettings.user_id == user_id).values(custom_channel_limit=limit)
            await self._session.execute(stmt)
        else:
            self._session.add(UserSettings(user_id=user_id, custom_channel_limit=limit))
        await self._session.commit()
