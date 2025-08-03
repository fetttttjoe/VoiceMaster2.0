import os
import sys
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from interfaces.audit_log_repository import IAuditLogRepository
from interfaces.guild_repository import IGuildRepository
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_repository import IVoiceChannelRepository
from interfaces.voice_channel_service import IVoiceChannelService
from services.audit_log_service import AuditLogService


@pytest.fixture
def mock_guild_repository():
    """Fixture for a mocked GuildRepository instance."""
    return AsyncMock(spec=IGuildRepository)


@pytest.fixture
def mock_voice_channel_repository():
    """Fixture for a mocked VoiceChannelRepository instance."""
    return AsyncMock(spec=IVoiceChannelRepository)


@pytest.fixture
def mock_audit_log_repository():
    """Fixture for a mocked AuditLogRepository instance."""
    return AsyncMock(spec=IAuditLogRepository)


@pytest.fixture
def mock_guild_service():
    """Fixture for a mocked GuildService instance."""
    return AsyncMock(spec=IGuildService)


@pytest.fixture
def mock_voice_channel_service():
    """Fixture for a mocked VoiceChannelService instance."""
    return AsyncMock(spec=IVoiceChannelService)


@pytest.fixture
def mock_audit_log_service():
    """Fixture for a mocked AuditLogService instance."""
    return AsyncMock(spec=AuditLogService)


@pytest.fixture
def mock_bot(mock_guild_service, mock_voice_channel_service, mock_audit_log_service):
    """
    Provides a mock bot instance with all necessary services attached,
    simulating the real bot's dependency injection container.
    """
    bot = AsyncMock(spec=commands.Bot)
    bot.guild_service = mock_guild_service
    bot.voice_channel_service = mock_voice_channel_service
    bot.audit_log_service = mock_audit_log_service
    return bot


@pytest.fixture
def mock_guild():
    """Fixture for a mocked guild instance."""
    guild = AsyncMock(spec=discord.Guild)
    guild.id = 12345
    guild.owner_id = 67890
    guild.default_role = MagicMock(spec=discord.Role)
    return guild


@pytest.fixture
def mock_member(mock_guild):
    """Fixture for a mocked member instance."""
    member = AsyncMock(spec=discord.Member)
    member.id = 54321
    member.display_name = "TestUser"
    member.guild = mock_guild
    member.voice = AsyncMock(spec=discord.VoiceState)
    member.voice.channel = AsyncMock(spec=discord.VoiceChannel)
    return member


@pytest.fixture
def mock_ctx(mock_guild, mock_member, mock_bot):
    """
    Provides a complete mock context, including a bot with services attached.
    This is the primary context fixture to use for most command/view tests.
    """
    ctx = AsyncMock(spec=commands.Context)
    ctx.guild = mock_guild
    ctx.author = mock_member
    ctx.bot = mock_bot
    return ctx


@pytest.fixture
def mock_db_session():
    """Fixture for a mocked database session."""
    session = AsyncMock()
    session.add = MagicMock()
    return session
