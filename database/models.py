# VoiceMaster2.0/database/models.py
from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Integer,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from enum import Enum # New import

Base = declarative_base()

# New Enum for Audit Log Event Types
class AuditLogEventType(Enum):
    """Defines the types of events that can be logged in the audit trail."""
    BOT_SETUP = "BOT_SETUP"
    SETUP_TIMED_OUT = "SETUP_TIMED_OUT"
    SETUP_ERROR = "SETUP_ERROR"
    CHANNEL_RENAMED = "CHANNEL_RENAMED"
    CATEGORY_RENAMED = "CATEGORY_RENAMED"
    CHANNEL_RENAME_TIMED_OUT = "CHANNEL_RENAME_TIMED_OUT"
    CHANNEL_RENAME_ERROR = "CHANNEL_RENAME_ERROR"
    CATEGORY_RENAME_TIMED_OUT = "CATEGORY_RENAME_TIMED_OUT"
    CATEGORY_RENAME_ERROR = "CATEGORY_RENAME_ERROR"
    CREATION_CHANNEL_CHANGED = "CREATION_CHANNEL_CHANGED"
    VOICE_CATEGORY_CHANGED = "VOICE_CATEGORY_CHANGED"
    LIST_CHANNELS = "LIST_CHANNELS"
    CHANNEL_LOCKED = "CHANNEL_LOCKED"
    CHANNEL_UNLOCKED = "CHANNEL_UNLOCKED"
    CHANNEL_PERMIT = "CHANNEL_PERMIT"
    CHANNEL_CLAIMED = "CHANNEL_CLAIMED"
    LIVE_CHANNEL_NAME_CHANGED = "LIVE_CHANNEL_NAME_CHANGED"
    USER_DEFAULT_NAME_SET = "USER_DEFAULT_NAME_SET"
    LIVE_CHANNEL_LIMIT_CHANGED = "LIVE_CHANNEL_LIMIT_CHANGED"
    USER_DEFAULT_LIMIT_SET = "USER_DEFAULT_LIMIT_SET"
    CHANNEL_DELETED = "CHANNEL_DELETED"
    CHANNEL_DELETED_NOT_FOUND = "CHANNEL_DELETED_NOT_FOUND"
    CHANNEL_DELETE_ERROR = "CHANNEL_DELETE_ERROR"
    USER_LEFT_OWNED_CHANNEL = "USER_LEFT_OWNED_CHANNEL"
    USER_LEFT_TEMP_CHANNEL = "USER_LEFT_TEMP_CHANNEL"
    USER_MOVED_TO_EXISTING_CHANNEL = "USER_MOVED_TO_EXISTING_CHANNEL"
    STALE_CHANNEL_CLEANUP = "STALE_CHANNEL_CLEANUP"
    CONFIG_ERROR = "CONFIG_ERROR"
    CATEGORY_NOT_FOUND = "CATEGORY_NOT_FOUND"
    CHANNEL_CREATED = "CHANNEL_CREATED"
    CHANNEL_CREATION_FAILED = "CHANNEL_CREATION_FAILED"


class Guild(Base):
    __tablename__ = "guilds"
    id = Column(BigInteger, primary_key=True, index=True)
    owner_id = Column(BigInteger, nullable=False)
    voice_category_id = Column(BigInteger, nullable=True)
    creation_channel_id = Column(BigInteger, nullable=True)

    settings = relationship("GuildSettings", back_populates="guild", uselist=False)


class GuildSettings(Base):
    __tablename__ = "guild_settings"
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), primary_key=True)
    default_channel_name = Column(String, default="{user}'s Channel")
    default_channel_limit = Column(Integer, default=0)

    guild = relationship("Guild", back_populates="settings")


class UserSettings(Base):
    __tablename__ = "user_settings"
    user_id = Column(BigInteger, primary_key=True, index=True)
    custom_channel_name = Column(String, nullable=True)
    custom_channel_limit = Column(Integer, nullable=True)


class VoiceChannel(Base):
    __tablename__ = "voice_channels"
    channel_id = Column(BigInteger, primary_key=True, index=True)
    owner_id = Column(BigInteger, nullable=False, index=True)

class AuditLogEntry(Base):
    __tablename__ = "audit_log_entries"
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    guild_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=True)
    channel_id = Column(BigInteger, nullable=True)
    event_type = Column(String, nullable=False)
    details = Column(String, nullable=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())