import pytest
from unittest.mock import patch, AsyncMock

from services.voice_channel_service import VoiceChannelService
from interfaces.voice_channel_repository import IVoiceChannelRepository
from interfaces.user_settings_repository import IUserSettingsRepository


@pytest.mark.asyncio
async def test_get_voice_channel_by_owner(mock_voice_channel_repository, mock_user_settings_repository):
    """
    Tests that get_voice_channel_by_owner calls get_by_owner on its repository.
    """
    vc_service = VoiceChannelService(mock_voice_channel_repository, mock_user_settings_repository)
    
    await vc_service.get_voice_channel_by_owner(123)
    mock_voice_channel_repository.get_by_owner.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_delete_voice_channel(mock_voice_channel_repository, mock_user_settings_repository):
    """
    Tests that delete_voice_channel calls delete on its repository.
    """
    vc_service = VoiceChannelService(mock_voice_channel_repository, mock_user_settings_repository)
    await vc_service.delete_voice_channel(456)
    mock_voice_channel_repository.delete.assert_called_once_with(456)
