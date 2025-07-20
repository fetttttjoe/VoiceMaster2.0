from sqlalchemy.ext.asyncio import AsyncSession

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


class Container:
    """
    A simple dependency injection container.
    It creates instances of services and repositories, wiring them together.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

        # Repositories
        self.guild_repository: IGuildRepository = GuildRepository(self.session)
        self.voice_channel_repository: IVoiceChannelRepository = VoiceChannelRepository(self.session)
        self.user_settings_repository: IUserSettingsRepository = UserSettingsRepository(self.session)
        self.audit_log_repository: IAuditLogRepository = AuditLogRepository(self.session)

        # Services
        self.guild_service: IGuildService = GuildService(self.guild_repository)
        self.voice_channel_service: IVoiceChannelService = VoiceChannelService(
            self.voice_channel_repository, self.user_settings_repository
        )
        self.audit_log_service: IAuditLogService = AuditLogService(self.audit_log_repository)

