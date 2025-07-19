from sqlalchemy.ext.asyncio import AsyncSession
from database import crud, models
import discord

class VoiceChannelService:
    def __init__(self, db_session: AsyncSession):
        self.db_session = db_session

    async def get_voice_channel_by_owner(self, owner_id: int):
        return await crud.get_voice_channel_by_owner(self.db_session, owner_id)

    async def get_voice_channel(self, channel_id: int):
        return await crud.get_voice_channel(self.db_session, channel_id)

    async def delete_voice_channel(self, channel_id: int):
        await crud.delete_voice_channel(self.db_session, channel_id)

    async def create_voice_channel(self, channel_id: int, owner_id: int):
        await crud.create_voice_channel(self.db_session, channel_id, owner_id)

    async def update_voice_channel_owner(self, channel_id: int, new_owner_id: int):
        await crud.update_voice_channel_owner(self.db_session, channel_id, new_owner_id)

    async def get_user_settings(self, user_id: int):
        return await crud.get_user_settings(self.db_session, user_id)

    async def update_user_channel_name(self, user_id: int, name: str):
        await crud.update_user_channel_name(self.db_session, user_id, name)

    async def update_user_channel_limit(self, user_id: int, limit: int):
        await crud.update_user_channel_limit(self.db_session, user_id, limit)