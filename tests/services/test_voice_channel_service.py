from unittest.mock import MagicMock

import pytest

from database.models import UserSettings, VoiceChannel
from services.voice_channel_service import VoiceChannelService


@pytest.mark.asyncio
async def test_get_voice_channel_by_owner(mock_voice_channel_repository):
    voice_channel_service = VoiceChannelService(mock_voice_channel_repository)
    mock_voice_channel_repository.get_voice_channel_by_owner.return_value = MagicMock(spec=VoiceChannel)
    result = await voice_channel_service.get_voice_channel_by_owner(123)
    mock_voice_channel_repository.get_voice_channel_by_owner.assert_called_once_with(123)
    assert result is not None


@pytest.mark.asyncio
async def test_get_voice_channel(mock_voice_channel_repository):
    voice_channel_service = VoiceChannelService(mock_voice_channel_repository)
    mock_voice_channel_repository.get_voice_channel.return_value = MagicMock(spec=VoiceChannel)
    result = await voice_channel_service.get_voice_channel(456)
    mock_voice_channel_repository.get_voice_channel.assert_called_once_with(456)
    assert result is not None


@pytest.mark.asyncio
async def test_delete_voice_channel(mock_voice_channel_repository):
    voice_channel_service = VoiceChannelService(mock_voice_channel_repository)
    await voice_channel_service.delete_voice_channel(789)
    mock_voice_channel_repository.delete_voice_channel.assert_called_once_with(789)


@pytest.mark.asyncio
async def test_create_voice_channel(mock_voice_channel_repository):
    voice_channel_service = VoiceChannelService(mock_voice_channel_repository)
    await voice_channel_service.create_voice_channel(111, 222, 333)
    mock_voice_channel_repository.create_voice_channel.assert_called_once_with(111, 222, 333)


@pytest.mark.asyncio
async def test_update_voice_channel_owner(mock_voice_channel_repository):
    voice_channel_service = VoiceChannelService(mock_voice_channel_repository)
    await voice_channel_service.update_voice_channel_owner(444, 555)
    mock_voice_channel_repository.update_voice_channel_owner.assert_called_once_with(444, 555)


@pytest.mark.asyncio
async def test_get_user_settings(mock_voice_channel_repository):
    voice_channel_service = VoiceChannelService(mock_voice_channel_repository)
    mock_voice_channel_repository.get_user_settings.return_value = MagicMock(spec=UserSettings)
    result = await voice_channel_service.get_user_settings(666)
    mock_voice_channel_repository.get_user_settings.assert_called_once_with(666)
    assert result is not None


@pytest.mark.asyncio
async def test_update_user_channel_name(mock_voice_channel_repository):
    voice_channel_service = VoiceChannelService(mock_voice_channel_repository)
    await voice_channel_service.update_user_channel_name(777, "New Name")
    mock_voice_channel_repository.update_user_channel_name.assert_called_once_with(777, "New Name")


@pytest.mark.asyncio
async def test_update_user_channel_limit(mock_voice_channel_repository):
    voice_channel_service = VoiceChannelService(mock_voice_channel_repository)
    await voice_channel_service.update_user_channel_limit(888, 10)
    mock_voice_channel_repository.update_user_channel_limit.assert_called_once_with(888, 10)
