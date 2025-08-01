from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession

from interfaces.audit_log_service import IAuditLogService
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from services.audit_log_service import AuditLogService
from services.guild_service import GuildService
from services.voice_channel_service import VoiceChannelService

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

        self.voice_channel_service: IVoiceChannelService = VoiceChannelService(self._session)
        self.audit_log_service: IAuditLogService = AuditLogService(self._session)

        self.guild_service: IGuildService = GuildService(session=self._session, voice_channel_service=self.voice_channel_service, bot=self._bot)
