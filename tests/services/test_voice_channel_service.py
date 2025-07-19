import pytest
from unittest.mock import patch, AsyncMock
from services.voice_channel_service import VoiceChannelService

@pytest.mark.asyncio
async def test_get_voice_channel_by_owner(mock_db_session):
    with patch('database.crud.get_voice_channel_by_owner', new_callable=AsyncMock) as mock_get_by_owner:
        vc_service = VoiceChannelService(mock_db_session)
        await vc_service.get_voice_channel_by_owner(123)
        mock_get_by_owner.assert_called_once_with(mock_db_session, 123)

@pytest.mark.asyncio
async def test_delete_voice_channel(mock_db_session):
    with patch('database.crud.delete_voice_channel', new_callable=AsyncMock) as mock_delete:
        vc_service = VoiceChannelService(mock_db_session)
        await vc_service.delete_voice_channel(456)
        mock_delete.assert_called_once_with(mock_db_session, 456)