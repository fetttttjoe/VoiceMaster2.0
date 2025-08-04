from unittest.mock import MagicMock

from container import Container


def test_container_initializes_all_repos_and_services():
    mock_session = MagicMock()
    bot = MagicMock()
    cont = Container(mock_session, bot)
    # Repositories
    from repositories.audit_log_repository import AuditLogRepository
    from repositories.guild_repository import GuildRepository
    from repositories.voice_channel_repository import VoiceChannelRepository
    assert isinstance(cont.audit_log_repository, AuditLogRepository)
    assert isinstance(cont.guild_repository, GuildRepository)
    assert isinstance(cont.voice_channel_repository, VoiceChannelRepository)
    # Services
    from services.audit_log_service import AuditLogService
    from services.guild_service import GuildService
    from services.voice_channel_service import VoiceChannelService
    assert isinstance(cont.audit_log_service, AuditLogService)
    assert isinstance(cont.voice_channel_service, VoiceChannelService)
    assert isinstance(cont.guild_service, GuildService)
