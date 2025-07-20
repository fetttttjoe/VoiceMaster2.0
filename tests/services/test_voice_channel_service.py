import pytest
from unittest.mock import patch, AsyncMock

from services.voice_channel_service import VoiceChannelService
# Import the repository abstractions
from interfaces.voice_channel_repository import IVoiceChannelRepository
from interfaces.user_settings_repository import IUserSettingsRepository


@pytest.mark.asyncio
async def test_get_voice_channel_by_owner(mock_db_session): # mock_db_session is now unused but kept by fixture
    """
    Tests that get_voice_channel_by_owner calls get_by_owner on its repository.
    """
    # Create mocks for the required repositories
    mock_vc_repository = AsyncMock(spec=IVoiceChannelRepository)
    mock_user_settings_repository = AsyncMock(spec=IUserSettingsRepository)

    # Instantiate the service with the mocked repositories
    vc_service = VoiceChannelService(mock_vc_repository, mock_user_settings_repository)
    
    # Ensure the mocked method on the repository is set up
    mock_vc_repository.get_by_owner.return_value = None # Or a mock VoiceChannel object if testing a found case

    await vc_service.get_voice_channel_by_owner(123)
    # Assert that the method on the MOCKED REPOSITORY was called
    mock_vc_repository.get_by_owner.assert_called_once_with(123)


@pytest.mark.asyncio
async def test_delete_voice_channel(mock_db_session): # mock_db_session is now unused but kept by fixture
    """
    Tests that delete_voice_channel calls delete on its repository.
    """
    # Create mocks for the required repositories
    mock_vc_repository = AsyncMock(spec=IVoiceChannelRepository)
    mock_user_settings_repository = AsyncMock(spec=IUserSettingsRepository)

    # Instantiate the service with the mocked repositories
    vc_service = VoiceChannelService(mock_vc_repository, mock_user_settings_repository)
    await vc_service.delete_voice_channel(456)
    # Assert that the method on the MOCKED REPOSITORY was called
    mock_vc_repository.delete.assert_called_once_with(456)