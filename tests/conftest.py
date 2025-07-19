import sys
import os
import pytest
from unittest.mock import AsyncMock, MagicMock
import discord
from discord.ext import commands

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture
def mock_bot():
    """Fixture for a mocked bot instance."""
    return AsyncMock(spec=commands.Bot)

@pytest.fixture
def mock_guild():
    """Fixture for a mocked guild instance."""
    guild = MagicMock(spec=discord.Guild)
    guild.id = 12345
    guild.owner_id = 67890
    guild.default_role = MagicMock(spec=discord.Role)
    return guild

@pytest.fixture
def mock_member(mock_guild):
    """Fixture for a mocked member instance."""
    member = MagicMock(spec=discord.Member)
    member.id = 54321
    member.display_name = "TestUser"
    member.guild = mock_guild
    member.voice = MagicMock(spec=discord.VoiceState)
    member.voice.channel = MagicMock(spec=discord.VoiceChannel)
    return member

@pytest.fixture
def mock_ctx(mock_guild, mock_member):
    """Fixture for a mocked context object."""
    ctx = AsyncMock(spec=commands.Context)
    ctx.guild = mock_guild
    ctx.author = mock_member
    return ctx

@pytest.fixture
def mock_db_session():
    """Fixture for a mocked database session."""
    return AsyncMock()