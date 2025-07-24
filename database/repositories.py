from typing import List, Optional, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from . import crud
from interfaces.guild_repository import IGuildRepository
from interfaces.voice_channel_repository import IVoiceChannelRepository
from interfaces.user_settings_repository import IUserSettingsRepository
from interfaces.audit_log_repository import IAuditLogRepository

# Implementations
from .models import AuditLogEntry, AuditLogEventType, Guild, UserSettings, VoiceChannel

class GuildRepository(IGuildRepository):
    """
    Implements the IGuildRepository interface, providing concrete database
    operations for Guild-related data using SQLAlchemy's CRUD functions.
    """
    def __init__(self, session: AsyncSession):
        """
        Initializes the GuildRepository with an asynchronous database session.

        Args:
            session: The SQLAlchemy asynchronous session.
        """
        self._db = session

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """
        Retrieves a Guild configuration.

        Args:
            guild_id: The ID of the guild.
        Returns:
            The Guild object if found, otherwise None.
        """
        return await crud.get_guild(self._db, guild_id)

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        """
        Creates or updates a Guild configuration.

        Args:
            guild_id: The ID of the guild.
            owner_id: The ID of the guild owner.
            category_id: The ID of the voice category.
            channel_id: The ID of the creation channel.
        """
        await crud.create_or_update_guild(self._db, guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        """
        Retrieves all active temporary voice channels.

        Returns:
            A list of VoiceChannel objects.
        """
        # Explicitly convert the SQLAlchemy `Sequence` result to a `list`
        # for clearer type hinting and direct list operations.
        return list(await crud.get_all_voice_channels(self._db))
      
    async def get_voice_channels_by_guild(self, guild_id: int) -> List[VoiceChannel]:
      """
      Gets all active temporary voice channels for a specific guild.
      """
    
      # Explicitly convert the SQLAlchemy `Sequence` result to a `list`
      # for clearer type hinting and direct list operations.
     
      return list(await crud.get_voice_channels_by_guild(self._db, guild_id))

    async def update_cleanup_flag(self, guild_id: int, enabled: bool) -> None:
        await crud.update_guild_cleanup_flag(self._db, guild_id, enabled)
class VoiceChannelRepository(IVoiceChannelRepository):
    """
    Implements the IVoiceChannelRepository interface, providing concrete
    database operations for temporary voice channel data.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the VoiceChannelRepository with an asynchronous database session.

        Args:
            session: The SQLAlchemy asynchronous session.
        """
        self._db = session

    async def get_by_owner(self, owner_id: int) -> Optional[VoiceChannel]:
        """
        Retrieves a voice channel by its owner's ID.

        Args:
            owner_id: The ID of the channel owner.
        Returns:
            The VoiceChannel object if found, otherwise None.
        """
        return await crud.get_voice_channel_by_owner(self._db, owner_id)

    async def get_by_channel_id(self, channel_id: int) -> Optional[VoiceChannel]:
        """
        Retrieves a voice channel by its channel ID.

        Args:
            channel_id: The ID of the voice channel.
        Returns:
            The VoiceChannel object if found, otherwise None.
        """
        return await crud.get_voice_channel(self._db, channel_id)

    async def create(self, channel_id: int, owner_id: int, guild_id: int) -> None:
        """
        Creates a new voice channel entry.

        Args:
            channel_id: The ID of the new voice channel.
            owner_id: The ID of the channel's owner.
        """
        await crud.create_voice_channel(self._db, channel_id, owner_id, guild_id=guild_id)

    async def delete(self, channel_id: int) -> None:
        """
        Deletes a voice channel entry.

        Args:
            channel_id: The ID of the voice channel to delete.
        """
        await crud.delete_voice_channel(self._db, channel_id)

    async def update_owner(self, channel_id: int, new_owner_id: int) -> None:
        """
        Updates the owner of a voice channel.

        Args:
            channel_id: The ID of the voice channel.
            new_owner_id: The ID of the new owner.
        """
        await crud.update_voice_channel_owner(self._db, channel_id, new_owner_id)


class UserSettingsRepository(IUserSettingsRepository):
    """
    Implements the IUserSettingsRepository interface, providing concrete
    database operations for user-specific settings.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the UserSettingsRepository with an asynchronous database session.

        Args:
            session: The SQLAlchemy asynchronous session.
        """
        self._db = session

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """
        Retrieves settings for a specific user.

        Args:
            user_id: The ID of the user.
        Returns:
            The UserSettings object if found, otherwise None.
        """
        return await crud.get_user_settings(self._db, user_id)

    async def update_channel_name(self, user_id: int, name: str) -> None:
        """
        Updates a user's custom channel name.

        Args:
            user_id: The ID of the user.
            name: The new custom channel name.
        """
        await crud.update_user_channel_name(self._db, user_id, name)

    async def update_channel_limit(self, user_id: int, limit: int) -> None:
        """
        Updates a user's custom channel user limit.

        Args:
            user_id: The ID of the user.
            limit: The new user limit for the channel.
        """
        await crud.update_user_channel_limit(self._db, user_id, limit)


class AuditLogRepository(IAuditLogRepository):
    """
    Implements the IAuditLogRepository interface, providing concrete
    database operations for audit log entries.
    """

    def __init__(self, session: AsyncSession):
        """
        Initializes the AuditLogRepository with an asynchronous database session.

        Args:
            session: The SQLAlchemy asynchronous session.
        """
        self._db = session

    async def create_entry(
        self,
        guild_id: int,
        event_type: AuditLogEventType,
        user_id: Optional[int] = None,
        channel_id: Optional[int] = None,
        details: Optional[str] = None,
    ) -> None:
        """
        Creates a new audit log entry.

        Args:
            guild_id: The ID of the guild where the event occurred.
            event_type: The type of event.
            user_id: The ID of the user associated with the event.
            channel_id: The ID of the channel associated with the event.
            details: A description of the event.
        """
        await crud.create_audit_log_entry(self._db, guild_id, event_type, user_id, channel_id, details)

    async def get_latest_entries(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]:
        """
        Retrieves the latest audit log entries for a guild.
        """
        # Explicitly convert the SQLAlchemy `Sequence` result to a `list`.
        return list(await crud.get_latest_audit_log_entries(self._db, guild_id, limit))