from typing import Optional, List
from interfaces.guild_service import IGuildService
from interfaces.guild_repository import IGuildRepository
from database.models import Guild, VoiceChannel # VoiceChannel is used for type hinting in get_all_voice_channels

class GuildService(IGuildService):
    """
    Implements the business logic for guild-related operations.

    This service handles the core operations related to Discord guilds (servers),
    such as retrieving and updating guild configurations. It abstracts away the
    direct database interactions by depending on an `IGuildRepository` abstraction.
    """
    def __init__(self, guild_repository: IGuildRepository):
        """
        Initializes the GuildService with a guild repository.

        Args:
            guild_repository: An implementation of `IGuildRepository` responsible
                              for guild data persistence.
        """
        self._guild_repository = guild_repository

    async def get_guild_config(self, guild_id: int) -> Optional[Guild]:
        """
        Retrieves the configuration for a specific guild.

        Args:
            guild_id: The unique ID of the guild.

        Returns:
            A `Guild` object containing the configuration if found, otherwise `None`.
        """
        return await self._guild_repository.get_guild(guild_id)

    async def create_or_update_guild(self, guild_id: int, owner_id: int, category_id: int, channel_id: int) -> None:
        """
        Creates a new guild configuration or updates an existing one.

        This method is typically called during the bot's initial setup or whenever
        core guild settings (like the creation channel or voice category) are changed.

        Args:
            guild_id: The unique ID of the guild.
            owner_id: The ID of the guild owner.
            category_id: The ID of the voice category designated for temporary channels.
            channel_id: The ID of the "join to create" voice channel.
        """
        await self._guild_repository.create_or_update_guild(guild_id, owner_id, category_id, channel_id)

    async def get_all_voice_channels(self) -> List[VoiceChannel]:
        """
        Retrieves a list of all active temporary voice channels managed by the bot across all guilds.

        This is primarily used for administrative purposes, such as listing all currently
        active dynamic channels.

        Returns:
            A list of `VoiceChannel` objects.
        """
        return await self._guild_repository.get_all_voice_channels()
      
             
    async def get_voice_channels_by_guild(self, guild_id:int) -> List[VoiceChannel]:
      """
      Gets all active temporary voice channels for a specific guild.
      """
    
      # Explicitly convert the SQLAlchemy `Sequence` result to a `list`
      # for clearer type hinting and direct list operations.
     
      return  self._guild_repository.get_voice_channels_by_guild(guild_id)