import logging

from discord.ext import commands

from container import Container
from database.database import db
from interfaces.audit_log_service import IAuditLogService
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService


class VoiceMasterBot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        # Typed service placeholders
        self.guild_service: IGuildService
        self.voice_channel_service: IVoiceChannelService
        self.audit_log_service: IAuditLogService

    async def setup_hook(self) -> None:
        """
        Called once after login and before gateway connection.
        Perfect for async initialization of services and cogs.
        """
        # Initialize DB session
        session = await db.get_session().__aenter__()
        container = Container(session, self)

        # Attach services
        self.guild_service = container.guild_service
        self.voice_channel_service = container.voice_channel_service
        self.audit_log_service = container.audit_log_service

        # Load extensions (cogs)
        await self.load_extension("cogs.events")
        await self.load_extension("cogs.voice_commands")
        await self.load_extension("cogs.errors")
        logging.info("All cogs loaded successfully.")
