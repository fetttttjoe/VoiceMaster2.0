import logging

import discord

from bot_instance import VoiceMasterBot
from config import settings
from database.database import db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    """Bootstrap and run the VoiceMasterBot."""
    if not settings.DISCORD_TOKEN:
        logging.critical(
            "DISCORD_TOKEN is not set. Please check your .env file."
        )
        return

    # Initialize DB (synchronous to set up pools, etc.)
    db.init_db(settings.DATABASE_URL)

    # Define gateway intents explicitly
    intents = discord.Intents.default()
    intents.message_content = True
    intents.voice_states = True
    intents.guilds = True
    intents.members = True

    # Instantiate the subclassed bot
    bot = VoiceMasterBot(command_prefix=".", intents=intents)

    # Run handles login -> setup_hook -> connect -> event loop -> cleanup
    try:
        bot.run(settings.DISCORD_TOKEN)
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested.")

if __name__ == "__main__":
    main()
