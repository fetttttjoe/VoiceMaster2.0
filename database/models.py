# VoiceMaster2.0/database/models.py
from sqlalchemy import (
    Column,
    BigInteger,
    Boolean,
    String,
    Integer,
    ForeignKey,
    DateTime,
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
from enum import Enum # Standard library enum for defining fixed sets of names/values

# Base class for declarative models, used to map Python classes to database tables.
Base = declarative_base()

# --- Enum for Audit Log Event Types ---
class AuditLogEventType(Enum):
    """
    Defines the types of events that can be logged in the audit trail.
    Each member has a string value that is stored in the database.
    """
    # Bot Setup Events
    BOT_SETUP = "BOT_SETUP"
    SETUP_TIMED_OUT = "SETUP_TIMED_OUT"
    SETUP_ERROR = "SETUP_ERROR"

    # Channel/Category Renaming Events
    CHANNEL_RENAMED = "CHANNEL_RENAMED"
    CATEGORY_RENAMED = "CATEGORY_RENAMED"
    CHANNEL_RENAME_TIMED_OUT = "CHANNEL_RENAME_TIMED_OUT"
    CHANNEL_RENAME_ERROR = "CHANNEL_RENAME_ERROR"
    CATEGORY_RENAME_TIMED_OUT = "CATEGORY_RENAME_TIMED_OUT"
    CATEGORY_RENAME_ERROR = "CATEGORY_RENAME_ERROR"

    # Configuration Change Events
    CREATION_CHANNEL_CHANGED = "CREATION_CHANNEL_CHANGED"
    VOICE_CATEGORY_CHANGED = "VOICE_CATEGORY_CHANGED"

    # User Command/Interaction Events
    LIST_CHANNELS = "LIST_CHANNELS"
    CHANNEL_LOCKED = "CHANNEL_LOCKED"
    CHANNEL_UNLOCKED = "CHANNEL_UNLOCKED"
    CHANNEL_PERMIT = "CHANNEL_PERMIT"
    CHANNEL_CLAIMED = "CHANNEL_CLAIMED"
    LIVE_CHANNEL_NAME_CHANGED = "LIVE_CHANNEL_NAME_CHANGED"
    USER_DEFAULT_NAME_SET = "USER_DEFAULT_NAME_SET"
    LIVE_CHANNEL_LIMIT_CHANGED = "LIVE_CHANNEL_LIMIT_CHANGED"
    USER_DEFAULT_LIMIT_SET = "USER_DEFAULT_LIMIT_SET"

    # Channel Deletion/Lifecycle Events
    CHANNEL_DELETED = "CHANNEL_DELETED"
    CHANNEL_DELETED_NOT_FOUND = "CHANNEL_DELETED_NOT_FOUND" # Channel gone from Discord but still in DB
    CHANNEL_DELETE_ERROR = "CHANNEL_DELETE_ERROR"
    USER_LEFT_OWNED_CHANNEL = "USER_LEFT_OWNED_CHANNEL"
    USER_LEFT_TEMP_CHANNEL = "USER_LEFT_TEMP_CHANNEL"
    USER_MOVED_TO_EXISTING_CHANNEL = "USER_MOVED_TO_EXISTING_CHANNEL"
    STALE_CHANNEL_CLEANUP = "STALE_CHANNEL_CLEANUP" # DB entry exists but Discord channel doesn't

    CLEANUP_STATE_CHANGED = "CLEANUP_STATE_CHANGED"

    # Error/Configuration Specific Events
    CONFIG_ERROR = "CONFIG_ERROR"
    CATEGORY_NOT_FOUND = "CATEGORY_NOT_FOUND"
    CHANNEL_CREATED = "CHANNEL_CREATED"
    CHANNEL_CREATION_FAILED = "CHANNEL_CREATION_FAILED"

    UNKNOWN_ERROR = "UNKNOWN_ERROR"

# --- Guild Model ---
class Guild(Base):
    """
    Represents a Discord guild (server) and its main configuration settings.
    This includes settings relevant to the bot's operation within that guild.
    """
    __tablename__ = "guilds" # Database table name

    id = Column(BigInteger, primary_key=True, index=True)
    owner_id = Column(BigInteger, nullable=False) # The ID of the guild's owner (Discord user ID)
    voice_category_id = Column(BigInteger, nullable=True) # The ID of the category where temp voice channels are created
    creation_channel_id = Column(BigInteger, nullable=True) # The ID of the voice channel users join to create new channels
    cleanup_on_startup = Column(Boolean, default=True, nullable=False)
    # One-to-one relationship with GuildSettings, allowing access to default settings
    # `uselist=False` indicates a one-to-one relationship
    settings = relationship("GuildSettings", back_populates="guild", uselist=False)
    audit_logs = relationship("AuditLogEntry", back_populates="guild")
    voice_channels = relationship("VoiceChannel")



# --- Guild Settings Model ---
class GuildSettings(Base):
    """
    Stores default settings for temporary channels within a specific guild.
    These are general settings applied to all new channels created in that guild,
    unless overridden by user-specific settings.
    """
    __tablename__ = "guild_settings"

    guild_id = Column(BigInteger, ForeignKey("guilds.id"), primary_key=True)
    default_channel_name = Column(String, default="{user}'s Channel") # Template for default channel name
    default_channel_limit = Column(Integer, default=0) # Default user limit for channels (0 means no limit)

    # Relationship back to the Guild model
    guild = relationship("Guild", back_populates="settings")


# --- User Settings Model ---
class UserSettings(Base):
    """
    Stores individual user preferences for their temporary voice channels.
    These settings override guild default settings.
    """
    __tablename__ = "user_settings"

    user_id = Column(BigInteger, primary_key=True, index=True)
    custom_channel_name = Column(String, nullable=True) # Custom name preference for user's channels
    custom_channel_limit = Column(Integer, nullable=True) # Custom user limit preference for user's channels


# --- Voice Channel Model ---
class VoiceChannel(Base):
    """
    Represents an active temporary voice channel created by the bot.
    Tracks which Discord channel is a temporary channel and who its owner is.
    """
    __tablename__ = "voice_channels"

    channel_id = Column(BigInteger, primary_key=True, index=True) # Discord channel ID
    owner_id = Column(BigInteger, nullable=False, index=True) # The ID of the user who "owns" this channel
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False, index=True) # the guild where the channel belongs to

# --- Audit Log Entry Model ---
class AuditLogEntry(Base):
    """
    Records significant events and administrative actions performed by or through the bot.
    Provides a historical trace of bot activities for auditing and debugging.
    """
    __tablename__ = "audit_log_entries"

    id = Column(BigInteger, primary_key=True, autoincrement=True) # Unique ID for each log entry
    guild_id = Column(BigInteger, ForeignKey("guilds.id"), nullable=False, index=True) # The guild where the event occurred
    user_id = Column(BigInteger, nullable=True) # Optional: User associated with the event
    channel_id = Column(BigInteger, nullable=True) # Optional: Channel associated with the event
    event_type = Column(String, nullable=False) # Type of event, stored as string from AuditLogEventType enum
    details = Column(String, nullable=True) # Optional: Detailed description of the event
    timestamp = Column(DateTime(timezone=True), server_default=func.now()) # Timestamp of the event, defaults to current UTC time

    guild = relationship("Guild", back_populates="audit_logs")