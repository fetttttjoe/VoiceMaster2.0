from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import update

from database.models import Guild
from repositories.guild_repository import GuildRepository


@pytest.mark.asyncio
async def test_get_guild_config(mock_db_session: AsyncMock):
    """
    Tests retrieving a guild configuration.
    """
    repository = GuildRepository(mock_db_session)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = MagicMock(spec=Guild)
    mock_db_session.execute = AsyncMock(return_value=mock_result)

    result = await repository.get_guild_config(1)

    mock_db_session.execute.assert_called_once()
    assert result is not None


@pytest.mark.asyncio
async def test_create_or_update_guild_creates_new(mock_db_session: AsyncMock):
    """
    Tests creating a new guild configuration.
    """
    repository = GuildRepository(mock_db_session)
    with patch.object(repository, "get_guild_config", new_callable=AsyncMock) as mock_get_guild_config:
        mock_get_guild_config.return_value = None
        mock_db_session.add = MagicMock()
        mock_db_session.commit = AsyncMock()

        await repository.create_or_update_guild(1, 2, 3, 4)

        mock_db_session.add.assert_called_once()
        mock_db_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_or_update_guild_updates_existing(mock_db_session: AsyncMock):
    """
    Tests updating an existing guild configuration.
    """
    repository = GuildRepository(mock_db_session)
    with patch.object(repository, "get_guild_config", new_callable=AsyncMock) as mock_get_guild_config:
        mock_get_guild_config.return_value = MagicMock(spec=Guild)
        mock_db_session.execute = AsyncMock()
        mock_db_session.commit = AsyncMock()
        mock_db_session.add = MagicMock()

        await repository.create_or_update_guild(1, 2, 3, 4)

        mock_db_session.execute.assert_called_once()
        # More detailed assertion to check the update statement
        call_args = mock_db_session.execute.call_args[0][0]
        assert isinstance(call_args, type(update(Guild)))
        mock_db_session.commit.assert_called_once()
        mock_db_session.add.assert_not_called()


@pytest.mark.asyncio
async def test_set_cleanup_on_startup(mock_db_session: AsyncMock):
    """
    Tests setting the cleanup_on_startup flag for a guild.
    """
    repository = GuildRepository(mock_db_session)
    mock_db_session.execute = AsyncMock()
    mock_db_session.commit = AsyncMock()

    await repository.set_cleanup_on_startup(1, True)

    mock_db_session.execute.assert_called_once()
    call_args = mock_db_session.execute.call_args[0][0]
    assert isinstance(call_args, type(update(Guild)))
    stmt_str = str(call_args.compile(compile_kwargs={"literal_binds": True}))
    assert "cleanup_on_startup=true" in stmt_str.lower()
    mock_db_session.commit.assert_called_once()
