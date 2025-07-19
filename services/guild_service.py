from sqlalchemy.ext.asyncio import AsyncSession
from database import crud, models

class GuildService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_guild_config(self, guild_id: int):
        return await crud.get_guild(self.db_session, guild_id)

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int):
        await crud.create_or_update_guild(self.db_session, guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self):
        return await crud.get_all_voice_channels(self.db_session)