# VoiceMaster2.0/views/voice_commands_views.py
import asyncio
import logging
from typing import Literal, Optional, cast

import discord
from discord import ui
from discord.ext.commands import Context
from discord.interactions import Interaction

from config import settings
from database.models import AuditLogEventType, Guild
from interfaces.audit_log_service import IAuditLogService
from interfaces.guild_service import IGuildService
from main import VoiceMasterBot
from utils.db_helpers import is_db_value_equal


class AuthorOnlyView(ui.View):
    """
    A base View that only allows the original command author to interact.
    Includes robust error handling and automatic component disabling on timeout.
    """

    def __init__(self, ctx: Context, **kwargs):
        super().__init__(**kwargs)
        self.ctx = ctx
        self.bot: VoiceMasterBot = cast(VoiceMasterBot, ctx.bot)
        self.message: Optional[discord.Message] = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """
        Ensures that the interacting user is the original author of the command.
        """
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("You are not authorized to interact with this component.", ephemeral=True)
            return False
        return True

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item) -> None:
        """
        Global error handler for the view. Logs unexpected errors.
        """
        logging.error(f"An error occurred in view '{type(self).__name__}' (Item: {item}): {error}", exc_info=True)
        message = "An unexpected error occurred. This has been logged for review."
        if interaction.response.is_done():
            await interaction.followup.send(message, ephemeral=True)
        else:
            await interaction.response.send_message(message, ephemeral=True)

    async def disable_components(self):
        """
        Disables all components in the view and edits the original message if available.
        """
        for item in self.children:
            if isinstance(item, (ui.Button, ui.Select)):
                item.disabled = True
        if self.message:
            try:
                await self.message.edit(view=self)
            except discord.NotFound:
                logging.warning(f"Could not find message {self.message.id} to disable its components.")
            except discord.HTTPException as e:
                logging.error(f"Failed to edit message {self.message.id} to disable components: {e}")

    async def on_timeout(self) -> None:
        """
        Handles the view timeout by disabling all components.
        """
        await self.disable_components()
        self.stop()


class RenameView(AuthorOnlyView):
    """
    A view with buttons to rename the creation channel or category.
    """

    def __init__(self, ctx: Context):
        super().__init__(ctx, timeout=settings.VIEW_TIMEOUT)
        self.guild_service: IGuildService = self.bot.guild_service
        self.audit_log_service: IAuditLogService = self.bot.audit_log_service

    async def _perform_rename(self, interaction: discord.Interaction, target: Literal["channel", "category"]):
        """A helper method to handle the renaming logic."""
        prompt = f"Please type the new name for the 'Join to Create' {target}:"
        await interaction.response.send_message(prompt, ephemeral=True)

        try:
            msg = await self.bot.wait_for("message", check=lambda m: m.author == self.ctx.author and m.channel == self.ctx.channel, timeout=60.0)
            await msg.delete()  # Clean up the user's message immediately

            if not self.ctx.guild:
                return

            config = await self.guild_service.get_guild_config(self.ctx.guild.id)
            if config is None:  # Check for None
                return await interaction.followup.send("Error: Bot not configured correctly.", ephemeral=True)

            target_id = config.creation_channel_id if target == "channel" else config.voice_category_id
            if not isinstance(target_id, int):
                return await interaction.followup.send(f"Error: Configured {target} not found.", ephemeral=True)

            discord_obj = self.ctx.guild.get_channel(target_id)
            if discord_obj is None:  # Check for None
                return await interaction.followup.send(f"Error: The configured {target} could not be found in this server.", ephemeral=True)

            old_name = discord_obj.name
            await discord_obj.edit(name=msg.content)

            response_msg = await self.ctx.send(f"✅ {target.capitalize()} renamed to **{msg.content}**.")
            await asyncio.sleep(10)
            await response_msg.delete()

            event_type = AuditLogEventType.CHANNEL_RENAMED if target == "channel" else AuditLogEventType.CATEGORY_RENAMED
            await self.audit_log_service.log_event(
                guild_id=self.ctx.guild.id,
                event_type=event_type,
                user_id=self.ctx.author.id,
                channel_id=discord_obj.id,
                details=f"Renamed {target} from '{old_name}' to '{msg.content}'.",
            )

        except asyncio.TimeoutError:
            await interaction.followup.send("Rename timed out. Please try again.", ephemeral=True)
        finally:
            await self.disable_components()
            self.stop()

    @ui.button(label="Rename 'Join' Channel", style=discord.ButtonStyle.primary, emoji="✏️")
    async def rename_channel_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._perform_rename(interaction, "channel")

    @ui.button(label="Rename Category", style=discord.ButtonStyle.primary, emoji="✏️")
    async def rename_category_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._perform_rename(interaction, "category")


