# utils/embed_helpers.py
from typing import Optional

import discord


def create_embed(
    title: str,
    description: str = "",
    color: discord.Color = discord.Color.blue(),
    footer: Optional[str] = None,
) -> discord.Embed:
    """
    Creates a standardized Discord embed.

    Args:
        title: The title of the embed.
        description: The description of the embed.
        color: The color of the embed.
        footer: The footer text of the embed.

    Returns:
        A discord.Embed object.
    """
    embed = discord.Embed(title=title, description=description, color=color)
    if footer:
        embed.set_footer(text=footer)
    return embed
