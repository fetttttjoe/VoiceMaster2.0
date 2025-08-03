from discord.ext import commands

from interfaces.audit_log_service import IAuditLogService
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService


class VoiceMasterBot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.guild_service: IGuildService
        self.voice_channel_service: IVoiceChannelService
        self.audit_log_service: IAuditLogService
