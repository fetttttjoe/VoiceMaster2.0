# tests/test_main.py
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
    # Arrange
    # Mock the async session context manager
    mock_session = AsyncMock()
    mock_get_session.return_value.__aenter__.return_value = mock_session

    # Create a real instance of the bot
    bot = VoiceMasterBot(command_prefix=".", intents=discord.Intents.default())

    # Act
    await bot.setup_hook()

    # Assert
    # 1. Database was initialized
    mock_init_db.assert_called_once()
    mock_get_session.assert_called_once()

    # 2. Services were created and attached to the bot
    assert hasattr(bot, "guild_service")
    assert hasattr(bot, "voice_channel_service")
    assert hasattr(bot, "audit_log_service")
    assert bot.guild_service is not None
    assert bot.voice_channel_service is not None
    assert bot.audit_log_service is not None

    # 3. Cogs were loaded
    assert mock_load_extension.call_count == 3
    mock_load_extension.assert_any_call("cogs.events")
    mock_load_extension.assert_any_call("cogs.voice_commands")
    mock_load_extension.assert_any_call("cogs.errors")


@pytest.mark.asyncio
@patch("main.config")
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
    # Arrange
    from main import main  # Import late to allow patching

    mock_config.DISCORD_TOKEN = None

    # Act
    await main()

    # Assert
    assert "DISCORD_TOKEN is not set" in caplog.text
    mock_bot.assert_not_called()  # Bot should not be instantiated