class SelectView(AuthorOnlyView):
    """
    A view with dropdowns to select a new creation channel or category.
    """

    def __init__(self, ctx: Context, voice_channels: list, categories: list):
        super().__init__(ctx, timeout=settings.VIEW_TIMEOUT)
        self.guild_service: IGuildService = self.bot.guild_service
        self.audit_log_service: IAuditLogService = self.bot.audit_log_service

        channel_options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in voice_channels[:25]]
        channel_select: ui.Select = ui.Select(placeholder="Select a new 'Join to Create' channel...", options=channel_options, custom_id="channel_select")
        channel_select.callback = self.channel_select_callback  # type: ignore
        self.add_item(channel_select)

        category_options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in categories[:25]]
        category_select: ui.Select = ui.Select(
            placeholder="Select a new category for temp channels...",
            options=category_options,
            custom_id="category_select",
        )
        category_select.callback = self.category_select_callback  # type: ignore
        self.add_item(category_select)

    async def _update_selection(self, interaction: Interaction, target: Literal["channel", "category"]):
        await interaction.response.defer(ephemeral=True)

        # --- 1. Guard Clauses for pre-conditions ---
        guild = self.ctx.guild
        if not guild or not guild.owner_id:
            logging.error("Guild or guild owner not found during selection update.")
            return

        config = await self.guild_service.get_guild_config(guild.id)
        if config is None:  # Check for None
            return await interaction.followup.send("Error: Bot not configured correctly.", ephemeral=True)

        if interaction.data is None or "values" not in interaction.data:
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

        if target == "channel":
            new_channel_id = selected_id
            new_category_id = config.voice_category_id
            event = AuditLogEventType.CREATION_CHANNEL_CHANGED
            old_id = config.creation_channel_id
        else:  # target == 'category'
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
            details=f"Changed {target} from {old_id} to {selected_id}.",
        )

        await self.disable_components()
        self.stop()

    async def channel_select_callback(self, interaction: Interaction):
        await self._update_selection(interaction, "channel")

    async def category_select_callback(self, interaction: Interaction):
        await self._update_selection(interaction, "category")


class ConfigView(AuthorOnlyView):
    """
    An interactive, persistent view for managing guild-specific bot configurations.
    """

    def __init__(self, ctx: Context, guild_config: Guild):
        super().__init__(ctx, timeout=None)
        self.guild_service: IGuildService = self.bot.guild_service
        self.audit_log_service: IAuditLogService = self.bot.audit_log_service
        self.guild_config = guild_config
        self._update_button_states()

    def _update_button_states(self):
        """Disables/Enables buttons based on the current config state."""
        for item in self.children:
            if isinstance(item, ui.Button):
                if item.custom_id == "enable_cleanup":
                    item.disabled = is_db_value_equal(self.guild_config.cleanup_on_startup, True)
                elif item.custom_id == "disable_cleanup":
                    item.disabled = is_db_value_equal(self.guild_config.cleanup_on_startup, False)

    async def _update_config(self, interaction: discord.Interaction, new_state: bool):
        if not self.ctx.guild:
            await interaction.response.send_message("This command can only be used in a server.", ephemeral=True)
            return

        if self.guild_config is None:
            await interaction.response.send_message("Guild configuration not found.", ephemeral=True)
            return

        details = f"Automatic cleanup on startup changed from {self.guild_config.cleanup_on_startup} to {new_state}."

        # Update the database
        await self.guild_service.set_cleanup_on_startup(self.ctx.guild.id, new_state)

        # Refresh local state from the database
        refreshed_config = await self.guild_service.get_guild_config(self.ctx.guild.id)
        if refreshed_config is None:
            await interaction.response.send_message("Error: Could not retrieve updated guild configuration.", ephemeral=True)
            self.stop()
            return
        self.guild_config = refreshed_config

        # Update the UI
        self._update_button_states()

        status_message = "Enabled" if new_state else "Disabled"
        status_icon = "✅" if new_state else "❌"

        embed = discord.Embed(
            title=f"VoiceMaster Config for {self.ctx.guild.name}",
            description="Use the buttons below to manage bot settings for this server.",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Automatic Channel Cleanup on Startup",
            value=f"{status_icon} Status: **{status_message}**\nThis feature automatically deletes empty temporary channels when the bot starts.",
            inline=False,
        )

        await interaction.response.edit_message(embed=embed, view=self)

        # Log the action
        await self.audit_log_service.log_event(
            guild_id=self.ctx.guild.id,
            event_type=AuditLogEventType.CLEANUP_STATE_CHANGED,
            user_id=interaction.user.id,
            details=details,
        )

    @ui.button(label="Enable Cleanup", style=discord.ButtonStyle.success, custom_id="enable_cleanup")
    async def enable_cleanup_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._update_config(interaction, True)

    @ui.button(label="Disable Cleanup", style=discord.ButtonStyle.danger, custom_id="disable_cleanup")
    async def disable_cleanup_button(self, interaction: discord.Interaction, button: ui.Button):
        await self._update_config(interaction, False)
