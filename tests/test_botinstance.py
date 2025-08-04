from unittest.mock import AsyncMock, MagicMock

import discord

from bot_instance import VoiceMasterBot
from container import Container


def test_voice_master_bot_setup_hook_initializes_services(monkeypatch):
    """
    Ensure setup_hook attaches services and loads cogs.
    """
    # Prepare bot
    bot = VoiceMasterBot(command_prefix="!", intents=discord.Intents.none())

    # Mock db.get_session return
    mock_session = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__.return_value = mock_session
    # Patch the get_session method on the db object used inside bot_instance
    import bot_instance
    monkeypatch.setattr(bot_instance.db, 'get_session', lambda: cm)

    # Mock Container in bot_instance namespace and capture calls
    import bot_instance
    container = MagicMock(spec=Container)
    container.guild_service = 'gs'
    container.voice_channel_service = 'vcs'
    container.audit_log_service = 'als'
    container_cls = MagicMock(return_value=container)
    monkeypatch.setattr(bot_instance, 'Container', container_cls)

    # Spy on load_extension calls calls
    bot.load_extension = AsyncMock()

    # Run the setup_hook coroutine
    import asyncio
    asyncio.run(bot.setup_hook())

    # Assert services attached from our mock container
    assert bot.guild_service == 'gs'
    assert bot.voice_channel_service == 'vcs'
    assert bot.audit_log_service == 'als'

    # Verify that all expected cogs were loaded
    bot.load_extension.assert_any_await('cogs.events')
    bot.load_extension.assert_any_await('cogs.voice_commands')
    bot.load_extension.assert_any_await('cogs.errors')
