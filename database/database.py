# database/database.py
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from config import settings

from .base import Base

logger = logging.getLogger(__name__)


class Database:
    def __init__(self):
        self.engine = None
        self.session_factory = None

    def init_db(self, db_url: str):
        """Initializes the database engine and session factory."""
        self.engine = create_async_engine(db_url, echo=settings.DB_ECHO)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

    async def create_all(self):
        """Creates all database tables."""
        if not self.engine:
            raise RuntimeError("Database has not been initialized. Call init_db() first.")
        async with self.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provides a transactional scope around a series of operations."""
        if not self.session_factory:
            raise RuntimeError("Database has not been initialized. Call init_db() first.")

        session: AsyncSession = self.session_factory()
        try:
            yield session
            await session.commit()
        except Exception as e:
            logger.error(f"Session rollback due to exception: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


# Create a single, uninitialized instance that will be configured at runtime.
db = Database()
