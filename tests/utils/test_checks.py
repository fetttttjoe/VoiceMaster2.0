# tests/utils/test_checks.py
from typing import cast
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest
from discord.ext import commands

from interfaces.voice_channel_service import IVoiceChannelService
from utils.checks import (
    NotChannelOwner,
    NotInVoiceChannel,
    is_channel_owner,
    is_in_voice_channel,
)


@pytest.fixture
def mock_ctx_with_voice():
    """Fixture for a mock context where the author is in a voice channel."""
    mock_ctx = AsyncMock(spec=commands.Context)
    mock_ctx.author = MagicMock(spec=discord.Member)
    mock_ctx.author.voice = MagicMock()
    mock_ctx.author.voice.channel = MagicMock(spec=discord.VoiceChannel)
    mock_ctx.author.id = 12345
    mock_ctx.author.voice.channel.id = 67890
    mock_ctx.bot = MagicMock()
    return mock_ctx


@pytest.fixture
def mock_ctx_without_voice():
    """Fixture for a mock context where the author is NOT in a voice channel."""
    mock_ctx = AsyncMock(spec=commands.Context)
    mock_ctx.author = MagicMock(spec=discord.Member)
    mock_ctx.author.voice = None
    return mock_ctx


@pytest.fixture
def mock_ctx_dm():
    """Fixture for a mock context where the author is in a DM."""
    mock_ctx = AsyncMock(spec=commands.Context)
    mock_ctx.author = MagicMock(spec=discord.User)
    return mock_ctx


@pytest.mark.asyncio
async def test_is_in_voice_channel_success(mock_ctx_with_voice):
    """Tests that is_in_voice_channel passes when the user is in a voice channel."""
    check = is_in_voice_channel()
    assert await check.predicate(mock_ctx_with_voice) is True


@pytest.mark.asyncio
async def test_is_in_voice_channel_failure(mock_ctx_without_voice):
    """Tests that is_in_voice_channel raises NotInVoiceChannel when the user is not in a voice channel."""
    check = is_in_voice_channel()
    with pytest.raises(NotInVoiceChannel):
        await check.predicate(mock_ctx_without_voice)


@pytest.mark.asyncio
async def test_is_in_voice_channel_failure_dm(mock_ctx_dm):
    """Tests that is_in_voice_channel raises NotInVoiceChannel when the command is used in a DM."""
    check = is_in_voice_channel()
    with pytest.raises(NotInVoiceChannel):
        await check.predicate(mock_ctx_dm)


@pytest.mark.asyncio
async def test_is_channel_owner_success(mock_ctx_with_voice):
    """Tests that is_channel_owner passes when the user is the owner of the channel."""
    mock_vc_service = AsyncMock(spec=IVoiceChannelService)
    mock_vc_service.get_voice_channel.return_value = MagicMock(owner_id=mock_ctx_with_voice.author.id)
    mock_bot = cast(commands.Bot, mock_ctx_with_voice.bot)
    mock_bot.voice_channel_service = mock_vc_service
    check = is_channel_owner()
    assert await check.predicate(mock_ctx_with_voice) is True
    mock_vc_service.get_voice_channel.assert_called_once_with(mock_ctx_with_voice.author.voice.channel.id)


@pytest.mark.asyncio
async def test_is_channel_owner_failure_not_owner(mock_ctx_with_voice):
    """Tests that is_channel_owner raises NotChannelOwner when the user is not the channel owner."""
    mock_vc_service = AsyncMock(spec=IVoiceChannelService)
    mock_vc_service.get_voice_channel.return_value = MagicMock(owner_id=54321)
    mock_bot = cast(commands.Bot, mock_ctx_with_voice.bot)
    mock_bot.voice_channel_service = mock_vc_service
    check = is_channel_owner()
    with pytest.raises(NotChannelOwner):
        await check.predicate(mock_ctx_with_voice)


@pytest.mark.asyncio
async def test_is_channel_owner_failure_not_temp_channel(mock_ctx_with_voice):
    """Tests that is_channel_owner raises NotChannelOwner if the channel is not a temp channel."""
    mock_vc_service = AsyncMock(spec=IVoiceChannelService)
    mock_vc_service.get_voice_channel.return_value = None
    mock_bot = cast(commands.Bot, mock_ctx_with_voice.bot)
    mock_bot.voice_channel_service = mock_vc_service
    check = is_channel_owner()
    with pytest.raises(NotChannelOwner):
        await check.predicate(mock_ctx_with_voice)


@pytest.mark.asyncio
async def test_is_channel_owner_failure_not_in_voice(mock_ctx_without_voice):
    """Tests that is_channel_owner raises NotInVoiceChannel if the user is not in a voice channel."""
    check = is_channel_owner()
    with pytest.raises(NotInVoiceChannel):
        await check.predicate(mock_ctx_without_voice)


@pytest.mark.asyncio
async def test_is_channel_owner_failure_dm(mock_ctx_dm):
    """Tests that is_channel_owner raises NotInVoiceChannel when the command is used in a DM."""
    check = is_channel_owner()
    with pytest.raises(NotInVoiceChannel):
        await check.predicate(mock_ctx_dm)
