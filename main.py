import asyncio
import logging

import discord
from discord.ext import commands

from config import settings
from container import Container
from database.database import db
from interfaces.audit_log_service import IAuditLogService
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


class VoiceMasterBot(commands.Bot):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.guild_service: IGuildService
        self.voice_channel_service: IVoiceChannelService
        self.audit_log_service: IAuditLogService

    async def setup_hook(self) -> None:
        """
        This is called once when the bot logs in, before any events are dispatched.
        It's the perfect place for asynchronous initialization.
        """
        await db.init_db()

        session = await db.get_session().__aenter__()
        container = Container(session, self)

        self.guild_service = container.guild_service
        self.voice_channel_service = container.voice_channel_service
        self.audit_log_service = container.audit_log_service

        await self.load_extension("cogs.events")
        await self.load_extension("cogs.voice_commands")
        await self.load_extension("cogs.errors")
        logging.info("All cogs loaded successfully.")


async def main():
    """Initializes and runs the bot."""
    if not settings.DISCORD_TOKEN:
        logging.critical("DISCORD_TOKEN is not set. Please check your .env file.")
        return

    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True
    intents.members = True

    bot = VoiceMasterBot(command_prefix=".", intents=intents)

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
