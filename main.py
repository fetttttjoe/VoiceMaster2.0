import asyncio
import logging

import discord
from discord.ext import commands

import config
from container import Container
from database.database import db
from interfaces.audit_log_service import IAuditLogService

# Abstractions (for type hinting the bot class)
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService

# --- Logging Setup ---
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")


# --- Custom Bot Class ---
# By creating a custom Bot class, we can properly type-hint our services.
# This makes the rest of our code cleaner and fully understandable by Pylance.
class VoiceMasterBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize service attributes for type-hinting purposes.
        # They will be properly assigned in the setup_hook.
        self.guild_service: IGuildService
        self.voice_channel_service: IVoiceChannelService
        self.audit_log_service: IAuditLogService

    async def setup_hook(self) -> None:
        """
        This is called once when the bot logs in, before any events are dispatched.
        It's the perfect place for asynchronous initialization.
        """
        # 1. Initialize the database connection.
        await db.init_db()

        # 2. Create a session and the bot instance (self) to the container.
        session = await db.get_session().__aenter__()
        container = Container(session, self)

        # 3. Attach the fully initialized services to the bot instance.
        self.guild_service = container.guild_service
        self.voice_channel_service = container.voice_channel_service
        self.audit_log_service = container.audit_log_service

        # 4. Load all cogs. They can now safely access the services.
        await self.load_extension("cogs.events")
        await self.load_extension("cogs.voice_commands")
        await self.load_extension("cogs.errors")
        logging.info("All cogs loaded successfully.")


# --- Main Asynchronous Function ---
async def main():
    """Initializes and runs the bot."""
    if not config.DISCORD_TOKEN:
        logging.critical("DISCORD_TOKEN is not set. Please check your .env file.")
        return

    # --- Intents Setup ---
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True
    intents.members = True

    bot = VoiceMasterBot(command_prefix=".", intents=intents)

    @bot.event
    async def on_ready():
        """Event triggered when the bot is ready."""
        if bot.user:
            logging.info(f"Logged in as {bot.user.name} ({bot.user.id})")
            logging.info("------")
        else:
            logging.error("Bot user is not available on ready.")

    await bot.start(config.DISCORD_TOKEN)


# --- Application Entry Point ---
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested.")
