import asyncio
import logging
import discord
from discord.ext import commands
import config
from database.database import init_db

# Logging setup
logging.basicConfig(level=logging.INFO)

# Bot intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True
intents.members = True

# Bot initialization
bot = commands.Bot(command_prefix=".", intents=intents)
bot.remove_command("help")


@bot.event
async def on_ready():
    """Event triggered when the bot is ready."""
    logging.info(f'Logged in as {bot.user.name} ({bot.user.id})')
    logging.info('------')


async def load_extensions():
    """Load all cogs from the cogs directory."""
    await bot.load_extension('cogs.events')
    await bot.load_extension('cogs.voice_commands')
    logging.info("All cogs loaded successfully.")


async def main():
    """Main function to run the bot."""
    await init_db()  # Initialize the database
    async with bot:
        await load_extensions()
        await bot.start(config.DISCORD_TOKEN)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Bot shutdown requested.")