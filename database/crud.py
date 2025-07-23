from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from . import models
from sqlalchemy import desc
from typing import Optional
from .models import AuditLogEventType

# --- Guild (Server) CRUD Operations ---

async def get_guild(db: AsyncSession, guild_id: int):
    """
    Retrieves a Guild configuration from the database by its ID.

    Args:
        db: The asynchronous database session.
        guild_id: The unique ID of the guild.

    Returns:
        The Guild model object if found, otherwise None.
    """
    result = await db.execute(select(models.Guild).where(models.Guild.id == guild_id))
    return result.scalar_one_or_none()

async def create_or_update_guild(
    db: AsyncSession,
    guild_id: int,
    owner_id: int,
    category_id: int,
    channel_id: int
):
    """
    Creates a new Guild entry or updates an existing one in the database.

    If a guild with the given `guild_id` already exists, its `owner_id`,
    `voice_category_id`, and `creation_channel_id` are updated.
    Otherwise, a new Guild entry is created.

    Args:
        db: The asynchronous database session.
        guild_id: The unique ID of the guild.
        owner_id: The ID of the guild owner.
        category_id: The ID of the voice channel category for temporary channels.
        channel_id: The ID of the "join to create" voice channel.
    """
    guild = await get_guild(db, guild_id)
    if guild:
        # Update existing guild configuration
        stmt = (
            update(models.Guild)
            .where(models.Guild.id == guild_id)
            .values(owner_id=owner_id, voice_category_id=category_id, creation_channel_id=channel_id)
        )
        await db.execute(stmt)
    else:
        # Create a new guild entry
        db.add(models.Guild(id=guild_id, owner_id=owner_id, voice_category_id=category_id, creation_channel_id=channel_id))
    await db.commit() # Commit the changes to the database

# --- Voice Channel CRUD Operations ---

async def get_voice_channel_by_owner(db: AsyncSession, owner_id: int):
    """
    Retrieves a VoiceChannel entry by its owner's ID.

    This is typically used to find a temporary voice channel owned by a specific user.

    Args:
        db: The asynchronous database session.
        owner_id: The ID of the user who owns the voice channel.

    Returns:
        The VoiceChannel model object if found, otherwise None.
    """
    result = await db.execute(select(models.VoiceChannel).where(models.VoiceChannel.owner_id == owner_id))
    return result.scalar_one_or_none()

async def get_voice_channel(db: AsyncSession, channel_id: int):
    """
    Retrieves a VoiceChannel entry by its channel ID.

    Args:
        db: The asynchronous database session.
        channel_id: The ID of the voice channel.

    Returns:
        The VoiceChannel model object if found, otherwise None.
    """
    result = await db.execute(select(models.VoiceChannel).where(models.VoiceChannel.channel_id == channel_id))
    return result.scalar_one_or_none()

async def get_all_voice_channels(db: AsyncSession):
    """
    Gets all active temporary voice channels from the database.

    Args:
        db: The asynchronous database session.

    Returns:
        A list of all VoiceChannel model objects.
    """
    result = await db.execute(select(models.VoiceChannel))
    return result.scalars().all()

async def get_voice_channels_by_guild(db: AsyncSession, guild_id: int):
    """
    Gets all active temporary voice channels for a specific guild.
    """
    result = await db.execute(
        select(models.VoiceChannel).where(models.VoiceChannel.guild_id == guild_id)
    )
    return result.scalars().all()

async def create_voice_channel(db: AsyncSession, channel_id: int, owner_id: int, guild_id):
    """
    Creates a new VoiceChannel entry in the database.

    Args:
        db: The asynchronous database session.
        channel_id: The ID of the newly created voice channel.
        owner_id: The ID of the user who owns this channel.
    """
    db.add(models.VoiceChannel(channel_id=channel_id, owner_id=owner_id, guild_id=guild_id))
    await db.commit() # Commit the new entry

async def delete_voice_channel(db: AsyncSession, channel_id: int):
    """
    Deletes a VoiceChannel entry from the database by its channel ID.

    Args:
        db: The asynchronous database session.
        channel_id: The ID of the voice channel to delete.
    """
    stmt = delete(models.VoiceChannel).where(models.VoiceChannel.channel_id == channel_id)
    await db.execute(stmt)
    await db.commit() # Commit the deletion

