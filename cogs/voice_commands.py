import logging
from typing import Optional, cast

import discord
from discord import ui
from discord.ext import commands
from discord.ext.commands import Context

from database.models import AuditLogEventType
from interfaces.audit_log_service import IAuditLogService
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from main import VoiceMasterBot
from services.audit_decorator import audit_log
from utils.checks import is_channel_owner, is_in_voice_channel
from utils.db_helpers import is_db_value_equal
from views.setup_view import SetupView
from views.voice_commands_views import ConfigView, RenameView, SelectView


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
        self._bot = bot
        self._guild_service = guild_service
        self._voice_channel_service = voice_channel_service
        self._audit_log_service = audit_log_service
        self._active_views: dict[int, ui.View] = {}

    @commands.hybrid_group(invoke_without_command=True)  # type: ignore
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
            color=discord.Color.blue(),
        )
        embed.set_footer(text=f"Use {ctx.prefix}voice <command> to get started.")

        embed.add_field(
            name="🛠️ Admin Commands",
            value=(
                f"`{ctx.prefix}voice setup` - The first-time setup for the bot.\n"
                f"`{ctx.prefix}voice edit rename` - Rename the creation channel or category.\n"
                f"`{ctx.prefix}voice edit select` - Select a different creation channel or category.\n"
                f"`{ctx.prefix}voice list` - Lists all active temporary channels.\n"
                f"`{ctx.prefix}voice auditlog [count]` - Shows recent bot activity.\n"
                f"`{ctx.prefix}voice config` - Opens an interactive menu for bot settings."
            ),
            inline=False,
        )
        embed.add_field(
            name="👤 User Commands",
            value=(
                f"`{ctx.prefix}voice lock` - Locks your current temporary channel.\n"
                f"`{ctx.prefix}voice unlock` - Unlocks your current temporary channel.\n"
                f"`{ctx.prefix}voice permit @user` - Permits a user to join your current locked temporary channel.\n"
                f"`{ctx.prefix}voice claim` - Claims an empty, ownerless channel.\n"
                f"`{ctx.prefix}voice name <new_name>` - Sets your default channel name.\n"
                f"`{ctx.prefix}voice limit <number>` - Sets your default channel user limit."
            ),
            inline=False,
        )
        await ctx.send(embed=embed)

    @voice.command(name="config")  # type: ignore
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def config(self, ctx: Context):
        if not ctx.guild:
            return

        guild_config = await self._guild_service.get_guild_config(ctx.guild.id)
        if guild_config is None:
            await ctx.send(f"The bot has not been set up yet. Run `{ctx.prefix}voice setup` first.", ephemeral=True)
            return

        cleanup_status = "Enabled" if is_db_value_equal(guild_config.cleanup_on_startup, True) else "Disabled"
        status_icon = "✅" if is_db_value_equal(guild_config.cleanup_on_startup, True) else "❌"

        embed = discord.Embed(
            title=f"VoiceMaster Config for {ctx.guild.name}",
            description="Use the buttons below to manage bot settings for this server.",
            color=discord.Color.orange(),
        )
        embed.add_field(
            name="Automatic Channel Cleanup on Startup",
            value=(f"{status_icon} Status: **{cleanup_status}**\nThis feature automatically deletes empty temporary channels when the bot starts."),
            inline=False,
        )

        view = ConfigView(ctx, guild_config)
        message = await ctx.send(embed=embed, view=view)
        view.message = message

    @voice.command(name="setup")  # type: ignore
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def setup(self, ctx: Context):
        """
        Sets up the voice channel creation category and channel for the first time.
        """
        view = SetupView(ctx)
        await ctx.send("Click the button to begin the setup process.", view=view)

    @voice.group(name="edit", invoke_without_command=True)  # type: ignore
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def edit(self, ctx: Context):
        """
        Group command for editing bot configuration (rename/select channels).
        If no subcommand is given, it prompts the user.
        """
        await ctx.send("Please specify what you want to edit. Use `.voice edit rename` or `.voice edit select`.")

    @edit.command(name="rename")  # type: ignore
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def edit_rename(self, ctx: Context):
        """
        Allows renaming the existing "Join to Create" channel or the temporary channels category.
        Provides interactive buttons for the user to choose what to rename.
        """
        guild = ctx.guild
        if not guild:
            logging.warning(f"Edit rename command invoked outside a guild context by {ctx.author.id}.")
            return await ctx.send("This command can only be used in a server.", ephemeral=True)

        guild_config = await self._guild_service.get_guild_config(guild.id)
        if guild_config is None:
            return await ctx.send("The bot has not been set up yet. Run `.voice setup` first.", ephemeral=True)

        view = RenameView(ctx)
        message = await ctx.send("Press a button to start renaming:", view=view)
        view.message = message

    @edit.command(name="select")  # type: ignore
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
            logging.warning(f"Edit select command invoked outside a guild context by {ctx.author.id}.")
            return await ctx.send("This command can only be used in a server.", ephemeral=True)
        if not guild.owner_id:
            logging.error(f"Guild {guild.id} has no owner_id, cannot proceed with edit select.")
            return await ctx.send("Could not determine the server owner. Cannot update configuration.", ephemeral=True)

        guild_config = await self._guild_service.get_guild_config(guild.id)
        if guild_config is None:
            return await ctx.send("The bot has not been set up yet. Run `.voice setup` first.", ephemeral=True)

        active_channels = await self._guild_service.get_voice_channels_by_guild(guild.id)
        temp_channel_ids = {vc.channel_id for vc in active_channels}

        voice_channels = [c for c in guild.voice_channels if c.category and c.id not in temp_channel_ids]
        if not voice_channels:
            await ctx.send("No non-temporary voice channels with categories found to select from.", ephemeral=True)
            return

        categories = guild.categories
        if not categories:
            await ctx.send("No categories found to select from.", ephemeral=True)
            return

        view = SelectView(ctx, voice_channels, categories)
        message = await ctx.send("Use the dropdowns to select a new channel or category:", view=view, ephemeral=True)
        view.message = message

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
            return await ctx.send("This command can only be used in a server.", ephemeral=True)

        active_channels = await self._guild_service.get_voice_channels_by_guild(guild.id)

        if not active_channels:
            await ctx.send("There are no active temporary channels managed by VoiceMaster in this guild.", ephemeral=True)
            return

        embed = discord.Embed(title="Active Temporary Channels", color=discord.Color.green())
        description_lines: list[str] = []

        for vc in active_channels:
            channel = guild.get_channel(cast(int, vc.channel_id))
            owner = guild.get_member(cast(int, vc.owner_id))

            if channel and owner:
                description_lines.append(f"**{channel.name}** (<#{channel.id}>) - Owned by {owner.mention}")
            elif channel:
                description_lines.append(f"**{channel.name}** (<#{channel.id}>) - Owner not found (ID: {vc.owner_id})")

        embed.description = "\n".join(description_lines) if description_lines else "No active temporary channels found."
        await ctx.send(embed=embed)

    @voice.command(name="lock")
    @commands.guild_only()
    @is_in_voice_channel()
    @is_channel_owner()
    @audit_log(
        AuditLogEventType.CHANNEL_LOCKED,
        "User {ctx.author.display_name} ({ctx.author.id}) locked channel "
        "'{ctx.author.voice.channel.name}' ({ctx.author.voice.channel.id}).",
    )
    async def lock(self, ctx: Context):
        """
        Locks your current temporary voice channel, preventing others from joining.
        Requires the user to be in and own the channel.
        """
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)
        if not author.voice or not author.voice.channel:
            return await ctx.send("Error: Could not determine your voice channel.", ephemeral=True)

        voice_channel_obj = cast(discord.VoiceChannel, author.voice.channel)

        await voice_channel_obj.set_permissions(guild.default_role, connect=False)
        await ctx.send("🔒 Channel locked.", ephemeral=True)

    @voice.command(name="unlock")
    @commands.guild_only()
    @is_in_voice_channel()
    @is_channel_owner()
    @audit_log(
        AuditLogEventType.CHANNEL_UNLOCKED,
        "User {ctx.author.display_name} ({ctx.author.id}) unlocked channel "
        "'{ctx.author.voice.channel.name}' ({ctx.author.voice.channel.id}).",
    )
    async def unlock(self, ctx: Context):
        """
        Unlocks your current temporary voice channel, allowing everyone to join.
        Requires the user to be in and own the channel.
        """
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)
        if not author.voice or not author.voice.channel:
            return await ctx.send("Error: Could not determine your voice channel.", ephemeral=True)

        voice_channel_obj = cast(discord.VoiceChannel, author.voice.channel)

        await voice_channel_obj.set_permissions(guild.default_role, connect=True)
        await ctx.send("🔓 Channel unlocked.", ephemeral=True)

    @voice.command(name="permit")
    @commands.guild_only()
    @is_in_voice_channel()
    @is_channel_owner()
    @audit_log(
        AuditLogEventType.CHANNEL_PERMIT,
        "User {ctx.author.display_name} ({ctx.author.id}) permitted {member.mention} "
        "({member.id}) to join '{ctx.author.voice.channel.name}' ({ctx.author.voice.channel.id}).",
    )
    async def permit(self, ctx: Context, member: discord.Member):
        """
        Permits a specific user to join your locked temporary channel.
        Requires the user to be in and own the channel.

        Args:
            member: The `discord.Member` to permit access to the channel.
        """
        author = cast(discord.Member, ctx.author)
        if not author.voice or not author.voice.channel:
            return await ctx.send("Error: Could not determine your voice channel.", ephemeral=True)

        voice_channel_obj = cast(discord.VoiceChannel, author.voice.channel)

        await voice_channel_obj.set_permissions(member, connect=True)
        await ctx.send(f"✅ {member.mention} can now join your channel.", ephemeral=True)

    @voice.command(name="claim")
    @commands.guild_only()
    @is_in_voice_channel()
    @audit_log(
        AuditLogEventType.CHANNEL_CLAIMED,
        "User {ctx.author.display_name} ({ctx.author.id}) claimed ownership of channel "
        "'{channel.name}' ({channel.id}) from old owner ID {old_owner_id}.",
    )
    async def claim(self, ctx: Context):
        """
        Claims ownership of an abandoned or unowned temporary channel.
        Allows a user to take over a temporary channel if its original owner
        is no longer present or if the channel is currently ownerless.
        """
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)
        voice_state = author.voice

        if not voice_state or not voice_state.channel:
            return await ctx.send("Error: Could not determine your voice channel.", ephemeral=True)

        channel = cast(discord.VoiceChannel, voice_state.channel)

        vc = await self._voice_channel_service.get_voice_channel(channel.id)
        if vc is None:
            return await ctx.send("This channel is not a temporary channel managed by VoiceMaster.", ephemeral=True)

        assert isinstance(vc.owner_id, int)
        owner = guild.get_member(vc.owner_id)

        if owner and owner in channel.members:
            return await ctx.send(f"The owner, {owner.mention}, is still in the channel. You cannot claim it.", ephemeral=True)

        await self._voice_channel_service.update_voice_channel_owner(channel.id, author.id)

        await channel.set_permissions(author, manage_channels=True, manage_roles=True)

        await ctx.send(f"👑 {author.mention}, you are now the owner of this channel!", ephemeral=True)

    @voice.command(name="name")
    @commands.guild_only()
    @audit_log(
        AuditLogEventType.USER_DEFAULT_NAME_SET,
        "User {ctx.author.display_name} ({ctx.author.id}) set default channel name to "
        "'{new_name}'.",
    )
    async def name(self, ctx: Context, *, new_name: str):
        """
        Sets a custom default name for the user's future temporary channels.
        If the user currently owns an active temporary channel, it also renames that channel.

        Args:
            new_name: The desired new name for the channel.
        """

        if not (2 <= len(new_name) <= 100):
            return await ctx.send("Please provide a name between 2 and 100 characters.", ephemeral=True)

        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)

        await self._voice_channel_service.update_user_channel_name(author.id, new_name)

        vc = await self._voice_channel_service.get_voice_channel_by_owner(author.id)
        if (
            vc
            and author.voice
            and author.voice.channel
            and
            isinstance(author.voice.channel, discord.VoiceChannel)
            and
            is_db_value_equal(author.voice.channel.id, vc.channel_id)
        ):
            voice_channel_obj = cast(discord.VoiceChannel, author.voice.channel)
            old_channel_name = voice_channel_obj.name
            await voice_channel_obj.edit(name=new_name)
            logging.info(f"Live channel {voice_channel_obj.id} renamed from '{old_channel_name}' to '{new_name}' by owner {author.id}.")

            await self._audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.LIVE_CHANNEL_NAME_CHANGED,
                user_id=author.id,
                channel_id=voice_channel_obj.id,
                details=f"User {author.display_name} ({author.id}) changed live channel name from '{old_channel_name}' to '{new_name}'.",
            )

        await ctx.send(
            f"Your channel name has been set to **{new_name}**. It will apply to your current (if you own one and are in it) and all future channels.",
            ephemeral=True,
        )

    @voice.command(name="limit")
    @commands.guild_only()
    @audit_log(
        AuditLogEventType.USER_DEFAULT_LIMIT_SET,
        "User {ctx.author.display_name} ({ctx.author.id}) set default channel limit to "
        "'{new_limit}'.",
    )
    async def limit(self, ctx: Context, new_limit: int):
        """
        Changes the user limit for the user's future temporary channels.
        If the user currently owns an active temporary channel, it also updates that channel's limit.

        Args:
            new_limit: The desired user limit (0 for unlimited, 1-99 for specific limit).
        """
        author = cast(discord.Member, ctx.author)
        guild = cast(discord.Guild, ctx.guild)

        if not (0 <= new_limit <= 99):
            return await ctx.send("Please provide a limit between 0 (unlimited) and 99.", ephemeral=True)

        await self._voice_channel_service.update_user_channel_limit(author.id, new_limit)

        vc = await self._voice_channel_service.get_voice_channel_by_owner(author.id)
        if (
            vc
            and author.voice
            and author.voice.channel
            and
            isinstance(author.voice.channel, discord.VoiceChannel)
            and
            is_db_value_equal(author.voice.channel.id, vc.channel_id)
        ):
            voice_channel_obj = cast(discord.VoiceChannel, author.voice.channel)
            old_limit = voice_channel_obj.user_limit
            await voice_channel_obj.edit(user_limit=new_limit)
            logging.info(f"Live channel {voice_channel_obj.id} limit changed from {old_limit} to {new_limit} by owner {author.id}.")

            await self._audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.LIVE_CHANNEL_LIMIT_CHANGED,
                user_id=author.id,
                channel_id=voice_channel_obj.id,
                details=(f"User {author.display_name} ({author.id}) changed live channel limit from {old_limit} to {new_limit}."),
            )

        limit_str = f"{new_limit if new_limit > 0 else 'unlimited'}"
        await ctx.send(
            f"Your channel limit has been set to **{limit_str}**. It will apply to your current (if you own one and are in it) and all future channels.",
            ephemeral=True,
        )

    @voice.command(name="auditlog")  # type: ignore
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

        if not (1 <= count <= 50):
            return await ctx.send("Please provide a count between 1 and 50.", ephemeral=True)

        logs = await self._audit_log_service.get_latest_logs(guild.id, count)

        if not logs:
            return await ctx.send("No audit log entries found for this guild.", ephemeral=True)

        embed = discord.Embed(
            title=f"Recent VoiceMaster Activity Logs ({len(logs)} entries)",
            color=discord.Color.orange(),
        )
        embed.set_footer(text="Most recent entries first. Times are UTC.")

        for entry in logs:
            user_id_val: Optional[int] = cast(Optional[int], entry.user_id)
            channel_id_val: Optional[int] = cast(Optional[int], entry.channel_id)
            details_val: Optional[str] = cast(Optional[str], entry.details)

            user_display: str = "N/A"
            if user_id_val is not None:
                fetched_user = self._bot.get_user(user_id_val)
                if fetched_user:
                    user_display = fetched_user.mention
                else:
                    user_display = f"User ID: {user_id_val} (Not found)"

            channel_display: str = "N/A"
            if channel_id_val is not None:
                fetched_channel = self._bot.get_channel(channel_id_val)
                if fetched_channel:
                    if isinstance(
                        fetched_channel,
                        (discord.VoiceChannel, discord.TextChannel, discord.CategoryChannel, discord.Thread),
                    ):
                        channel_display = fetched_channel.mention
                    elif isinstance(fetched_channel, discord.DMChannel):
                        channel_display = f"DM Channel ({fetched_channel.id})"
                    else:
                        channel_name_attr = getattr(fetched_channel, "name", f"Unknown Channel Type (ID: {channel_id_val})")
                        channel_display = f"Channel '{channel_name_attr}' (ID: {channel_id_val})"
                else:
                    channel_display = f"Channel ID: {channel_id_val} (Not found)"

            timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

            field_value = (
                f"**Type**: {entry.event_type.replace('_', ' ').title()}\n"
                f"**User**: {user_display}\n"
                f"**Channel**: {channel_display}\n"
                f"**Details**: {details_val if details_val is not None else 'N/A'}\n"
                f"**Time**: {timestamp_str}"
            )
            embed.add_field(name=f"Log Entry #{entry.id}", value=field_value, inline=False)

        await ctx.send(embed=embed, ephemeral=True)


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
    custom_bot = cast(VoiceMasterBot, bot)
    await bot.add_cog(
        VoiceCommandsCog(
            bot=custom_bot,
            guild_service=custom_bot.guild_service,
            voice_channel_service=custom_bot.voice_channel_service,
            audit_log_service=custom_bot.audit_log_service,
        )
    )

