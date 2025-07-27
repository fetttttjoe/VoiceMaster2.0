from typing import Optional
from interfaces.voice_channel_service import IVoiceChannelService
from sqlalchemy.ext.asyncio import AsyncSession
from database import crud
from database.models import VoiceChannel, UserSettings # Used for type hinting

class VoiceChannelService(IVoiceChannelService):
    """
    Implements the business logic for managing temporary voice channels and
    user-specific channel settings.

    This service orchestrates operations related to voice channels, such as creation,
    deletion, and ownership transfers, and manages user preferences for these channels.
    It relies on data access abstractions (`IVoiceChannelRepository`, `IUserSettingsRepository`)
    for data persistence.
    """
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_voice_channel_by_owner(self, owner_id: int) -> Optional[VoiceChannel]:
        """
        Retrieves a temporary voice channel owned by a specific user.

        Args:
            owner_id: The ID of the user (potential owner).

        Returns:
            The `VoiceChannel` object if found, otherwise `None`.
        """
        return await crud.get_voice_channel_by_owner(self._session, owner_id)

    async def get_voice_channel(self, channel_id: int) -> Optional[VoiceChannel]:
        """
        Retrieves a temporary voice channel by its Discord channel ID.

        Args:
            channel_id: The Discord ID of the voice channel.

        Returns:
            The `VoiceChannel` object if found, otherwise `None`.
        """
        return await crud.get_voice_channel(self._session, channel_id)

    async def delete_voice_channel(self, channel_id: int) -> None:
        """
        Deletes a temporary voice channel entry from the database.

        This operation typically follows the successful deletion of the
        corresponding Discord voice channel.

        Args:
            channel_id: The Discord ID of the channel to delete from the database.
        """
        await crud.delete_voice_channel(self._session, channel_id)

    async def create_voice_channel(self, channel_id: int, owner_id: int, guild_id: int) -> None:
        """
        Creates a new temporary voice channel entry in the database.

        This method is called after a new Discord voice channel has been
        successfully created by the bot for a user.

        Args:
            channel_id: The Discord ID of the newly created channel.
            owner_id: The ID of the user who owns this new channel.
        """
        await crud.create_voice_channel(self._session, channel_id, owner_id, guild_id)

    async def update_voice_channel_owner(self, channel_id: int, new_owner_id: int) -> None:
        """
        Updates the owner of an existing temporary voice channel in the database.

        This is used, for example, when a user "claims" an abandoned channel.

        Args:
            channel_id: The Discord ID of the channel to update.
            new_owner_id: The ID of the new owner for the channel.
        """
        await crud.update_voice_channel_owner(self._session, channel_id, new_owner_id)

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """
        Retrieves the custom settings for a specific user.

        Args:
            user_id: The ID of the user.

        Returns:
            The `UserSettings` object if found, otherwise `None`.
        """
        return await crud.get_user_settings(self._session, user_id)

    async def update_user_channel_name(self, user_id: int, name: str) -> None:
        """
        Updates a user's preferred custom channel name.

        Args:
            user_id: The ID of the user.
            name: The new custom channel name.
        """
        await crud.update_user_channel_name(self._session, user_id, name)

    async def update_user_channel_limit(self, user_id: int, limit: int) -> None:
        await crud.update_user_channel_limit(self._session, user_id, limit)