# VoiceMaster2.0/cogs/voice_commands.py
import logging
import discord
import asyncio
from discord import ui  # For Discord UI components like Buttons and Selects
from discord.ext import commands
from discord.ext.commands import Context
# `cast` for explicit type hints to help Pylance
from typing import Optional, Union, cast

from database.models import AuditLogEventType  # Enum for audit log event types
# Custom decorator for automatic audit logging
from services.audit_decorator import audit_log
from utils.checks import is_in_voice_channel, is_channel_owner  # Custom command checks
# Helper for safe database value comparison
from utils.db_helpers import is_db_value_equal

# Abstractions for dependency injection
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from interfaces.audit_log_service import IAuditLogService
from main import VoiceMasterBot  # Import your custom bot class for type hinting


class VoiceCommandsCog(commands.Cog):
    """
    A cog containing all commands related to temporary voice channel management.
    """

    def __init__(
        self,
        bot: VoiceMasterBot,
        guild_service: IGuildService,
        voice_channel_service: IVoiceChannelService,
        audit_log_service: IAuditLogService,
    ):
        """
        Initializes the VoiceCommandsCog with the bot instance and necessary services.

        Args:
            bot: The custom VoiceMasterBot instance.
            guild_service: Service for guild-related operations.
            voice_channel_service: Service for voice channel management.
            audit_log_service: Service for logging audit events.
        """
        self.bot = bot
        self.guild_service = guild_service
        self.voice_channel_service = voice_channel_service
        self.audit_log_service = audit_log_service
        # Store active UI views to manage their lifecycle and prevent memory leaks.
        # This will be useful if we create persistent views or need to clean up.
        self.active_views: dict[int, ui.View] = {}

    @commands.hybrid_group(invoke_without_command=True)
    async def voice(self, ctx: Context):
        """
        Displays a custom help embed for all VoiceMaster commands.

        This is the base command for the `voice` command group. When invoked
        without a subcommand (e.g., `.voice`), it sends an informative embed
        listing all available commands and their categories.
        """
        embed = discord.Embed(
            title="🎧 VoiceMaster Commands",
            description="Here are all the commands to manage your temporary voice channels. "
                        "Commands require you to be in a voice channel you own or manage, "
                        "unless otherwise specified.",
            color=discord.Color.blue()
        )
        embed.set_footer(
            text=f"Use {ctx.prefix}voice <command> to get started.")

        embed.add_field(
            name="🛠️ Admin Commands",
            value=(
                f"`{ctx.prefix}voice setup` - The first-time setup for the bot.\n"
                f"`{ctx.prefix}voice edit rename` - Rename the creation channel or category.\n"
                f"`{ctx.prefix}voice edit select` - Select a different creation channel or category.\n"
                f"`{ctx.prefix}voice list` - Lists all active temporary channels.\n"
                f"`{ctx.prefix}voice auditlog [count]` - Shows recent bot activity."
            ),
            inline=False
        )
        embed.add_field(
            name="👤 User Commands",
            value=(
                f"`{ctx.prefix}voice lock` - Locks your channel so nobody can join.\n"
                f"`{ctx.prefix}voice unlock` - Unlocks your channel for everyone.\n"
                f"`{ctx.prefix}voice permit @user` - Allows a specific user to join your locked channel.\n"
                f"`{ctx.prefix}voice claim` - Claims an empty, ownerless channel.\n"
                f"`{ctx.prefix}voice name <new_name>` - Sets a custom name for your channel.\n"
                f"`{ctx.prefix}voice limit <number>` - Sets a user limit for your channel (0 for none)."
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @voice.command(name="setup")
    # Requires administrator permissions to run
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()  # Can only be used in a Discord guild (server), not in DMs
    async def setup(self, ctx: Context):
        """
        Sets up the voice channel creation category and channel for the first time.

        This command guides an administrator through creating a dedicated category
        for temporary voice channels and a "join to create" voice channel.
        It then saves these configurations to the database.
        """
        guild = ctx.guild  # Get the guild object from the context
        if not guild:
            # This check is technically redundant due to @commands.guild_only(),
            # but serves as a type guard for static analysis and explicit safety.
            logging.warning(
                f"Setup command invoked outside a guild context by {ctx.author.id}.")
            return await ctx.send("This command can only be used in a server.", ephemeral=True)

        # Define a check function for `bot.wait_for` to ensure responses come from
        # the same author in the same channel.
        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("I'll guide you through setting up temporary voice channels. "
                       "First, enter the name for the new **category** where temporary channels will be created:")
        try:
            # Wait for the user's response for the category name with a timeout.
            category_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            # Create the Discord category channel.
            category = await guild.create_category(name=category_msg.content)
            logging.info(
                f"Created category '{category.name}' ({category.id}) in guild {guild.id}.")

            await ctx.send("Great! Now, enter the name for the **voice channel** users will join to create their own (e.g., 'Join to Create'):")
            # Wait for the user's response for the creation channel name.
            channel_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            # Create the Discord voice channel within the newly created category.
            channel = await guild.create_voice_channel(name=channel_msg.content, category=category)
            logging.info(
                f"Created creation channel '{channel.name}' ({channel.id}) in category {category.id}.")

            # Ensure guild owner ID is available for database storage.
            if not guild.owner_id:
                logging.error(
                    f"Could not determine owner_id for guild {guild.id} during setup.")
                return await ctx.send("Could not determine the server owner. Setup aborted.", ephemeral=True)

            # Store or update the guild configuration in the database.
            await self.guild_service.create_or_update_guild(guild.id, guild.owner_id, category.id, channel.id)
            logging.info(
                f"Guild {guild.id} setup configuration saved to database.")

            # Log the successful bot setup event.
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.BOT_SETUP,
                user_id=ctx.author.id,
                details=(
                    f"Bot setup complete. Category: '{category.name}' ({category.id}), "
                    f"Creation Channel: '{channel.name}' ({channel.id})."
                )
            )

            await ctx.send(f"✅ Setup complete! Users can now join '{channel.name}' to create their own channels.")

        except asyncio.TimeoutError:
            # Handle cases where the user does not respond within the timeout period.
            logging.warning(
                f"Setup timed out for user {ctx.author.id} in guild {guild.id}.")
            await ctx.send("Setup timed out. Please try again.", ephemeral=True)
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.SETUP_TIMED_OUT,
                user_id=ctx.author.id,
                details="Bot setup timed out due to no response."
            )
        except Exception as e:
            # Catch any other unexpected errors during the setup process.
            logging.error(
                f"An unexpected error occurred during setup in guild {guild.id} by {ctx.author.id}: {e}", exc_info=True)
            await ctx.send(f"An error occurred during setup: {e}. Please check logs.", ephemeral=True)
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.SETUP_ERROR,
                user_id=ctx.author.id,
                details=f"An error occurred during setup: {e}"
            )

    @voice.group(name="edit", invoke_without_command=True)
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def edit(self, ctx: Context):
        """
        Group command for editing bot configuration (rename/select channels).
        If no subcommand is given, it prompts the user.
        """
        await ctx.send("Please specify what you want to edit. Use `.voice edit rename` or `.voice edit select`.")

    @edit.command(name="rename")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def edit_rename(self, ctx: Context):
        """
        Allows renaming the existing "Join to Create" channel or the temporary channels category.
        Provides interactive buttons for the user to choose what to rename.
        """
        guild = ctx.guild
        if not guild:
            logging.warning(
                f"Edit rename command invoked outside a guild context by {ctx.author.id}.")
            return await ctx.send("This command can only be used in a server.", ephemeral=True)

        guild_config = await self.guild_service.get_guild_config(guild.id)
        if not guild_config:
            # Bot must be set up before attempting to rename configured channels/categories.
            return await ctx.send("The bot has not been set up yet. Run `.voice setup` first.", ephemeral=True)

        # Create UI buttons for renaming options.
        view = ui.View(timeout=180.0)  # View times out after 3 minutes
        rename_channel_btn = ui.Button(
            label="Rename 'Join' Channel", style=discord.ButtonStyle.primary, emoji="✏️")
        rename_category_btn = ui.Button(
            label="Rename Category", style=discord.ButtonStyle.primary, emoji="✏️")

        async def rename_channel_callback(interaction: discord.Interaction):
            """Callback for the 'Rename Join Channel' button."""
            # Ensure only the original invoker can interact.
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)

            # Send an ephemeral message asking for the new name.
            await interaction.response.send_message("Please type the new name for the 'Join to Create' channel:", ephemeral=True)

            try:
                # Wait for the user's message containing the new name.
                msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0)

                # Retrieve the latest guild config in case it changed since button press.
                current_guild_config = await self.guild_service.get_guild_config(guild.id)
                # Ensure current_guild_config is not None before proceeding.
                if current_guild_config and isinstance(current_guild_config.creation_channel_id, int):
                    # Assign to local variable
                    creation_channel_id = current_guild_config.creation_channel_id
                    creation_channel = guild.get_channel(creation_channel_id)

                    if creation_channel and isinstance(creation_channel, discord.VoiceChannel):
                        old_name = creation_channel.name
                        # Perform the rename on Discord
                        await creation_channel.edit(name=msg.content)
                        logging.info(
                            f"Creation channel '{old_name}' renamed to '{msg.content}' in guild {guild.id}.")
                        await msg.reply(f"✅ Channel renamed to **{msg.content}**.", delete_after=10)

                        await self.audit_log_service.log_event(
                            guild_id=guild.id,
                            event_type=AuditLogEventType.CHANNEL_RENAMED,
                            user_id=ctx.author.id,
                            channel_id=creation_channel.id,
                            details=f"Creation channel renamed from '{old_name}' to '{msg.content}'."
                        )
                    else:
                        logging.warning(
                            f"Configured creation channel {creation_channel_id} not found for renaming in guild {guild.id}.")
                        await interaction.followup.send("Error: Configured 'Join to Create' channel not found or is no longer a voice channel.", ephemeral=True)
                else:
                    logging.warning(
                        f"Invalid creation_channel_id in guild {guild.id} during rename attempt: {current_guild_config.creation_channel_id if current_guild_config else 'None'}.")
                    await interaction.followup.send("Error: Invalid creation channel configured. Please run setup again.", ephemeral=True)
                # Delete the user's input message for cleanliness.
                await msg.delete()
            except asyncio.TimeoutError:
                logging.warning(
                    f"Renaming 'Join' channel timed out for {ctx.author.id} in guild {guild.id}.")
                await interaction.followup.send("Rename timed out. Please try again.", ephemeral=True)
                await self.audit_log_service.log_event(
                    guild_id=guild.id,
                    event_type=AuditLogEventType.CHANNEL_RENAME_TIMED_OUT,
                    user_id=ctx.author.id,
                    details="Renaming 'Join' channel timed out."
                )
            except Exception as e:
                logging.error(
                    f"Error renaming 'Join' channel in guild {guild.id} by {ctx.author.id}: {e}", exc_info=True)
                await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
                await self.audit_log_service.log_event(
                    guild_id=guild.id,
                    event_type=AuditLogEventType.CHANNEL_RENAME_ERROR,
                    user_id=ctx.author.id,
                    details=f"An error occurred during setup: {e}"
                )
            finally:
                # Stop the view after an action is completed or times out.
                view.stop()

        async def rename_category_callback(interaction: discord.Interaction):
            """Callback for the 'Rename Category' button."""
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)

            await interaction.response.send_message("Please type the new name for the temporary channels category:", ephemeral=True)
            try:
                msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0)

                current_guild_config = await self.guild_service.get_guild_config(guild.id)
                # Ensure current_guild_config is not None before proceeding.
                if current_guild_config and isinstance(current_guild_config.voice_category_id, int):
                    voice_category_id = current_guild_config.voice_category_id  # Assign to local variable
                    category = guild.get_channel(voice_category_id)

                    if category and isinstance(category, discord.CategoryChannel):
                        old_name = category.name
                        # Perform the rename on Discord
                        await category.edit(name=msg.content)
                        logging.info(
                            f"Category '{old_name}' renamed to '{msg.content}' in guild {guild.id}.")
                        await msg.reply(f"✅ Category renamed to **{msg.content}**.", delete_after=10)

                        await self.audit_log_service.log_event(
                            guild_id=guild.id,
                            event_type=AuditLogEventType.CATEGORY_RENAMED,
                            user_id=ctx.author.id,
                            channel_id=category.id,
                            details=f"Category renamed from '{old_name}' to '{msg.content}'."
                        )
                    else:
                        logging.warning(
                            f"Configured voice category {voice_category_id} not found for renaming in guild {guild.id}.")
                        await interaction.followup.send("Error: Configured temporary channels category not found or is no longer a category.", ephemeral=True)
                else:
                    logging.warning(
                        f"Invalid voice_category_id in guild {guild.id} during rename attempt: {current_guild_config.voice_category_id if current_guild_config else 'None'}.")
                    await interaction.followup.send("Error: Invalid voice category configured. Please run setup again.", ephemeral=True)
                await msg.delete()
            except asyncio.TimeoutError:
                logging.warning(
                    f"Renaming category timed out for {ctx.author.id} in guild {guild.id}.")
                await interaction.followup.send("Rename timed out. Please try again.", ephemeral=True)
                await self.audit_log_service.log_event(
                    guild_id=guild.id,
                    event_type=AuditLogEventType.CATEGORY_RENAME_TIMED_OUT,
                    user_id=ctx.author.id,
                    details="Renaming category timed out."
                )
            except Exception as e:
                logging.error(
                    f"Error renaming category in guild {guild.id} by {ctx.author.id}: {e}", exc_info=True)
                await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
                await self.audit_log_service.log_event(
                    guild_id=guild.id,
                    event_type=AuditLogEventType.CATEGORY_RENAME_ERROR,
                    user_id=ctx.author.id,
                    details=f"An error occurred during setup: {e}"
                )
            finally:
                # Stop the view after an action is completed or times out.
                view.stop()

        rename_channel_btn.callback = rename_channel_callback
        rename_category_btn.callback = rename_category_callback
        view.add_item(rename_channel_btn)
        view.add_item(rename_category_btn)

        # Store view to manage its lifecycle
        self.active_views[ctx.channel.id] = view
        await ctx.send("Press a button to start renaming:", view=view)

        # Remove view from active_views when it stops.
        await view.wait()
        if ctx.channel.id in self.active_views:
            del self.active_views[ctx.channel.id]

    @voice.command(name="select")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def edit_select(self, ctx: Context):
        """
        Allows an administrator to select an existing channel to be the "Join to Create" channel
        or an existing category to be the temporary channels category.
        Provides dropdowns for selection.
        """
        guild = ctx.guild
        if not guild:
            logging.warning(
                f"Edit select command invoked outside a guild context by {ctx.author.id}.")
            return await ctx.send("This command can only be used in a server.", ephemeral=True)
        if not guild.owner_id:
            # We need the owner_id to update guild config in DB.
            logging.error(
                f"Guild {guild.id} has no owner_id, cannot proceed with edit select.")
            return await ctx.send("Could not determine the server owner. Cannot update configuration.", ephemeral=True)

        guild_config = await self.guild_service.get_guild_config(guild.id)
        if not guild_config:
            return await ctx.send("The bot has not been set up yet. Run `.voice setup` first.", ephemeral=True)

        view = ui.View(timeout=180.0)

        # Prepare options for selecting a "Join to Create" channel.
        # Only list voice channels that are part of a category to keep options relevant.
        voice_channels = [c for c in guild.voice_channels if c.category]
        if not voice_channels:
            await ctx.send("No voice channels with categories found to select from.", ephemeral=True)
            return

        channel_options = [discord.SelectOption(
            label=c.name, value=str(c.id)) for c in voice_channels]
        # Max 25 options per select menu. If more, implement pagination or search.
        if len(channel_options) > 25:
            # Truncate for simplicity for now
            channel_options = channel_options[:25]
        channel_select = ui.Select(
            placeholder="Select a new 'Join to Create' channel...", options=channel_options)

        # Prepare options for selecting a new temporary channels category.
        categories = guild.categories
        if not categories:
            await ctx.send("No categories found to select from.", ephemeral=True)
            return

        category_options = [discord.SelectOption(
            label=cat.name, value=str(cat.id)) for cat in categories]
        if len(category_options) > 25:
            # Truncate for simplicity for now
            category_options = category_options[:25]
        category_select = ui.Select(
            placeholder="Select a new category for temp channels...", options=category_options)

        async def channel_callback(interaction: discord.Interaction):
            """Callback for the 'Select Channel' dropdown."""
            await interaction.response.defer(ephemeral=True)  # Defer to show "Bot is thinking..."
            if interaction.user != ctx.author or not guild.owner_id:
                return await interaction.followup.send("You cannot interact with this menu.", ephemeral=True)

            # Re-fetch config to ensure it's up-to-date before updating.
            current_guild_config = await self.guild_service.get_guild_config(guild.id)
            # Ensure current_guild_config is not None before proceeding.
            if not current_guild_config or not isinstance(current_guild_config.voice_category_id, int):
                logging.error(
                    f"Error: Could not find current config for guild {guild.id} or voice_category_id is invalid.")
                return await interaction.followup.send("Error: Could not find current configuration or voice category is invalid. Please try setup again.", ephemeral=True)

            old_channel_id = current_guild_config.creation_channel_id
            # Get the selected channel ID
            new_channel_id = int(channel_select.values[0])

            # Update the guild configuration in the database.
            await self.guild_service.create_or_update_guild(guild.id, guild.owner_id, current_guild_config.voice_category_id, new_channel_id)
            logging.info(
                f"Creation channel updated from {old_channel_id} to {new_channel_id} in guild {guild.id}.")
            await interaction.followup.send(f"✅ 'Join to Create' channel updated to <#{new_channel_id}>!")

            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.CREATION_CHANNEL_CHANGED,
                user_id=ctx.author.id,
                channel_id=new_channel_id,
                details=f"'Join to Create' channel changed from {old_channel_id} to {new_channel_id}."
            )
            view.stop()  # Stop the view so it can be cleaned up.

        async def category_callback(interaction: discord.Interaction):
            """Callback for the 'Select Category' dropdown."""
            await interaction.response.defer(ephemeral=True)
            if interaction.user != ctx.author or not guild.owner_id:
                return await interaction.followup.send("You cannot interact with this menu.", ephemeral=True)

            current_config = await self.guild_service.get_guild_config(guild.id)
            # Ensure current_config is not None before proceeding.
            if not current_config or not isinstance(current_config.creation_channel_id, int):
                logging.error(
                    f"Error: Could not find current config for guild {guild.id} or creation_channel_id is invalid.")
                return await interaction.followup.send("Error: Could not find current configuration or creation channel is invalid. Please try setup again.", ephemeral=True)

            old_category_id = current_config.voice_category_id
            # Get the selected category ID
            new_category_id = int(category_select.values[0])

            # Update the guild configuration in the database.
            await self.guild_service.create_or_update_guild(guild.id, guild.owner_id, new_category_id, current_config.creation_channel_id)
            logging.info(
                f"Voice category updated from {old_category_id} to {new_category_id} in guild {guild.id}.")
            await interaction.followup.send(f"✅ Category for temporary channels updated to <#{new_category_id}>!")

            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.VOICE_CATEGORY_CHANGED,
                user_id=ctx.author.id,
                channel_id=new_category_id,
                details=f"Voice category changed from {old_category_id} to {new_category_id}."
            )
            view.stop()  # Stop the view.

        channel_select.callback = channel_callback
        category_select.callback = category_callback

        view.add_item(channel_select)
        view.add_item(category_select)

        self.active_views[ctx.channel.id] = view
        await ctx.send("Use the dropdowns to select a new channel or category:", view=view, ephemeral=True)

        await view.wait()
        if ctx.channel.id in self.active_views:
            del self.active_views[ctx.channel.id]

    @voice.command(name="list")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    @audit_log(AuditLogEventType.LIST_CHANNELS, "User {ctx.author.display_name} listed active temporary channels.")
    async def list_channels(self, ctx: Context):
        """
        Lists all active temporary voice channels managed by the bot in the current guild.
        Provides an embed with channel names and their owners.
        """
        guild = ctx.guild
        if not guild:
            # Redundant due to @commands.guild_only(), but good for type safety.
            return await ctx.send("This command can only be used in a server.", ephemeral=True)

        logging.info(f"DEBUG: list_channels called in guild {guild.id}")
        all_channels = await self.guild_service.get_all_voice_channels()
        logging.info(f"DEBUG: All voice channels from DB: {len(all_channels)} entries.")

        # Filter channels to only those belonging to the current guild
        # Assuming VoiceChannel model has guild_id, or we need to fetch guild-specific channels.
        # Currently, get_all_voice_channels returns all channels across all guilds.
        # A more efficient approach would be to have a get_guild_voice_channels in crud.
        # For now, filter after fetching.
        guild_channels = []
        for vc in all_channels:
            logging.info(f"DEBUG: Processing VC: {vc.channel_id} (owner: {vc.owner_id})")
            if isinstance(vc.channel_id, int):
                channel_obj = guild.get_channel(vc.channel_id)
                # Check if the channel object exists and is indeed a voice channel within this guild
                # Added channel_obj.guild check
                logging.info(f"DEBUG: Discord channel obj for {vc.channel_id}: {channel_obj.id if channel_obj else 'None'}")
                if channel_obj and isinstance(channel_obj, discord.VoiceChannel) and channel_obj.guild and is_db_value_equal(channel_obj.guild.id, guild.id):
                    logging.info(f"DEBUG: Found relevant channel: {channel_obj.id} in guild {channel_obj.guild.id}")
                    guild_channels.append(vc)
                else:
                    logging.info(f"DEBUG: Channel {vc.channel_id} not relevant for this guild or not a voice channel.")
            else:
                logging.info(f"DEBUG: vc.channel_id is not an int: {vc.channel_id}")


        logging.info(f"DEBUG: Filtered guild_channels count: {len(guild_channels)}")
        if not guild_channels:
            logging.info(f"DEBUG: No active temporary channels found for guild {guild.id}. Sending ephemeral message.")
            await ctx.send("There are no active temporary channels managed by VoiceMaster in this guild.", ephemeral=True)
            # Audit log is handled by the decorator for this case as well.
            return

        embed = discord.Embed(
            title="Active Temporary Channels", color=discord.Color.green())
        # Use a list to build description efficiently
        description_lines: list[str] = []

        for vc in guild_channels:
            # Ensure IDs are integers for API calls and type safety.
            assert isinstance(vc.channel_id, int) and isinstance(
                vc.owner_id, int)

            # Fetch Discord channel and owner member objects.
            channel = guild.get_channel(vc.channel_id)
            # get_member is a cached lookup, fetch_member for non-cached
            owner = guild.get_member(vc.owner_id)

            if channel and owner:
                # If both channel and owner are found on Discord.
                description_lines.append(
                    f"**{channel.name}** (<#{channel.id}>) - Owned by {owner.mention}")
            elif channel:
                # If channel found but owner not (e.g., owner left guild).
                description_lines.append(
                    f"**{channel.name}** (<#{channel.id}>) - Owner not found (ID: {vc.owner_id})")
            # If channel is None, it implies a stale entry, which should ideally be cleaned up by events.
            # We don't add stale entries to the list here.

        embed.description = "\n".join(
            description_lines) if description_lines else "No active temporary channels found."
        await ctx.send(embed=embed)
        logging.info(f"DEBUG: Sent embed for active channels. Embed description length: {len(embed.description)}")
        # Audit log is handled by the decorator.

    @voice.command(name="lock")
    @commands.guild_only()
    # Apply custom checks to ensure user is in a voice channel and owns it.
    @is_in_voice_channel()
    @is_channel_owner()
    @audit_log(AuditLogEventType.CHANNEL_LOCKED, "User {ctx.author.display_name} ({ctx.author.id}) locked channel '{ctx.author.voice.channel.name}' ({ctx.author.voice.channel.id}).")
    async def lock(self, ctx: Context):
        """
        Locks your current temporary voice channel, preventing others from joining.
        Requires the user to be in and own the channel.
        """
        # Type guards based on checks applied by decorators.
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)
        # Ensure author.voice and author.voice.channel are not None before casting
        if not author.voice or not author.voice.channel:
            # This case should ideally be caught by @is_in_voice_channel()
            # but this acts as a robust type guard for Pylance if it struggles
            # with decorator-based type narrowing.
            # Fallback error
            return await ctx.send("Error: Could not determine your voice channel.", ephemeral=True)

        voice_channel_obj = cast(discord.VoiceChannel, author.voice.channel)

        # Set `connect` permission to `False` for `@everyone` role.
        await voice_channel_obj.set_permissions(guild.default_role, connect=False)
        await ctx.send("🔒 Channel locked.", ephemeral=True)

    @voice.command(name="unlock")
    @commands.guild_only()
    @is_in_voice_channel()
    @is_channel_owner()
    @audit_log(AuditLogEventType.CHANNEL_UNLOCKED, "User {ctx.author.display_name} ({ctx.author.id}) unlocked channel '{ctx.author.voice.channel.name}' ({ctx.author.voice.channel.id}).")
    async def unlock(self, ctx: Context):
        """
        Unlocks your current temporary voice channel, allowing everyone to join.
        Requires the user to be in and own the channel.
        """
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)
        # Ensure author.voice and author.voice.channel are not None before casting
        if not author.voice or not author.voice.channel:
            return await ctx.send("Error: Could not determine your voice channel.", ephemeral=True)

        voice_channel_obj = cast(discord.VoiceChannel, author.voice.channel)

        # Set `connect` permission to `True` for `@everyone` role.
        await voice_channel_obj.set_permissions(guild.default_role, connect=True)
        await ctx.send("🔓 Channel unlocked.", ephemeral=True)

    @voice.command(name="permit")
    @commands.guild_only()
    @is_in_voice_channel()
    @is_channel_owner()
    @audit_log(AuditLogEventType.CHANNEL_PERMIT, "User {ctx.author.display_name} ({ctx.author.id}) permitted {member.mention} ({member.id}) to join '{ctx.author.voice.channel.name}' ({ctx.author.voice.channel.id}).")
    async def permit(self, ctx: Context, member: discord.Member):
        """
        Permits a specific user to join your locked temporary channel.
        Requires the user to be in and own the channel.

        Args:
            member: The `discord.Member` to permit access to the channel.
        """
        author = cast(discord.Member, ctx.author)
        # Ensure author.voice and author.voice.channel are not None before casting
        if not author.voice or not author.voice.channel:
            return await ctx.send("Error: Could not determine your voice channel.", ephemeral=True)

        voice_channel_obj = cast(discord.VoiceChannel, author.voice.channel)

        # Set `connect` permission to `True` specifically for the target member.
        await voice_channel_obj.set_permissions(member, connect=True)
        await ctx.send(f"✅ {member.mention} can now join your channel.", ephemeral=True)

    @voice.command(name="claim")
    @commands.guild_only()
    @is_in_voice_channel()  # Ensure invoker is in a voice channel
    @audit_log(AuditLogEventType.CHANNEL_CLAIMED, "User {ctx.author.display_name} ({ctx.author.id}) claimed ownership of channel '{channel.name}' ({channel.id}) from old owner ID {old_owner_id}.")
    async def claim(self, ctx: Context):
        """
        Claims ownership of an abandoned or unowned temporary channel.
        Allows a user to take over a temporary channel if its original owner
        is no longer present or if the channel is currently ownerless.
        """
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)
        voice_state = author.voice  # Assured by @is_in_voice_channel()

        # Ensure voice_state and voice_state.channel are not None before casting
        if not voice_state or not voice_state.channel:
            return await ctx.send("Error: Could not determine your voice channel.", ephemeral=True)

        # Already checked by is_in_voice_channel()
        channel = cast(discord.VoiceChannel, voice_state.channel)

        # Retrieve the channel from the database to check if it's a bot-managed temporary channel.
        vc = await self.voice_channel_service.get_voice_channel(channel.id)
        if not vc:
            return await ctx.send("This channel is not a temporary channel managed by VoiceMaster.", ephemeral=True)

        # Check if the channel currently has an owner and if that owner is still in the channel.
        # We also need `vc.owner_id` for logging, which is handled by audit_log decorator.
        # Type guard for the original owner ID
        assert isinstance(vc.owner_id, int)
        old_owner_id = vc.owner_id  # Capture for audit log details
        # Attempt to fetch the Discord member object for the owner
        owner = guild.get_member(vc.owner_id)

        if owner and owner in channel.members:
            # If the owner is found and still in the channel, it cannot be claimed.
            return await ctx.send(f"The owner, {owner.mention}, is still in the channel. You cannot claim it.", ephemeral=True)

        # Update the channel's owner in the database to the commanding user's ID.
        await self.voice_channel_service.update_voice_channel_owner(channel.id, author.id)

        # Grant the new owner management permissions for the channel.
        await channel.set_permissions(author, manage_channels=True, manage_roles=True)

        await ctx.send(f"👑 {author.mention}, you are now the owner of this channel!", ephemeral=True)
        # Audit log is handled by the decorator, which will receive `old_owner_id` from local scope.

    @voice.command(name="name")
    @commands.guild_only()
    @audit_log(AuditLogEventType.USER_DEFAULT_NAME_SET, "User {ctx.author.display_name} ({ctx.author.id}) set default channel name to '{new_name}'.")
    async def name(self, ctx: Context, *, new_name: str):
        """
        Sets a custom default name for the user's future temporary channels.
        If the user currently owns an active temporary channel, it also renames that channel.

        Args:
            new_name: The desired new name for the channel.
        """
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)

        # First, update the user's preferred default channel name in the database.
        await self.voice_channel_service.update_user_channel_name(author.id, new_name)

        # Check if the user currently owns an active temporary channel and is in it.
        vc = await self.voice_channel_service.get_voice_channel_by_owner(author.id)
        if (
            vc and
            author.voice and
            author.voice.channel and
            # Type guard for safety
            isinstance(author.voice.channel, discord.VoiceChannel) and
            # Using helper for comparison
            is_db_value_equal(author.voice.channel.id, vc.channel_id)
        ):
            # Assign to a local variable after casting to help Pylance
            voice_channel_obj = cast(
                discord.VoiceChannel, author.voice.channel)
            old_channel_name = voice_channel_obj.name
            await voice_channel_obj.edit(name=new_name)
            logging.info(
                f"Live channel {voice_channel_obj.id} renamed from '{old_channel_name}' to '{new_name}' by owner {author.id}.")

            # Log the live channel name change separately.
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.LIVE_CHANNEL_NAME_CHANGED,
                user_id=author.id,
                channel_id=voice_channel_obj.id,
                details=f"User {author.display_name} ({author.id}) changed live channel name from '{old_channel_name}' to '{new_name}'."
            )

        await ctx.send(
            f"Your channel name has been set to **{new_name}**. "
            "It will apply to your current (if you own one and are in it) and all future channels.",
            ephemeral=True
        )
        # Audit log for default name set is handled by the decorator.

    @voice.command(name="limit")
    @commands.guild_only()
    @audit_log(AuditLogEventType.USER_DEFAULT_LIMIT_SET, "User {ctx.author.display_name} ({ctx.author.id}) set default channel limit to '{new_limit}'.")
    async def limit(self, ctx: Context, new_limit: int):
        """
        Changes the user limit for the user's future temporary channels.
        If the user currently owns an active temporary channel, it also updates that channel's limit.

        Args:
            new_limit: The desired user limit (0 for unlimited, 1-99 for specific limit).
        """
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)

        # Validate the input limit. Discord channel user limits are between 0 and 99.
        if not (0 <= new_limit <= 99):
            return await ctx.send("Please provide a limit between 0 (unlimited) and 99.", ephemeral=True)

        # First, update the user's preferred default channel limit in the database.
        await self.voice_channel_service.update_user_channel_limit(author.id, new_limit)

        # Check if the user currently owns an active temporary channel and is in it.
        vc = await self.voice_channel_service.get_voice_channel_by_owner(author.id)
        if (
            vc and
            author.voice and
            author.voice.channel and
            # Type guard for safety
            isinstance(author.voice.channel, discord.VoiceChannel) and
            # Using helper for comparison
            is_db_value_equal(author.voice.channel.id, vc.channel_id)
        ):
            # Assign to a local variable after casting to help Pylance
            voice_channel_obj = cast(
                discord.VoiceChannel, author.voice.channel)
            old_limit = voice_channel_obj.user_limit
            await voice_channel_obj.edit(user_limit=new_limit)
            logging.info(
                f"Live channel {voice_channel_obj.id} limit changed from {old_limit} to {new_limit} by owner {author.id}.")

            # Log the live channel limit change separately.
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.LIVE_CHANNEL_LIMIT_CHANGED,
                user_id=author.id,
                channel_id=voice_channel_obj.id,
                details=(
                    f"User {author.display_name} ({author.id}) changed live channel limit "
                    f"from {old_limit} to {new_limit}."
                )
            )

        limit_str = f"{new_limit if new_limit > 0 else 'unlimited'}"
        await ctx.send(
            f"Your channel limit has been set to **{limit_str}**. "
            "It will apply to your current (if you own one and are in it) and all future channels.",
            ephemeral=True
        )
        # Audit log for default limit set is handled by the decorator.

    @voice.command(name="auditlog")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def auditlog(self, ctx: Context, count: int = 10):
        """
        Displays the latest X bot activity logs for the current guild.
        The number of entries can be specified (default is 10, max 50).

        Args:
            count: The number of latest audit log entries to display (1-50).
        """
        guild = ctx.guild
        if not guild:
            return await ctx.send("This command can only be used in a server.", ephemeral=True)

        # Validate the requested number of log entries.
        if not (1 <= count <= 50):
            return await ctx.send("Please provide a count between 1 and 50.", ephemeral=True)

        # Retrieve the latest audit logs from the service.
        logs = await self.audit_log_service.get_latest_logs(guild.id, count)

        if not logs:
            return await ctx.send("No audit log entries found for this guild.", ephemeral=True)

        embed = discord.Embed(
            title=f"Recent VoiceMaster Activity Logs ({len(logs)} entries)",
            color=discord.Color.orange()  # Corrected to discord.Color.orange()
        )
        embed.set_footer(text="Most recent entries first. Times are UTC.")

        for entry in logs:
            # Safely cast Optional types for easier handling and type checking.
            user_id_val: Optional[int] = cast(Optional[int], entry.user_id)
            channel_id_val: Optional[int] = cast(
                Optional[int], entry.channel_id)
            details_val: Optional[str] = cast(Optional[str], entry.details)

            # Resolve user display name/mention.
            user_display: str = "N/A"
            if user_id_val is not None:
                fetched_user = self.bot.get_user(
                    user_id_val)  # Tries cached first
                if fetched_user:
                    user_display = fetched_user.mention  # Use mention for Discord user link
                else:
                    # If user not found in cache, it might be an old user or left guild.
                    # Fallback to fetching directly if really needed, or just show ID.
                    user_display = f"User ID: {user_id_val} (Not found)"

            # Resolve channel display name/mention.
            channel_display: str = "N/A"
            if channel_id_val is not None:
                fetched_channel = self.bot.get_channel(
                    channel_id_val)  # Tries cached first
                if fetched_channel:
                    # Use mention for guild channels if available, or just name/ID.
                    if isinstance(fetched_channel, (discord.VoiceChannel, discord.TextChannel, discord.CategoryChannel, discord.Thread)):
                        channel_display = fetched_channel.mention
                    # Added specific check for DMChannel
                    elif isinstance(fetched_channel, discord.DMChannel):
                        channel_display = f"DM Channel ({fetched_channel.id})"
                    else:
                        # Fallback for other channel types which might not have .name or are unknown
                        # Using getattr with a default to safely get 'name' attribute if it exists
                        channel_name_attr = getattr(
                            fetched_channel, 'name', f"Unknown Channel Type (ID: {channel_id_val})")
                        channel_display = f"Channel '{channel_name_attr}' (ID: {channel_id_val})"
                else:
                    channel_display = f"Channel ID: {channel_id_val} (Not found)"

            # Format timestamp for readability.
            timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

            # Construct the field value for the embed.
            field_value = (
                # Format enum string
                f"**Type**: {entry.event_type.replace('_', ' ').title()}\n"
                f"**User**: {user_display}\n"
                f"**Channel**: {channel_display}\n"
                f"**Details**: {details_val if details_val is not None else 'N/A'}\n"
                f"**Time**: {timestamp_str}"
            )
            # Add each log entry as a separate field in the embed.
            embed.add_field(
                name=f"Log Entry #{entry.id}", value=field_value, inline=False)

        # Send the audit log embed ephemerally
        await ctx.send(embed=embed, ephemeral=True)
        # Audit log is handled by the decorator.


async def setup(bot: commands.Bot):
    """
    The entry point for loading the VoiceCommandsCog into the bot.

    This function is called by Discord.py when loading extensions.
    It ensures that the cog receives the necessary service dependencies
    from the custom bot instance.

    Args:
        bot: The `commands.Bot` instance, which is cast to `VoiceMasterBot`
             to access custom service attributes.
    """
    # Cast the generic commands.Bot to our specific VoiceMasterBot type
    # to access the services that are attached during bot initialization.
    custom_bot = cast(VoiceMasterBot, bot)
    await bot.add_cog(
        VoiceCommandsCog(
            bot=custom_bot,
            guild_service=custom_bot.guild_service,
            voice_channel_service=custom_bot.voice_channel_service,
            audit_log_service=custom_bot.audit_log_service
        )
    )