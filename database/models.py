from sqlalchemy import (
    Column,
    BigInteger,
    String,
    Integer,
    ForeignKey,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

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