from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from .models import Base
from config import DATABASE_URL

class Database:
    def __init__(self, db_url: str):
        self.engine = create_async_engine(db_url, echo=False)
        self.session_factory = async_sessionmaker(
            bind=self.engine, expire_on_commit=False
        )

    async def init_db(self):
        """
        A hook for database initialization. In this application, it serves as a placeholder
        as all database schema migrations are handled by Alembic.
        """
        pass  # Alembic handles table creation.

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provide a transactional scope around a series of operations.
        This is the main entry point for database sessions.
        """
        async with self.session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
                


db = Database(DATABASE_URL)