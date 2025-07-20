import logging
import discord
import asyncio
from discord import ui
from discord.ext import commands
from discord.ext.commands import Context
from typing import Optional, Union, cast

from database.models import AuditLogEventType
from services.audit_decorator import audit_log

# Abstractions
from interfaces.guild_service import IGuildService
from interfaces.voice_channel_service import IVoiceChannelService
from interfaces.audit_log_service import IAuditLogService
from main import VoiceMasterBot # Import your custom bot class

class VoiceCommandsCog(commands.Cog):
    def __init__(
        self,
        bot: VoiceMasterBot,
        guild_service: IGuildService,
        voice_channel_service: IVoiceChannelService,
        audit_log_service: IAuditLogService,
    ):
        self.bot = bot
        self.guild_service = guild_service
        self.voice_channel_service = voice_channel_service
        self.audit_log_service = audit_log_service

    @commands.hybrid_group(invoke_without_command=True)
    async def voice(self, ctx: Context):
        """Displays a custom help embed for voice commands."""
        embed = discord.Embed(
            title="🎧 VoiceMaster Commands",
            description="Here are all the commands to manage your temporary voice channels.",
            color=discord.Color.blue()
        )
        embed.set_footer(text="Use .voice <command> to get started.")
        
        embed.add_field(
            name="🛠️ Admin Commands",
            value=(
                "`.voice setup` - The first-time setup for the bot.\n"
                "`.voice edit rename` - Rename the creation channel or category.\n"
                "`.voice edit select` - Select a different creation channel or category.\n"
                "`.voice list` - Lists all active temporary channels.\n"
                "`.voice auditlog [count]` - Shows recent bot activity."
            ),
            inline=False
        )
        embed.add_field(
            name="👤 User Commands",
            value=(
                "`.voice lock` - Locks your channel so nobody can join.\n"
                "`.voice unlock` - Unlocks your channel for everyone.\n"
                "`.voice permit @user` - Allows a specific user to join your locked channel.\n"
                "`.voice claim` - Claims an empty, ownerless channel.\n"
                "`.voice name <new_name>` - Sets a custom name for your channel.\n"
                "`.voice limit <number>` - Sets a user limit for your channel (0 for none)."
            ),
            inline=False
        )
        await ctx.send(embed=embed)

    @voice.command(name="setup")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def setup(self, ctx: Context):
        """Sets up the voice channel creation category and channel."""
        guild = ctx.guild
        if not guild:
            return

        def check(m: discord.Message) -> bool:
            return m.author == ctx.author and m.channel == ctx.channel

        await ctx.send("Enter the name for the new **category** where temporary channels will be created:")
        try:
            category_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            category = await guild.create_category(name=category_msg.content)

            await ctx.send("Now, enter the name for the **voice channel** users will join to create their own (e.g., 'Join to Create'):")
            channel_msg = await self.bot.wait_for('message', check=check, timeout=60.0)
            channel = await guild.create_voice_channel(name=channel_msg.content, category=category)

            if not guild.owner_id:
                 return await ctx.send("Could not determine the server owner.")

            await self.guild_service.create_or_update_guild(guild.id, guild.owner_id, category.id, channel.id)
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.BOT_SETUP,
                user_id=ctx.author.id,
                details=f"Bot setup complete. Category: '{category.name}' ({category.id}), Creation Channel: '{channel.name}' ({channel.id})."
            )

            await ctx.send(f"✅ Setup complete! Users can now join '{channel.name}' to create their own channels.")
        except asyncio.TimeoutError:
            await ctx.send("Setup timed out. Please try again.")
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.SETUP_TIMED_OUT,
                user_id=ctx.author.id,
                details="Bot setup timed out."
            )
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            logging.error(f"Setup error in guild {guild.id}: {e}")
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
        """Edit the bot's configuration for this server."""
        await ctx.send("Please specify what you want to edit. Use `.voice edit rename` or `.voice edit select`.")

    @edit.command(name="rename")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def edit_rename(self, ctx: Context):
        """Rename the existing creation channel and category."""
        guild = ctx.guild
        if not guild:
            return

        guild_config = await self.guild_service.get_guild_config(guild.id)
        if not guild_config:
            return await ctx.send("The bot has not been set up yet. Run `.voice setup` first.")

        view = ui.View(timeout=180.0)
        rename_channel_btn = ui.Button(label="Rename 'Join' Channel", style=discord.ButtonStyle.primary, emoji="✏️")
        rename_category_btn = ui.Button(label="Rename Category", style=discord.ButtonStyle.primary, emoji="✏️")

        async def rename_channel_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            
            await interaction.response.send_message("Please type the new name for the 'Join to Create' channel:", ephemeral=True)
            try:
                msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0)
                if guild_config and isinstance(guild_config.creation_channel_id, int):
                    creation_channel = guild.get_channel(guild_config.creation_channel_id)
                    if creation_channel:
                        old_name = creation_channel.name
                        await creation_channel.edit(name=msg.content)
                        await msg.reply(f"✅ Channel renamed to **{msg.content}**.", delete_after=10)
                        await self.audit_log_service.log_event(
                            guild_id=guild.id,
                            event_type=AuditLogEventType.CHANNEL_RENAMED,
                            user_id=ctx.author.id,
                            channel_id=creation_channel.id,
                            details=f"Creation channel renamed from '{old_name}' to '{msg.content}'."
                        )
                await msg.delete()
            except asyncio.TimeoutError:
                await interaction.followup.send("Rename timed out.", ephemeral=True)
                await self.audit_log_service.log_event(
                    guild_id=guild.id,
                    event_type=AuditLogEventType.CHANNEL_RENAME_TIMED_OUT,
                    user_id=ctx.author.id,
                    details="Renaming 'Join' channel timed out."
                )
            except Exception as e:
                logging.error(f"Error renaming channel in guild {guild.id}: {e}")
                await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
                await self.audit_log_service.log_event(
                    guild_id=guild.id,
                    event_type=AuditLogEventType.CHANNEL_RENAME_ERROR,
                    user_id=ctx.author.id,
                    details=f"Error renaming 'Join' channel: {e}"
                )

        async def rename_category_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)

            await interaction.response.send_message("Please type the new name for the temporary channels category:", ephemeral=True)
            try:
                msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0)
                if guild_config and isinstance(guild_config.voice_category_id, int):
                    category = guild.get_channel(guild_config.voice_category_id)
                    if category:
                        old_name = category.name
                        await category.edit(name=msg.content)
                        await msg.reply(f"✅ Category renamed to **{msg.content}**.", delete_after=10)
                        await self.audit_log_service.log_event(
                            guild_id=guild.id,
                            event_type=AuditLogEventType.CATEGORY_RENAMED,
                            user_id=ctx.author.id,
                            channel_id=category.id,
                            details=f"Category renamed from '{old_name}' to '{msg.content}'."
                        )
                await msg.delete()
            except asyncio.TimeoutError:
                await interaction.followup.send("Rename timed out.", ephemeral=True)
                await self.audit_log_service.log_event(
                    guild_id=guild.id,
                    event_type=AuditLogEventType.CATEGORY_RENAME_TIMED_OUT,
                    user_id=ctx.author.id,
                    details="Renaming category timed out."
                )
            except Exception as e:
                logging.error(f"Error renaming category in guild {guild.id}: {e}")
                await interaction.followup.send(f"An error occurred: {e}", ephemeral=True)
                await self.audit_log_service.log_event(
                    guild_id=guild.id,
                    event_type=AuditLogEventType.CATEGORY_RENAME_ERROR,
                    user_id=ctx.author.id,
                    details=f"Error renaming category: {e}"
                )

        rename_channel_btn.callback = rename_channel_callback
        rename_category_btn.callback = rename_category_callback
        view.add_item(rename_channel_btn)
        view.add_item(rename_category_btn)
        await ctx.send("Press a button to start renaming:", view=view)

    @edit.command(name="select")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def edit_select(self, ctx: Context):
        """Select a different creation channel or category."""
        guild = ctx.guild
        if not guild or not guild.owner_id:
            return

        guild_config = await self.guild_service.get_guild_config(guild.id)
        if not guild_config:
            return await ctx.send("The bot has not been set up yet. Run `.voice setup` first.")

        view = ui.View(timeout=180.0)
        voice_channels = [c for c in guild.voice_channels if c.category]
        channel_options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in voice_channels]
        channel_select = ui.Select(placeholder="Select a new 'Join to Create' channel...", options=channel_options)

        category_options = [discord.SelectOption(label=cat.name, value=str(cat.id)) for cat in guild.categories]
        category_select = ui.Select(placeholder="Select a new category for temp channels...", options=category_options)

        async def channel_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            if interaction.user != ctx.author or not guild.owner_id:
                return await interaction.followup.send("You cannot interact with this menu.")
            
            current_config = await self.guild_service.get_guild_config(guild.id)
            if not current_config or not isinstance(current_config.voice_category_id, int):
                return await interaction.followup.send("Error: Could not find current config.")
            
            old_channel_id = current_config.creation_channel_id
            new_channel_id = int(channel_select.values[0])
            await self.guild_service.create_or_update_guild(guild.id, guild.owner_id, current_config.voice_category_id, new_channel_id)
            await interaction.followup.send(f"✅ 'Join to Create' channel updated!")
            
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.CREATION_CHANNEL_CHANGED,
                user_id=ctx.author.id,
                channel_id=new_channel_id,
                details=f"'Join to Create' channel changed from {old_channel_id} to {new_channel_id}."
            )
            view.stop()

        async def category_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            if interaction.user != ctx.author or not guild.owner_id:
                return await interaction.followup.send("You cannot interact with this menu.")

            current_config = await self.guild_service.get_guild_config(guild.id)
            if not current_config or not isinstance(current_config.creation_channel_id, int):
                return await interaction.followup.send("Error: Could not find current config.")

            old_category_id = current_config.voice_category_id
            new_category_id = int(category_select.values[0])
            await self.guild_service.create_or_update_guild(guild.id, guild.owner_id, new_category_id, current_config.creation_channel_id)
            await interaction.followup.send(f"✅ Category for temporary channels updated!")
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.VOICE_CATEGORY_CHANGED,
                user_id=ctx.author.id,
                channel_id=new_category_id,
                details=f"Voice category changed from {old_category_id} to {new_category_id}."
            )
            view.stop()

        channel_select.callback = channel_callback
        category_select.callback = category_callback
        view.add_item(channel_select)
        view.add_item(category_select)
        await ctx.send("Use the dropdowns to select a new channel or category:", view=view)

    @voice.command(name="list")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def list_channels(self, ctx: Context):
        """Lists all active temporary voice channels."""
        guild = ctx.guild
        if not guild:
            return

        all_channels = await self.guild_service.get_all_voice_channels()
        
        if not all_channels:
            await ctx.send("There are no active temporary channels.")
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.LIST_CHANNELS,
                user_id=ctx.author.id,
                details="Attempted to list active channels, none found."
            )
            return

        embed = discord.Embed(title="Active Temporary Channels", color=discord.Color.green())
        description = ""
        for vc in all_channels:
            assert isinstance(vc.channel_id, int) and isinstance(vc.owner_id, int)
            channel = guild.get_channel(vc.channel_id)
            owner = guild.get_member(vc.owner_id)
            if channel and owner:
                description += f"**{channel.name}** - Owned by {owner.mention}\n"
            elif channel:
                description += f"**{channel.name}** - Owner not found (ID: {vc.owner_id})\n"
        
        embed.description = description or "No active temporary channels found."
        await ctx.send(embed=embed)
        await self.audit_log_service.log_event(
            guild_id=guild.id,
            event_type=AuditLogEventType.LIST_CHANNELS,
            user_id=ctx.author.id,
            details=f"Listed {len(all_channels)} active temporary channels."
        )

    @voice.command(name="lock")
    @commands.guild_only()
    @audit_log(AuditLogEventType.CHANNEL_LOCKED, "User {ctx.author.display_name} locked channel '{ctx.author.voice.channel.name}'.")
    async def lock(self, ctx: Context):
        """Locks your current voice channel."""
        author = ctx.author
        guild = ctx.guild
        if not isinstance(author, discord.Member) or not guild:
            return

        voice_state = author.voice
        if not voice_state or not isinstance(voice_state.channel, discord.VoiceChannel):
            return await ctx.send("You are not in a voice channel.")

        vc = await self.voice_channel_service.get_voice_channel_by_owner(author.id)
        if not vc or voice_state.channel.id != vc.channel_id:
            return await ctx.send("You don't own this voice channel.")
        
        await voice_state.channel.set_permissions(guild.default_role, connect=False)
        await ctx.send("🔒 Channel locked.")

    @voice.command(name="unlock")
    @commands.guild_only()
    @audit_log(AuditLogEventType.CHANNEL_UNLOCKED, "User {ctx.author.display_name} unlocked channel '{ctx.author.voice.channel.name}'.")
    async def unlock(self, ctx: Context):
        """Unlocks your current voice channel."""
        author = ctx.author
        guild = ctx.guild
        if not isinstance(author, discord.Member) or not guild:
            return

        voice_state = author.voice
        if not voice_state or not isinstance(voice_state.channel, discord.VoiceChannel):
            return await ctx.send("You are not in a voice channel.")

        vc = await self.voice_channel_service.get_voice_channel_by_owner(author.id)
        if not vc or voice_state.channel.id != vc.channel_id:
            return await ctx.send("You don't own this voice channel.")
        
        await voice_state.channel.set_permissions(guild.default_role, connect=True)
        await ctx.send("🔓 Channel unlocked.")

    @voice.command(name="permit")
    @commands.guild_only()
    @audit_log(AuditLogEventType.CHANNEL_PERMIT, "User {ctx.author.display_name} permitted {member.mention} to join '{ctx.author.voice.channel.name}'.")
    async def permit(self, ctx: Context, member: discord.Member):
        """Permits a user to join your locked channel."""
        author = ctx.author
        if not isinstance(author, discord.Member):
            return
            
        voice_state = author.voice
        if not voice_state or not isinstance(voice_state.channel, discord.VoiceChannel):
            return await ctx.send("You are not in a voice channel.")

        vc = await self.voice_channel_service.get_voice_channel_by_owner(author.id)
        if not vc or voice_state.channel.id != vc.channel_id:
            return await ctx.send("You don't own this voice channel.")
        
        await voice_state.channel.set_permissions(member, connect=True)
        await ctx.send(f"✅ {member.mention} can now join your channel.")

    @voice.command(name="claim")
    @commands.guild_only()
    async def claim(self, ctx: Context):
        """Claims ownership of an abandoned channel."""
        author = ctx.author
        guild = ctx.guild
        if not isinstance(author, discord.Member) or not guild:
            return
            
        voice_state = author.voice
        if not voice_state or not isinstance(voice_state.channel, discord.VoiceChannel):
            return await ctx.send("You are not in a voice channel.")
            
        channel = voice_state.channel
        vc = await self.voice_channel_service.get_voice_channel(channel.id)
        if not vc:
            return await ctx.send("This channel is not a temporary channel.")

        assert isinstance(vc.owner_id, int)
        owner = guild.get_member(vc.owner_id)
        if owner and owner in channel.members:
            return await ctx.send(f"The owner, {owner.mention}, is still in the channel.")

        old_owner_id = vc.owner_id
        await self.voice_channel_service.update_voice_channel_owner(channel.id, author.id)
        await channel.set_permissions(author, manage_channels=True, manage_roles=True)
        await ctx.send(f"👑 {author.mention} you are now the owner of this channel!")
        await self.audit_log_service.log_event(
            guild_id=guild.id,
            event_type=AuditLogEventType.CHANNEL_CLAIMED,
            user_id=author.id,
            channel_id=channel.id,
            details=f"User {author.display_name} claimed ownership of channel '{channel.name}' from old owner ID {old_owner_id}."
        )

    @voice.command(name="name")
    @commands.guild_only()
    async def name(self, ctx: Context, *, new_name: str):
        """Changes the name of your channel."""
        author = ctx.author
        guild = ctx.guild
        if not isinstance(author, discord.Member) or not guild:
            return

        await self.voice_channel_service.update_user_channel_name(author.id, new_name)
        
        vc = await self.voice_channel_service.get_voice_channel_by_owner(author.id)
        if vc and author.voice and author.voice.channel and author.voice.channel.id == vc.channel_id:
            old_channel_name = author.voice.channel.name
            await author.voice.channel.edit(name=new_name)
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.LIVE_CHANNEL_NAME_CHANGED,
                user_id=author.id,
                channel_id=author.voice.channel.id,
                details=f"User {author.display_name} changed live channel name from '{old_channel_name}' to '{new_name}'."
            )

        await ctx.send(f"Your channel name has been set to **{new_name}**. It will apply to your current (if you own one) and all future channels.")
        await self.audit_log_service.log_event(
            guild_id=guild.id,
            event_type=AuditLogEventType.USER_DEFAULT_NAME_SET,
            user_id=author.id,
            details=f"User {author.display_name} set default channel name to '{new_name}'."
        )

    @voice.command(name="limit")
    @commands.guild_only()
    async def limit(self, ctx: Context, new_limit: int):
        """Changes the user limit of your channel."""
        author = ctx.author
        guild = ctx.guild
        if not isinstance(author, discord.Member) or not guild:
            return

        if not (0 <= new_limit <= 99):
            return await ctx.send("Please provide a limit between 0 (unlimited) and 99.")
        
        await self.voice_channel_service.update_user_channel_limit(author.id, new_limit)

        vc = await self.voice_channel_service.get_voice_channel_by_owner(author.id)
        if vc and author.voice and author.voice.channel and isinstance(author.voice.channel, discord.VoiceChannel) and author.voice.channel.id == vc.channel_id:
            old_limit = author.voice.channel.user_limit
            await author.voice.channel.edit(user_limit=new_limit)
            await self.audit_log_service.log_event(
                guild_id=guild.id,
                event_type=AuditLogEventType.LIVE_CHANNEL_LIMIT_CHANGED,
                user_id=author.id,
                channel_id=author.voice.channel.id,
                details=f"User {author.display_name} changed live channel limit from {old_limit} to {new_limit}."
            )

        limit_str = f"{new_limit if new_limit > 0 else 'unlimited'}"
        await ctx.send(f"Your channel limit has been set to **{limit_str}**. It will apply to your current (if you own one) and all future channels.")
        await self.audit_log_service.log_event(
            guild_id=guild.id,
            event_type=AuditLogEventType.USER_DEFAULT_LIMIT_SET,
            user_id=author.id,
            details=f"User {author.display_name} set default channel limit to {new_limit}."
        )

    @voice.command(name="auditlog")
    @commands.has_guild_permissions(administrator=True)
    @commands.guild_only()
    async def auditlog(self, ctx: Context, count: int = 10):
        """
        Displays the latest X bot activity logs.
        Adjustable via settings (default is 10).
        """
        if not ctx.guild:
            return

        if not (1 <= count <= 50):
            return await ctx.send("Please provide a count between 1 and 50.")

        logs = await self.audit_log_service.get_latest_logs(ctx.guild.id, count)
        
        if not logs:
            return await ctx.send("No audit log entries found for this guild.")

        embed = discord.Embed(
            title=f"Recent VoiceMaster Activity Logs ({len(logs)} entries)",
            color=discord.Color.orange()
        )
        embed.set_footer(text="Most recent entries first.")

        for entry in logs:
            user_id_val: Optional[int] = cast(Optional[int], entry.user_id)
            channel_id_val: Optional[int] = cast(Optional[int], entry.channel_id)
            details_val: Optional[str] = cast(Optional[str], entry.details)

            user_obj: Union[discord.User, str] = "N/A"
            if user_id_val is not None:
                fetched_user = self.bot.get_user(user_id_val)
                if fetched_user:
                    user_obj = fetched_user
                else:
                    user_obj = f"User ID: {user_id_val} (Not found)"
            
            channel_obj: Union[discord.abc.GuildChannel, discord.Thread, discord.abc.PrivateChannel, str] = "N/A"
            if channel_id_val is not None:
                fetched_channel = self.bot.get_channel(channel_id_val)
                if fetched_channel:
                    channel_obj = fetched_channel
                else:
                    channel_obj = f"Channel ID: {channel_id_val} (Not found)"
            
            user_display = user_obj.mention if isinstance(user_obj, discord.User) else str(user_obj)
            
            if isinstance(channel_obj, (discord.VoiceChannel, discord.TextChannel, discord.CategoryChannel, discord.Thread)):
                channel_display = channel_obj.mention
            elif isinstance(channel_obj, discord.abc.PrivateChannel):
                channel_display = f"DM Channel ({channel_obj.id})"
            else:
                channel_display = str(channel_obj)

            timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M:%S UTC")

            field_value = (
                f"**Type**: {entry.event_type}\n"
                f"**User**: {user_display}\n"
                f"**Channel**: {channel_display}\n"
                f"**Details**: {details_val if details_val is not None else 'N/A'}\n"
                f"**Time**: {timestamp_str}"
            )
            embed.add_field(name=f"Log Entry #{entry.id}", value=field_value, inline=False)
        
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    """The entry point for loading the cog."""
    custom_bot = cast(VoiceMasterBot, bot)
    await bot.add_cog(
        VoiceCommandsCog(
            bot=custom_bot,
            guild_service=custom_bot.guild_service,
            voice_channel_service=custom_bot.voice_channel_service,
            audit_log_service=custom_bot.audit_log_service
        )
    )
