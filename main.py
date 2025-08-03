import asyncio
import logging

import discord

from bot_instance import VoiceMasterBot
from config import settings
from container import Container
from database.database import db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


async def main():
    """Initializes and runs the bot."""
    if not settings.DISCORD_TOKEN:
        logging.critical("DISCORD_TOKEN is not set. Please check your .env file.")
        return

    db.init_db(settings.DATABASE_URL)

    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True
    intents.members = True

    bot = VoiceMasterBot(command_prefix=".", intents=intents)

    @bot.setup_hook
    async def setup_hook() -> None:
        """
        This is called once when the bot logs in, before any events are dispatched.
        It's the perfect place for asynchronous initialization.
        """
        session = await db.get_session().__aenter__()
        container = Container(session, bot)

        bot.guild_service = container.guild_service
        bot.voice_channel_service = container.voice_channel_service
        bot.audit_log_service = container.audit_log_service

        await bot.load_extension("cogs.events")
        await bot.load_extension("cogs.voice_commands")
        await bot.load_extension("cogs.errors")
        logging.info("All cogs loaded successfully.")

    @bot.event
    async def on_ready() -> None:
        """Event triggered when the bot is ready."""
        if bot.user:
            logging.info(f"Logged in as {bot.user.name} ({bot.user.id})")
            logging.info("------")
        else:
            logging.error("Bot user is not available on ready.")

    await bot.start(settings.DISCORD_TOKEN)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested.")
