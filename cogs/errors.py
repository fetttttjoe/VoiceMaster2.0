import discord
from discord.ext import commands
import logging

class ErrorHandlerCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_error(self, ctx: commands.Context, error: commands.CommandError):
        if isinstance(error, commands.CommandNotFound):
            return  # Ignore command not found errors
        elif isinstance(error, commands.MissingPermissions):
            await ctx.send("You don't have the required permissions to run this command.")
        elif isinstance(error, commands.NoPrivateMessage):
            await ctx.send("This command cannot be used in private messages.")
        else:
            # Check if the command exists before trying to access its name
            command_name = ctx.command.name if ctx.command else "unknown"
            logging.error(f"An error occurred in command {command_name}: {error}")
            await ctx.send("An unexpected error occurred. Please try again later.")

async def setup(bot: commands.Bot):
    """The entry point for loading the cog."""
    await bot.add_cog(ErrorHandlerCog(bot))
