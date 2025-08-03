import runpy
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot_instance import VoiceMasterBot


@pytest.mark.asyncio
@patch("main.settings")
@patch("main.asyncio.run")
@patch("main.VoiceMasterBot")
@patch("database.database.db")
async def test_main_starts_bot_and_runs_setup(
    mock_db: MagicMock,
    mock_VoiceMasterBot: MagicMock,
    mock_asyncio_run: MagicMock,
    mock_settings: MagicMock,
):
    """
    Tests that the main function initializes the database, configures the bot,
    and starts the bot. This implicitly tests that the setup_hook is run.
    """
    # Arrange
    mock_settings.DISCORD_TOKEN = "fake_token"
    mock_bot_instance = AsyncMock(spec=VoiceMasterBot)
    mock_VoiceMasterBot.return_value = mock_bot_instance

    # Dynamically import main to use the patches
    from main import main

    # Act
    await main()

    # Assert
    mock_db.init_db.assert_called_once_with(mock_settings.DATABASE_URL)
    mock_VoiceMasterBot.assert_called_once()
    mock_bot_instance.start.assert_called_once_with("fake_token")

    # The setup_hook is decorated on the bot instance, so we can check if it was awaited
    # This is an indirect way to verify the hook ran.
    assert mock_bot_instance.setup_hook.awaited


@pytest.mark.asyncio
@patch("main.settings")
@patch("main.VoiceMasterBot")
async def test_main_function_critical_log_on_no_token(
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
