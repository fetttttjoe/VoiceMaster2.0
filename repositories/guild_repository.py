from typing import List, Optional

from sqlalchemy import update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.models import Guild, VoiceChannel
from interfaces.guild_repository import IGuildRepository


class GuildRepository(IGuildRepository):
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_guild_config(self, guild_id: int) -> Optional[Guild]:
        result = await self._session.execute(select(Guild).where(Guild.id == guild_id))
        return result.scalar_one_or_none()

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        guild = await self.get_guild_config(guild_id)
        if guild:
            stmt = update(Guild).where(Guild.id == guild_id).values(owner_id=owner_id, voice_category_id=category_id, creation_channel_id=channel_id)
            await self._session.execute(stmt)
        else:
            self._session.add(Guild(id=guild_id, owner_id=owner_id, voice_category_id=category_id, creation_channel_id=channel_id))
        await self._session.commit()

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        result = await self._session.execute(select(VoiceChannel))
        return list(result.scalars().all())

    async def get_voice_channels_by_guild(self, guild_id: int) -> List[VoiceChannel]:
        result = await self._session.execute(select(VoiceChannel).where(VoiceChannel.guild_id == guild_id))
        return list(result.scalars().all())

    async def set_cleanup_on_startup(self, guild_id: int, enabled: bool) -> None:
        stmt = update(Guild).where(Guild.id == guild_id).values(cleanup_on_startup=enabled)
        await self._session.execute(stmt)
        await self._session.commit()
