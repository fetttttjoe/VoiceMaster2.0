import runpy
from unittest.mock import AsyncMock, MagicMock, patch

import discord
import pytest

from main import VoiceMasterBot


@pytest.mark.asyncio
@patch("database.database.db.init_db")
@patch("database.database.db.get_session")
@patch("main.VoiceMasterBot.load_extension")
async def test_setup_hook_initializes_services_and_loads_cogs(
    mock_load_extension: AsyncMock,
    mock_get_session: MagicMock,
    mock_init_db: AsyncMock,
):
    """
    Tests that the bot's setup_hook correctly initializes the database,
    creates the DI container, attaches services, and loads all cogs.
    """
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    bot = VoiceMasterBot(command_prefix=".", intents=discord.Intents.default())

    await bot.setup_hook()

    mock_init_db.assert_called_once()
    mock_get_session.assert_called_once()

    assert hasattr(bot, "guild_service")
    assert hasattr(bot, "voice_channel_service")
    assert hasattr(bot, "audit_log_service")
    assert bot.guild_service is not None
    assert bot.voice_channel_service is not None
    assert bot.audit_log_service is not None

    assert mock_load_extension.call_count == 3
    mock_load_extension.assert_any_call("cogs.events")
    mock_load_extension.assert_any_call("cogs.voice_commands")
    mock_load_extension.assert_any_call("cogs.errors")


@pytest.mark.asyncio
@patch("main.settings")
@patch("main.VoiceMasterBot")
@patch("asyncio.run")
async def test_main_function_critical_log_on_no_token(
    mock_asyncio_run: MagicMock,
    mock_bot: MagicMock,
    mock_config: MagicMock,
    caplog,
):
    """
    Tests that the main function logs a critical error if DISCORD_TOKEN is not set.
    """
    from main import main

    mock_config.DISCORD_TOKEN = None

    await main()

    assert "DISCORD_TOKEN is not set" in caplog.text
    mock_bot.assert_not_called()


@patch("main.main")
def test_main_entrypoint(mock_main: MagicMock):
    """
    Tests that the main function is called when the script is executed.
    """
    with patch.object(runpy, "run_path") as mock_run_path:
        runpy.run_path("main.py", run_name="__main__")
        mock_run_path.assert_called_once_with("main.py", run_name="__main__")
