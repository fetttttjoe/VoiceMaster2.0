import logging
import discord
import asyncio
from discord.ext import commands
from sqlalchemy.ext.asyncio import AsyncSession
from database.database import get_session
from database import crud

class VoiceCommandsCog(commands.Cog, name="Voice Commands"):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def voice(self, ctx: commands.Context):
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
                "`.voice list` - Lists all active temporary channels."
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
    async def setup(self, ctx: commands.Context):
        """Sets up the voice channel creation category and channel."""
        guild = ctx.guild
        if not guild:
            return await ctx.send("This command can only be used in a server.")

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

            async with get_session() as session:
                await crud.create_or_update_guild(session, guild.id, guild.owner_id, category.id, channel.id)

            await ctx.send(f"✅ Setup complete! Users can now join '{channel.name}' to create their own channels.")
        except asyncio.TimeoutError:
            await ctx.send("Setup timed out. Please try again.")
        except Exception as e:
            await ctx.send(f"An error occurred: {e}")
            logging.error(f"Setup error in guild {guild.id}: {e}")

    @voice.group(name="edit", invoke_without_command=True)
    @commands.has_guild_permissions(administrator=True)
    async def edit(self, ctx: commands.Context):
        """Edit the bot's configuration for this server."""
        await ctx.send("Please specify what you want to edit. Use `.voice edit rename` or `.voice edit select`.")

    @edit.command(name="rename")
    @commands.has_guild_permissions(administrator=True)
    async def edit_rename(self, ctx: commands.Context):
        """Rename the existing creation channel and category."""
        guild = ctx.guild
        if not guild:
            return await ctx.send("This command can only be used in a server.")

        async with get_session() as session:
            guild_config = await crud.get_guild(session, guild.id)
            if not guild_config:
                return await ctx.send("The bot has not been set up yet. Run `.voice setup` first.")

        view = discord.ui.View(timeout=180.0)
        rename_channel_btn = discord.ui.Button(label="Rename 'Join' Channel", style=discord.ButtonStyle.primary, emoji="✏️")
        rename_category_btn = discord.ui.Button(label="Rename Category", style=discord.ButtonStyle.primary, emoji="✏️")

        async def rename_channel_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)
            
            await interaction.response.send_message("Please type the new name for the 'Join to Create' channel:", ephemeral=True)
            try:
                msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0)
                if guild_config and isinstance(guild_config.creation_channel_id, int):
                    creation_channel = guild.get_channel(guild_config.creation_channel_id)
                    if creation_channel:
                        await creation_channel.edit(name=msg.content)
                        await msg.reply(f"✅ Channel renamed to **{msg.content}**.", delete_after=10)
                await msg.delete()
            except asyncio.TimeoutError:
                await interaction.followup.send("Rename timed out.", ephemeral=True)

        async def rename_category_callback(interaction: discord.Interaction):
            if interaction.user != ctx.author:
                return await interaction.response.send_message("You cannot interact with this menu.", ephemeral=True)

            await interaction.response.send_message("Please type the new name for the temporary channels category:", ephemeral=True)
            try:
                msg = await self.bot.wait_for('message', check=lambda m: m.author == ctx.author and m.channel == ctx.channel, timeout=60.0)
                if guild_config and isinstance(guild_config.voice_category_id, int):
                    category = guild.get_channel(guild_config.voice_category_id)
                    if category:
                        await category.edit(name=msg.content)
                        await msg.reply(f"✅ Category renamed to **{msg.content}**.", delete_after=10)
                await msg.delete()
            except asyncio.TimeoutError:
                await interaction.followup.send("Rename timed out.", ephemeral=True)

        rename_channel_btn.callback = rename_channel_callback
        rename_category_btn.callback = rename_category_callback
        view.add_item(rename_channel_btn)
        view.add_item(rename_category_btn)
        await ctx.send("Press a button to start renaming:", view=view)

    @edit.command(name="select")
    @commands.has_guild_permissions(administrator=True)
    async def edit_select(self, ctx: commands.Context):
        """Select a different creation channel or category."""
        guild = ctx.guild
        if not guild or not guild.owner_id:
            return await ctx.send("This command can only be used in a server.")

        async with get_session() as session:
            guild_config = await crud.get_guild(session, guild.id)
            if not guild_config:
                return await ctx.send("The bot has not been set up yet. Run `.voice setup` first.")

        view = discord.ui.View(timeout=180.0)
        voice_channels = [c for c in guild.voice_channels if c.category]
        channel_options = [discord.SelectOption(label=c.name, value=str(c.id)) for c in voice_channels]
        channel_select = discord.ui.Select(placeholder="Select a new 'Join to Create' channel...", options=channel_options)

        category_options = [discord.SelectOption(label=cat.name, value=str(cat.id)) for cat in guild.categories]
        category_select = discord.ui.Select(placeholder="Select a new category for temp channels...", options=category_options)

        async def channel_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            if interaction.user != ctx.author or not guild.owner_id:
                return await interaction.followup.send("You cannot interact with this menu.")
            
            async with get_session() as s:
                current_config = await crud.get_guild(s, guild.id)
                if not current_config or not isinstance(current_config.voice_category_id, int):
                    return await interaction.followup.send("Error: Could not find current config.")
                
                new_channel_id = int(channel_select.values[0])
                await crud.create_or_update_guild(s, guild.id, guild.owner_id, current_config.voice_category_id, new_channel_id)
            await interaction.followup.send(f"✅ 'Join to Create' channel updated!")
            view.stop()

        async def category_callback(interaction: discord.Interaction):
            await interaction.response.defer(ephemeral=True)
            if interaction.user != ctx.author or not guild.owner_id:
                return await interaction.followup.send("You cannot interact with this menu.")

            async with get_session() as s:
                current_config = await crud.get_guild(s, guild.id)
                if not current_config or not isinstance(current_config.creation_channel_id, int):
                    return await interaction.followup.send("Error: Could not find current config.")

                new_category_id = int(category_select.values[0])
                await crud.create_or_update_guild(s, guild.id, guild.owner_id, new_category_id, current_config.creation_channel_id)
            await interaction.followup.send(f"✅ Category for temporary channels updated!")
            view.stop()

        channel_select.callback = channel_callback
        category_select.callback = category_callback
        view.add_item(channel_select)
        view.add_item(category_select)
        await ctx.send("Use the dropdowns to select a new channel or category:", view=view)

    @voice.command(name="list")
    @commands.has_guild_permissions(administrator=True)
    async def list_channels(self, ctx: commands.Context):
        """Lists all active temporary voice channels."""
        guild = ctx.guild
        if not guild:
            return await ctx.send("This command can only be used in a server.")

        async with get_session() as session:
            all_channels = await crud.get_all_voice_channels(session)
        
        if not all_channels:
            return await ctx.send("There are no active temporary channels.")

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

    @voice.command(name="lock")
    async def lock(self, ctx: commands.Context):
        """Locks your current voice channel."""
        author = ctx.author
        guild = ctx.guild
        if not isinstance(author, discord.Member) or not guild:
            return await ctx.send("This command can only be used in a server.")

        voice_state = author.voice
        if not voice_state or not voice_state.channel:
            return await ctx.send("You are not in a voice channel.")

        async with get_session() as session:
            vc = await crud.get_voice_channel_by_owner(session, author.id)
            if not vc or voice_state.channel.id != vc.channel_id:
                return await ctx.send("You don't own this voice channel.")
            
            await voice_state.channel.set_permissions(guild.default_role, connect=False)
            await ctx.send("🔒 Channel locked.")

    @voice.command(name="unlock")
    async def unlock(self, ctx: commands.Context):
        """Unlocks your current voice channel."""
        author = ctx.author
        guild = ctx.guild
        if not isinstance(author, discord.Member) or not guild:
            return await ctx.send("This command can only be used in a server.")

        voice_state = author.voice
        if not voice_state or not voice_state.channel:
            return await ctx.send("You are not in a voice channel.")

        async with get_session() as session:
            vc = await crud.get_voice_channel_by_owner(session, author.id)
            if not vc or voice_state.channel.id != vc.channel_id:
                return await ctx.send("You don't own this voice channel.")
            
            await voice_state.channel.set_permissions(guild.default_role, connect=True)
            await ctx.send("🔓 Channel unlocked.")

    @voice.command(name="permit")
    async def permit(self, ctx: commands.Context, member: discord.Member):
        """Permits a user to join your locked channel."""
        author = ctx.author
        if not isinstance(author, discord.Member):
            return await ctx.send("This command can only be used in a server.")
            
        voice_state = author.voice
        if not voice_state or not voice_state.channel:
            return await ctx.send("You are not in a voice channel.")

        async with get_session() as session:
            vc = await crud.get_voice_channel_by_owner(session, author.id)
            if not vc or voice_state.channel.id != vc.channel_id:
                return await ctx.send("You don't own this voice channel.")
            
            await voice_state.channel.set_permissions(member, connect=True)
            await ctx.send(f"✅ {member.mention} can now join your channel.")

    @voice.command(name="claim")
    async def claim(self, ctx: commands.Context):
        """Claims ownership of an abandoned channel."""
        author = ctx.author
        guild = ctx.guild
        if not isinstance(author, discord.Member) or not guild:
            return await ctx.send("This command can only be used in a server.")
            
        voice_state = author.voice
        if not voice_state or not voice_state.channel:
            return await ctx.send("You are not in a voice channel.")
            
        channel = voice_state.channel
        async with get_session() as session:
            vc = await crud.get_voice_channel(session, channel.id)
            if not vc:
                return await ctx.send("This channel is not a temporary channel.")

            assert isinstance(vc.owner_id, int)
            owner = guild.get_member(vc.owner_id)
            if owner and owner in channel.members:
                return await ctx.send(f"The owner, {owner.mention}, is still in the channel.")

            await crud.update_voice_channel_owner(session, channel.id, author.id)
            await channel.set_permissions(author, manage_channels=True, manage_roles=True)
            await ctx.send(f"👑 {author.mention} you are now the owner of this channel!")

    @voice.command(name="name")
    async def name(self, ctx: commands.Context, *, new_name: str):
        """Changes the name of your channel."""
        author = ctx.author
        if not isinstance(author, discord.Member):
            return await ctx.send("This command can only be used in a server.")

        async with get_session() as session:
            await crud.update_user_channel_name(session, author.id, new_name)
            
            vc = await crud.get_voice_channel_by_owner(session, author.id)
            if vc and author.voice and author.voice.channel and author.voice.channel.id == vc.channel_id:
                await author.voice.channel.edit(name=new_name)

            await ctx.send(f"Your channel name has been set to **{new_name}**. It will apply to your current (if you own one) and all future channels.")

    @voice.command(name="limit")
    async def limit(self, ctx: commands.Context, new_limit: int):
        """Changes the user limit of your channel."""
        author = ctx.author
        if not isinstance(author, discord.Member):
            return await ctx.send("This command can only be used in a server.")

        if not (0 <= new_limit <= 99):
            return await ctx.send("Please provide a limit between 0 (unlimited) and 99.")
        
        async with get_session() as session:
            await crud.update_user_channel_limit(session, author.id, new_limit)

            vc = await crud.get_voice_channel_by_owner(session, author.id)
            if vc and author.voice and author.voice.channel and author.voice.channel.id == vc.channel_id:
                await author.voice.channel.edit(user_limit=new_limit)

            await ctx.send(f"Your channel name has been set to **{new_limit if new_limit > 0 else 'unlimited'}**. It will apply to your current (if you own one) and all future channels.")


async def setup(bot: commands.Bot):
    await bot.add_cog(VoiceCommandsCog(bot))
