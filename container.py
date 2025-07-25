from sqlalchemy.ext.asyncio import AsyncSession
from typing import TYPE_CHECKING

# Abstractions
from interfaces.guild_repository import IGuildRepository
from interfaces.voice_channel_repository import IVoiceChannelRepository
from interfaces.user_settings_repository import IUserSettingsRepository
from interfaces.audit_log_repository import IAuditLogRepository
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from interfaces.audit_log_service import IAuditLogService

# Implementations
from database.repositories import (
    GuildRepository,
    VoiceChannelRepository,
    UserSettingsRepository,
    AuditLogRepository,
)
from services.guild_service import GuildService
from services.voice_channel_service import VoiceChannelService
from services.audit_log_service import AuditLogService

if TYPE_CHECKING:
    from main import VoiceMasterBot


class Container:
    """
    A simple dependency injection container.
    It creates instances of services and repositories, wiring them together.
    """

    def __init__(self, session: AsyncSession, bot: "VoiceMasterBot"):
        self._session = session
        self._bot = bot

        # Repositories
        self.guild_repository: IGuildRepository = GuildRepository(self._session)
        self.voice_channel_repository: IVoiceChannelRepository = VoiceChannelRepository(self._session)
        self.user_settings_repository: IUserSettingsRepository = UserSettingsRepository(self._session)
        self.audit_log_repository: IAuditLogRepository = AuditLogRepository(self._session)

        # Services
        self.voice_channel_service: IVoiceChannelService = VoiceChannelService(
            self.voice_channel_repository, self.user_settings_repository
        )
        self.audit_log_service: IAuditLogService = AuditLogService(self.audit_log_repository)
        
        self.guild_service: IGuildService = GuildService(
            guild_repository=self.guild_repository,
            voice_channel_service=self.voice_channel_service,
            bot=self._bot
        )