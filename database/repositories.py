from typing import Optional, List, cast
from sqlalchemy.ext.asyncio import AsyncSession
from database import crud
from database.models import Guild, VoiceChannel, UserSettings, AuditLogEntry, AuditLogEventType

# --- Repository Implementations ---

class GuildRepository:
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
        self.db = session

    async def get_guild(self, guild_id: int) -> Optional[Guild]:
        """
        Retrieves a Guild configuration.

        Args:
            guild_id: The ID of the guild.
        Returns:
            The Guild object if found, otherwise None.
        """
        return await crud.get_guild(self.db, guild_id)

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        """
        Creates or updates a Guild configuration.

        Args:
            guild_id: The ID of the guild.
            owner_id: The ID of the guild owner.
            category_id: The ID of the voice category.
            channel_id: The ID of the creation channel.
        """
        await crud.create_or_update_guild(self.db, guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        """
        Retrieves all active temporary voice channels.

        Returns:
            A list of VoiceChannel objects.
        """
        # Explicitly convert the SQLAlchemy `Sequence` result to a `list`
        # for clearer type hinting and direct list operations.
        return list(await crud.get_all_voice_channels(self.db))


class VoiceChannelRepository:
    """
    Implements the IVoiceChannelRepository interface, providing concrete database
    operations for VoiceChannel-related data using SQLAlchemy's CRUD functions.
    """
    def __init__(self, session: AsyncSession):
        """
        Initializes the VoiceChannelRepository with an asynchronous database session.

        Args:
            session: The SQLAlchemy asynchronous session.
        """
        self.db = session

    async def get_by_owner(self, owner_id: int) -> Optional[VoiceChannel]:
        """
        Retrieves a VoiceChannel entry by its owner's ID.
        """
        return await crud.get_voice_channel_by_owner(self.db, owner_id)

    async def get_by_channel_id(self, channel_id: int) -> Optional[VoiceChannel]:
        """
        Retrieves a VoiceChannel entry by its channel ID.
        """
        return await crud.get_voice_channel(self.db, channel_id)

    async def create(self, channel_id: int, owner_id: int) -> None:
        """
        Creates a new VoiceChannel entry.
        """
        await crud.create_voice_channel(self.db, channel_id, owner_id)

    async def delete(self, channel_id: int) -> None:
        """
        Deletes a VoiceChannel entry.
        """
        await crud.delete_voice_channel(self.db, channel_id)

    async def update_owner(self, channel_id: int, new_owner_id: int) -> None:
        """
        Updates the owner of a VoiceChannel.
        """
        await crud.update_voice_channel_owner(self.db, channel_id, new_owner_id)


class UserSettingsRepository:
    """
    Implements the IUserSettingsRepository interface, providing concrete database
    operations for UserSettings-related data using SQLAlchemy's CRUD functions.
    """
    def __init__(self, session: AsyncSession):
        """
        Initializes the UserSettingsRepository with an asynchronous database session.

        Args:
            session: The SQLAlchemy asynchronous session.
        """
        self.db = session

    async def get_user_settings(self, user_id: int) -> Optional[UserSettings]:
        """
        Retrieves UserSettings for a specific user.
        """
        return await crud.get_user_settings(self.db, user_id)

    async def update_channel_name(self, user_id: int, name: str) -> None:
        """
        Updates a user's custom channel name.
        """
        await crud.update_user_channel_name(self.db, user_id, name)

    async def update_channel_limit(self, user_id: int, limit: int) -> None:
        """
        Updates a user's custom channel limit.
        """
        await crud.update_user_channel_limit(self.db, user_id, limit)


class AuditLogRepository:
    """
    Implements the IAuditLogRepository interface, providing concrete database
    operations for AuditLogEntry-related data using SQLAlchemy's CRUD functions.
    """
    def __init__(self, session: AsyncSession):
        """
        Initializes the AuditLogRepository with an asynchronous database session.

        Args:
            session: The SQLAlchemy asynchronous session.
        """
        self.db = session

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
        """
        await crud.create_audit_log_entry(
            self.db, guild_id, event_type, user_id, channel_id, details
        )

    async def get_latest_entries(self, guild_id: int, limit: int = 10) -> List[AuditLogEntry]:
        """
        Retrieves the latest audit log entries for a guild.
        """
        # Explicitly convert the SQLAlchemy `Sequence` result to a `list`.
        return list(await crud.get_latest_audit_log_entries(self.db, guild_id, limit))