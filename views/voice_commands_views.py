# VoiceMaster2.0/views/voice_commands_views.py
import discord
from discord import ui
from discord.ext.commands import Context
import asyncio
import logging
from typing import cast, Literal, Optional

from main import VoiceMasterBot
from interfaces.guild_service import IGuildService
from interfaces.audit_log_service import IAuditLogService
from database.models import AuditLogEventType
from discord.interactions import Interaction

class AuthorOnlyView(ui.View):
    """
    A base View that only allows the original command author to interact.
    """
    def __init__(self, ctx: Context, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.bot: VoiceMasterBot = cast(VoiceMasterBot, ctx.bot)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Ensures that the interacting user is the original author of the command.
        """
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You are not the owner of this interactive component.", ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item) -> None:
        """
        Global error handler for the view. Logs unexpected errors.
        """
        logging.error(f"An error occurred in a view: {error}", exc_info=True)
        message = "An unexpected error occurred. This has been logged."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

class RenameView(AuthorOnlyView):
    """
    A view with buttons to rename the creation channel or category.
    """
    def __init__(self, ctx: Context):
        super().__init__(ctx, timeout=180.0)
        self.guild_service: IGuildService = self.bot.guild_service
        self.audit_log_service: IAuditLogService = self.bot.audit_log_service

    async def _perform_rename(self, interaction: discord.Interaction, target: Literal['channel', 'category']):
        """A helper method to handle the renaming logic."""
        prompt = f"Please type the new name for the 'Join to Create' {target}:"
        await interaction.response.send_message(prompt, ephemeral=True)
        
        try:
            msg = await self.bot.wait_for('message', check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60.0)
            await msg.delete() # Clean up the user's message immediately

            if not self.ctx.guild: return

            config = await self.guild_service.get_guild_config(self.ctx.guild.id)
            if not config:
                return await interaction.followup.send("Error: Bot not configured correctly.", ephemeral=True)

            target_id = config.creation_channel_id if target == 'channel' else config.voice_category_id
            if not isinstance(target_id, int):
                return await interaction.followup.send(f"Error: Configured {target} not found.", ephemeral=True)

            discord_obj = self.ctx.guild.get_channel(target_id)
            if not discord_obj:
                return await interaction.followup.send(f"Error: The configured {target} could not be found in this server.", ephemeral=True)

            old_name = discord_obj.name
            await discord_obj.edit(name=msg.content)

            response_msg = await self.ctx.send(f"✅ {target.capitalize()} renamed to **{msg.content}**.")
            await asyncio.sleep(10)
            await response_msg.delete()

            event_type = AuditLogEventType.CHANNEL_RENAMED if target == 'channel' else AuditLogEventType.CATEGORY_RENAMED
            await self.audit_log_service.log_event(
                guild_id=self.ctx.guild.id, event_type=event_type, user_id=self.ctx.author.id,
                channel_id=discord_obj.id, details=f"Renamed {target} from '{old_name}' to '{msg.content}'."
            )

        except asyncio.TimeoutError:
            await interaction.followup.send("Rename timed out. Please try again.", ephemeral=True)
        finally:
            self.stop()

    @ui.button(label="Rename 'Join' Channel", style=discord.ButtonStyle.primary, emoji="✏️")
    async def rename_channel_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._perform_rename(interaction, 'channel')

    @ui.button(label="Rename Category", style=discord.ButtonStyle.primary, emoji="✏️")
    async def rename_category_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._perform_rename(interaction, 'category')


class SelectView(AuthorOnlyView):
    """
    A view with dropdowns to select a new creation channel or category.
    """
    def __init__(self, ctx: Context, voice_channels: list, categories: list):
        super().__init__(ctx, timeout=180.0)
        self.guild_service: IGuildService = self.bot.guild_service
        self.audit_log_service: IAuditLogService = self.bot.audit_log_service

        channel_options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in voice_channels[:25]]
        channel_select = ui.Select(placeholder="Select a new 'Join to Create' channel...", options=channel_options, custom_id="channel_select")
        channel_select.callback = self.channel_select_callback
        self.add_item(channel_select)

        category_options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in categories[:25]]
        category_select = ui.Select(placeholder="Select a new category for temp channels...", options=category_options, custom_id="category_select")
        category_select.callback = self.category_select_callback
        self.add_item(category_select)

    async def _update_selection(self, interaction: Interaction, target: Literal['channel', 'category']):
        await interaction.response.defer(ephemeral=True)
        
        # --- 1. Guard Clauses for pre-conditions ---
        guild = self.ctx.guild
        if not guild or not guild.owner_id:
            logging.error("Guild or guild owner not found during selection update.")
            return

        config = await self.guild_service.get_guild_config(guild.id)
        if not config:
            return await interaction.followup.send("Error: Bot not configured correctly.", ephemeral=True)

        if interaction.data is None or 'values' not in interaction.data:
            return await interaction.followup.send("Error: Invalid interaction data.", ephemeral=True)
            
        if not isinstance(config.creation_channel_id, int) or not isinstance(config.voice_category_id, int):
            return await interaction.followup.send("Error: Voice category is not configured.", ephemeral=True)

        # --- 2. Prepare parameters for the update ---
        selected_id = int(interaction.data["values"][0])
        owner_id = guild.owner_id
        
        new_channel_id: int
        new_category_id: int
        event: AuditLogEventType
        old_id: Optional[int]

        if target == 'channel':
            new_channel_id = selected_id
            new_category_id = config.voice_category_id
            event = AuditLogEventType.CREATION_CHANNEL_CHANGED
            old_id = config.creation_channel_id
        else: # target == 'category'
            new_channel_id = config.creation_channel_id
            new_category_id = selected_id
            event = AuditLogEventType.VOICE_CATEGORY_CHANGED
            old_id = config.voice_category_id

        # --- 3. Perform the update and log the event ---
        await self.guild_service.create_or_update_guild(guild.id, owner_id, new_category_id, new_channel_id)

        await interaction.followup.send(f"✅ Configuration updated. The new {target} is <#{selected_id}>!", ephemeral=True)
        
        await self.audit_log_service.log_event(
            guild_id=guild.id, 
            event_type=event, 
            user_id=self.ctx.author.id,
            channel_id=selected_id, 
            details=f"Changed {target} from {old_id} to {selected_id}."
        )
        self.stop()

    async def channel_select_callback(self, interaction: Interaction):
        await self._update_selection(interaction, 'channel')

    async def category_select_callback(self, interaction: Interaction):
        await self._update_selection(interaction, 'category')