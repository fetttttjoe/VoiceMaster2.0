from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from .models import Base
from config import DATABASE_URL

# Create an async engine
engine = create_async_engine(DATABASE_URL, echo=False)

# Create a configured "AsyncSession" class using the modern async_sessionmaker.
# This factory will create new AsyncSession objects when called.
AsyncSessionFactory = async_sessionmaker(
    bind=engine, expire_on_commit=False
)

async def init_db():
    """
    A hook for database initialization. In this application, it serves as a placeholder
    as all database schema migrations are handled by Alembic.
    """
    pass # Alembic handles table creation.

@asynccontextmanager
async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a transactional scope around a series of operations.
    This is the main entry point for database sessions.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
