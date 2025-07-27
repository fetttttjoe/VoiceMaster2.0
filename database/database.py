from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from contextlib import asynccontextmanager
from typing import AsyncGenerator
import logging # Import logging for explicit error logging

from .models import Base
from config import DATABASE_URL, DB_ECHO # Ensure DATABASE_URL and DB_ECHO are correctly imported from config

class Database:
    """
    Manages the asynchronous database connection and session lifecycle.
    It provides an engine for database interaction and a session factory
    for creating transactional scopes.
    """
    def __init__(self, db_url: str):
        """
        Initializes the Database instance with a database URL.

        Args:
            db_url: The connection string for the PostgreSQL database.
        """
        # Create an asynchronous SQLAlchemy engine.
        # `echo=False` means SQL statements won't be printed to console by default,
        # which is suitable for production but can be set to `True` for debugging.
        self.engine = create_async_engine(db_url, echo=DB_ECHO)
        
        # Create a sessionmaker for asynchronous sessions.
        # `expire_on_commit=False` ensures that objects remain accessible after commit
        # without needing to be reloaded, which can simplify some data access patterns.
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            expire_on_commit=False,
            class_=AsyncSession # Explicitly set the session class to AsyncSession
        )

    async def init_db(self):
        """
        A hook for database initialization.

        In this application, schema creation and migrations are handled externally
        by Alembic, so this method serves primarily as a placeholder for any
        future direct database initialization logic (e.g., creating tables if not
        using Alembic, or populating initial data).
        """
        # Alembic handles table creation and schema updates.
        # No direct table creation via SQLAlchemy's ORM `Base.metadata.create_all`
        # is performed here to avoid conflicts with Alembic.
        pass

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Provides an asynchronous transactional scope around a series of database operations.

        This is the primary entry point for acquiring and managing database sessions.
        It ensures that a session is properly opened, committed on success,
        and rolled back on any exceptions, then safely closed.

        Yields:
            An `AsyncSession` instance, which can be used to interact with the database.

        Raises:
            Exception: Re-raises any exception that occurs within the transactional block
                       after performing a rollback.
        """
        # Use `async with` for proper asynchronous session management.
        async with self.session_factory() as session:
            try:
                yield session # Yield the session for use in the 'async with' block
                await session.commit() # Commit changes if no exceptions occurred
            except Exception as e:
                # Log the exception for debugging purposes before rolling back.
                logging.error(f"Database session encountered an error, rolling back: {e}", exc_info=True)
                await session.rollback() # Rollback changes on any exception
                raise # Re-raise the exception to propagate it
                

# Instantiate the Database class with the URL from config.
# This makes the `db` object available globally for easy session retrieval.
db = Database(DATABASE_URL)