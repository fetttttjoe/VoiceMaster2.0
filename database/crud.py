from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from . import models
from sqlalchemy import desc
from typing import Optional
from .models import AuditLogEventType
# Guild CRUD
async def get_guild(db: AsyncSession, guild_id: int):
    result = await db.execute(select(models.Guild).where(models.Guild.id == guild_id))
    return result.scalar_one_or_none()

async def create_or_update_guild(db: AsyncSession, guild_id: int, owner_id: int, category_id: int, channel_id: int):
    guild = await get_guild(db, guild_id)
    if guild:
        stmt = (
            update(models.Guild)
            .where(models.Guild.id == guild_id)
            .values(owner_id=owner_id, voice_category_id=category_id, creation_channel_id=channel_id)
        )
        await db.execute(stmt)
    else:
        db.add(models.Guild(id=guild_id, owner_id=owner_id, voice_category_id=category_id, creation_channel_id=channel_id))
    await db.commit()

# Voice Channel CRUD
async def get_voice_channel_by_owner(db: AsyncSession, owner_id: int):
    result = await db.execute(select(models.VoiceChannel).where(models.VoiceChannel.owner_id == owner_id))
    return result.scalar_one_or_none()

async def get_voice_channel(db: AsyncSession, channel_id: int):
    result = await db.execute(select(models.VoiceChannel).where(models.VoiceChannel.channel_id == channel_id))
    return result.scalar_one_or_none()

async def get_all_voice_channels(db: AsyncSession):
    """Gets all active temporary voice channels from the database."""
    result = await db.execute(select(models.VoiceChannel))
    return result.scalars().all()

async def create_voice_channel(db: AsyncSession, channel_id: int, owner_id: int):
    db.add(models.VoiceChannel(channel_id=channel_id, owner_id=owner_id))
    await db.commit()

async def delete_voice_channel(db: AsyncSession, channel_id: int):
    stmt = delete(models.VoiceChannel).where(models.VoiceChannel.channel_id == channel_id)
    await db.execute(stmt)
    await db.commit()
    
async def update_voice_channel_owner(db: AsyncSession, channel_id: int, new_owner_id: int):
    stmt = update(models.VoiceChannel).where(models.VoiceChannel.channel_id == channel_id).values(owner_id=new_owner_id)
    await db.execute(stmt)
    await db.commit()


# User Settings CRUD
async def get_user_settings(db: AsyncSession, user_id: int):
    result = await db.execute(select(models.UserSettings).where(models.UserSettings.user_id == user_id))
    return result.scalar_one_or_none()

async def update_user_channel_name(db: AsyncSession, user_id: int, name: str):
    settings = await get_user_settings(db, user_id)
    if settings:
        stmt = update(models.UserSettings).where(models.UserSettings.user_id == user_id).values(custom_channel_name=name)
        await db.execute(stmt)
    else:
        db.add(models.UserSettings(user_id=user_id, custom_channel_name=name))
    await db.commit()

async def update_user_channel_limit(db: AsyncSession, user_id: int, limit: int):
    settings = await get_user_settings(db, user_id)
    if settings:
        stmt = update(models.UserSettings).where(models.UserSettings.user_id == user_id).values(custom_channel_limit=limit)
        await db.execute(stmt)
    else:
        db.add(models.UserSettings(user_id=user_id, custom_channel_limit=limit))
    await db.commit()

async def create_audit_log_entry(
    db: AsyncSession,
    guild_id: int,
    event_type: AuditLogEventType, # Changed type hint to Enum
    user_id: Optional[int] = None,
    channel_id: Optional[int] = None,
    details: Optional[str] = None
):
    """Creates a new audit log entry."""
    db.add(models.AuditLogEntry(
        guild_id=guild_id,
        user_id=user_id,
        channel_id=channel_id,
        event_type=event_type.value, # Store the string value
        details=details
    ))
    await db.commit()

async def get_latest_audit_log_entries(db: AsyncSession, guild_id: int, limit: int = 10):
    """Gets the latest audit log entries for a given guild."""
    result = await db.execute(
        select(models.AuditLogEntry)
        .where(models.AuditLogEntry.guild_id == guild_id)
        .order_by(desc(models.AuditLogEntry.timestamp))
        .limit(limit)
    )
    return result.scalars().all()