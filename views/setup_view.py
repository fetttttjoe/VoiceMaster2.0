# VoiceMaster2.0/views/setup_view.py
import logging
from typing import cast

import discord
from discord import ui
from discord.ext.commands import Context

from config import settings
from database.models import AuditLogEventType
from interfaces.audit_log_service import IAuditLogService
from interfaces.guild_service import IGuildService
from main import VoiceMasterBot
from views.voice_commands_views import AuthorOnlyView


class SetupModal(ui.Modal, title="VoiceMaster Setup"):
    category_name: ui.TextInput = ui.TextInput(label="Category Name", placeholder="e.g., 'Voice Channels'")
    channel_name: ui.TextInput = ui.TextInput(label="Creation Channel Name", placeholder="e.g., '➕ New Channel'")

    def __init__(self, bot: VoiceMasterBot, guild_service: IGuildService, audit_log_service: IAuditLogService):
        super().__init__()
        self.bot = bot
        self.guild_service = guild_service
        self.audit_log_service = audit_log_service

    async def on_submit(self, interaction: discord.Interaction):
        guild = interaction.guild
        if not guild or not guild.owner_id:
            await interaction.response.send_message("This command can only be used in a server by the server owner.", ephemeral=True)
            return

        try:
            # Create category
            category = await guild.create_category(self.category_name.value)
            # Create voice channel inside the category
            channel = await guild.create_voice_channel(name=self.channel_name.value, category=category)

            await self.guild_service.create_or_update_guild(
                guild_id=guild.id,
                owner_id=guild.owner_id,
                category_id=category.id,
                channel_id=channel.id,
            )

            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.BOT_SETUP,
                user_id=interaction.user.id,
                details=f"Setup complete. Category: '{category.name}', Channel: '{channel.name}'",
            )

            await interaction.response.send_message(
                f"✅ Setup complete! Users can now join '{channel.name}' to create their own channels.", ephemeral=True
            )
        except Exception as e:
            logging.error(f"Error during setup modal submission: {e}", exc_info=True)
            await interaction.response.send_message("An unexpected error occurred during setup.", ephemeral=True)


class SetupView(AuthorOnlyView):
    def __init__(self, ctx: Context):
        super().__init__(ctx, timeout=settings.VIEW_TIMEOUT)
        self.bot = cast(VoiceMasterBot, ctx.bot)
        self.guild_service: IGuildService = self.bot.guild_service
        self.audit_log_service: IAuditLogService = self.bot.audit_log_service

    @ui.button(label="Start Setup", style=discord.ButtonStyle.primary, emoji="⚙️")
    async def start_setup(self, interaction: discord.Interaction, button: ui.Button):
        modal = SetupModal(self.bot, self.guild_service, self.audit_log_service)
        await interaction.response.send_modal(modal)
        self.stop()
        await self.disable_components()
