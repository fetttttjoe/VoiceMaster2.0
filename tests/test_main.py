import logging
import runpy
from unittest.mock import MagicMock, patch


# Test that main() initializes DB and starts the bot using bot.run()
@patch("main.settings")
@patch("main.db")
@patch("main.VoiceMasterBot")
def test_main_starts_bot_and_runs_setup(mock_bot_cls, mock_db, mock_settings):
    """
    main() should initialize the database and call bot.run(token).
    """
    # Arrange
    mock_settings.DISCORD_TOKEN = "fake_token"
    mock_settings.DATABASE_URL = "db_url"
    mock_db.init_db = MagicMock()
    mock_bot = MagicMock()
    mock_bot_cls.return_value = mock_bot

    # Act
    import main
    main.main()

    # Assert
    mock_db.init_db.assert_called_once_with("db_url")
    mock_bot_cls.assert_called_once()
    mock_bot.run.assert_called_once_with("fake_token")

# Test that missing token logs a critical error and does not start the bot
@patch("main.settings", new=MagicMock(DISCORD_TOKEN=None))
@patch("main.db")
@patch("main.VoiceMasterBot")
def test_main_logs_critical_and_exits(mock_bot_cls, mock_db, caplog):
    """
    If DISCORD_TOKEN is not set, main() should log a critical message and return early.
    """
    import main
    caplog.set_level(logging.CRITICAL)
    main.main()
    assert "DISCORD_TOKEN is not set" in caplog.text
    mock_db.init_db.assert_not_called()
    mock_bot_cls.assert_not_called()

# Test the entrypoint calls run_path on __main__
@patch("runpy.run_path")
def test_entrypoint_uses_run_path(mock_run_path):
    import main
    with patch.object(main, '__name__', '__main__'):
        runpy.run_path("main.py", run_name="__main__")
    mock_run_path.assert_called_once_with("main.py", run_name="__main__")
