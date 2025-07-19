import asyncio
import logging
import discord
from discord.ext import commands
import config
from database.database import db

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

# Bot initialization
bot = commands.Bot(command_prefix=".", intents=intents)

@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    if bot.user:
        logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
        logging.info('------')
    else:
        logging.error("Bot user is not available on ready.")


async def load_extensions():
    """Load all cogs from the cogs directory."""
    await bot.load_extension('cogs.events')
    await bot.load_extension('cogs.voice_commands')
    await bot.load_extension('cogs.errors')  # Load the new error handler
    logging.info("All cogs loaded successfully.")


async def main():
    """Main function to run the bot."""
    if not config.DISCORD_TOKEN:
        logging.critical("DISCORD_TOKEN is not set. Please check your .env file.")
        return

    await db.init_db()  # Initialize the database
    async with bot:
        await load_extensions()
        await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested.")