async def update_voice_channel_owner(db: AsyncSession, channel_id: int, new_owner_id: int):
    """
    Updates the owner of an existing VoiceChannel entry.

    Args:
        db: The asynchronous database session.
        channel_id: The ID of the voice channel to update.
        new_owner_id: The ID of the new owner.
    """
    stmt = update(models.VoiceChannel).where(models.VoiceChannel.channel_id == channel_id).values(owner_id=new_owner_id)
    await db.execute(stmt)
    await db.commit() # Commit the owner update


# --- User Settings CRUD Operations ---

async def get_user_settings(db: AsyncSession, user_id: int):
    """
    Retrieves UserSettings for a specific user.

    These settings include custom channel names and limits.

    Args:
        db: The asynchronous database session.
        user_id: The unique ID of the user.

    Returns:
        The UserSettings model object if found, otherwise None.
    """
    result = await db.execute(select(models.UserSettings).where(models.UserSettings.user_id == user_id))
    return result.scalar_one_or_none()

async def update_user_channel_name(db: AsyncSession, user_id: int, name: str):
    """
    Updates a user's custom channel name setting or creates it if it doesn't exist.

    Args:
        db: The asynchronous database session.
        user_id: The ID of the user.
        name: The new custom channel name.
    """
    settings = await get_user_settings(db, user_id)
    if settings:
        # Update existing user settings
        stmt = update(models.UserSettings).where(models.UserSettings.user_id == user_id).values(custom_channel_name=name)
        await db.execute(stmt)
    else:
        # Create new user settings
        db.add(models.UserSettings(user_id=user_id, custom_channel_name=name))
    await db.commit() # Commit the changes

async def update_user_channel_limit(db: AsyncSession, user_id: int, limit: int):
    """
    Updates a user's custom channel limit setting or creates it if it doesn't exist.

    Args:
        db: The asynchronous database session.
        user_id: The ID of the user.
        limit: The new custom channel limit.
    """
    settings = await get_user_settings(db, user_id)
    if settings:
        # Update existing user settings
        stmt = update(models.UserSettings).where(models.UserSettings.user_id == user_id).values(custom_channel_limit=limit)
        await db.execute(stmt)
    else:
        # Create new user settings
        db.add(models.UserSettings(user_id=user_id, custom_channel_limit=limit))
    await db.commit() # Commit the changes

# --- Audit Log CRUD Operations ---

async def create_audit_log_entry(
    db: AsyncSession,
    guild_id: int,
    event_type: AuditLogEventType, # Using the Enum type directly for clarity
    user_id: Optional[int] = None,
    channel_id: Optional[int] = None,
    details: Optional[str] = None
):
    """
    Creates a new audit log entry in the database.

    Args:
        db: The asynchronous database session.
        guild_id: The ID of the guild where the event occurred.
        event_type: The type of event (from AuditLogEventType enum).
        user_id: Optional. The ID of the user associated with the event.
        channel_id: Optional. The ID of the channel associated with the event.
        details: Optional. A detailed description of the event.
    """
    db.add(models.AuditLogEntry(
        guild_id=guild_id,
        user_id=user_id,
        channel_id=channel_id,
        event_type=event_type.value, # Store the string value of the Enum
        details=details
    ))
    await db.commit() # Commit the new log entry

async def get_latest_audit_log_entries(db: AsyncSession, guild_id: int, limit: int = 10):
    """
    Gets the latest audit log entries for a given guild, ordered by timestamp descending.

    Args:
        db: The asynchronous database session.
        guild_id: The ID of the guild to retrieve logs for.
        limit: The maximum number of entries to retrieve (default is 10).

    Returns:
        A list of AuditLogEntry model objects.
    """
    result = await db.execute(
        select(models.AuditLogEntry)
        .where(models.AuditLogEntry.guild_id == guild_id)
        .order_by(desc(models.AuditLogEntry.timestamp))
        .limit(limit)
    )
    return result.scalars().all()