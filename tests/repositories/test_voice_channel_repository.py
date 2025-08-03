from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from database.models import UserSettings, VoiceChannel
from repositories.voice_channel_repository import VoiceChannelRepository


@pytest.mark.asyncio
async def test_get_voice_channel_by_owner(mock_db_session: AsyncMock):
    repository = VoiceChannelRepository(mock_db_session)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(spec=VoiceChannel)
    mock_db_session.execute = AsyncMock(return_value=mock_result)
    result = await repository.get_voice_channel_by_owner(1)
    mock_db_session.execute.assert_called_once()
    assert result is not None


@pytest.mark.asyncio
async def test_create_voice_channel(mock_db_session: AsyncMock):
    repository = VoiceChannelRepository(mock_db_session)
    mock_db_session.add = MagicMock()
    mock_db_session.commit = AsyncMock()
    await repository.create_voice_channel(1, 2, 3)
    mock_db_session.add.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_voice_channel(mock_db_session: AsyncMock):
    repository = VoiceChannelRepository(mock_db_session)
    mock_db_session.execute = AsyncMock()
    mock_db_session.commit = AsyncMock()
    await repository.delete_voice_channel(1)
    mock_db_session.execute.assert_called_once()
    mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_update_user_channel_name_updates_existing(mock_db_session: AsyncMock):
    repository = VoiceChannelRepository(mock_db_session)
    with patch.object(repository, "get_user_settings", new_callable=AsyncMock) as mock_get_user_settings:
        mock_get_user_settings.return_value = MagicMock(spec=UserSettings)
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.add = MagicMock()
        await repository.update_user_channel_name(1, "new-name")
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_channel_name_creates_new(mock_db_session: AsyncMock):
    repository = VoiceChannelRepository(mock_db_session)
    with patch.object(repository, "get_user_settings", new_callable=AsyncMock) as mock_get_user_settings:
        mock_get_user_settings.return_value = None
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.execute = AsyncMock()
        await repository.update_user_channel_name(1, "new-name")
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.execute.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_channel_limit_updates_existing(mock_db_session: AsyncMock):
    repository = VoiceChannelRepository(mock_db_session)
    with patch.object(repository, "get_user_settings", new_callable=AsyncMock) as mock_get_user_settings:
        mock_get_user_settings.return_value = MagicMock(spec=UserSettings)
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.add = MagicMock()
        await repository.update_user_channel_limit(1, 5)
        mock_db_session.execute.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_update_user_channel_limit_creates_new(mock_db_session: AsyncMock):
    repository = VoiceChannelRepository(mock_db_session)
    with patch.object(repository, "get_user_settings", new_callable=AsyncMock) as mock_get_user_settings:
        mock_get_user_settings.return_value = None
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.execute = AsyncMock()
        await repository.update_user_channel_limit(1, 5)
        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()
        mock_db_session.execute.assert_not_called()
