import pytest
from unittest.mock import AsyncMock, MagicMock

from services.voice_channel_service import VoiceChannelService
from database.models import VoiceChannel, UserSettings
from database import crud

@pytest.mark.asyncio
async def test_get_voice_channel_by_owner(mock_db_session):
    voice_channel_service = VoiceChannelService(mock_db_session)
    crud.get_voice_channel_by_owner = AsyncMock(return_value=MagicMock(spec=VoiceChannel))
    result = await voice_channel_service.get_voice_channel_by_owner(123)
    crud.get_voice_channel_by_owner.assert_called_once_with(mock_db_session, 123)
    assert result is not None

@pytest.mark.asyncio
async def test_get_voice_channel(mock_db_session):
    voice_channel_service = VoiceChannelService(mock_db_session)
    crud.get_voice_channel = AsyncMock(return_value=MagicMock(spec=VoiceChannel))
    result = await voice_channel_service.get_voice_channel(456)
    crud.get_voice_channel.assert_called_once_with(mock_db_session, 456)
    assert result is not None

@pytest.mark.asyncio
async def test_delete_voice_channel(mock_db_session):
    voice_channel_service = VoiceChannelService(mock_db_session)
    crud.delete_voice_channel = AsyncMock()
    await voice_channel_service.delete_voice_channel(789)
    crud.delete_voice_channel.assert_called_once_with(mock_db_session, 789)

@pytest.mark.asyncio
async def test_create_voice_channel(mock_db_session):
    voice_channel_service = VoiceChannelService(mock_db_session)
    crud.create_voice_channel = AsyncMock()
    await voice_channel_service.create_voice_channel(111, 222, 333)
    crud.create_voice_channel.assert_called_once_with(mock_db_session, 111, 222, 333)

@pytest.mark.asyncio
async def test_update_voice_channel_owner(mock_db_session):
    voice_channel_service = VoiceChannelService(mock_db_session)
    crud.update_voice_channel_owner = AsyncMock()
    await voice_channel_service.update_voice_channel_owner(444, 555)
    crud.update_voice_channel_owner.assert_called_once_with(mock_db_session, 444, 555)

@pytest.mark.asyncio
async def test_get_user_settings(mock_db_session):
    voice_channel_service = VoiceChannelService(mock_db_session)
    crud.get_user_settings = AsyncMock(return_value=MagicMock(spec=UserSettings))
    result = await voice_channel_service.get_user_settings(666)
    crud.get_user_settings.assert_called_once_with(mock_db_session, 666)
    assert result is not None

@pytest.mark.asyncio
async def test_update_user_channel_name(mock_db_session):
    voice_channel_service = VoiceChannelService(mock_db_session)
    crud.update_user_channel_name = AsyncMock()
    await voice_channel_service.update_user_channel_name(777, "New Name")
    crud.update_user_channel_name.assert_called_once_with(mock_db_session, 777, "New Name")

@pytest.mark.asyncio
async def test_update_user_channel_limit(mock_db_session):
    voice_channel_service = VoiceChannelService(mock_db_session)
    crud.update_user_channel_limit = AsyncMock()
    await voice_channel_service.update_user_channel_limit(888, 10)
    crud.update_user_channel_limit.assert_called_once_with(mock_db_session, 888, 10)
