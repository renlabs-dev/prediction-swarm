import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import (
    create_engine,  # pyright: ignore[reportUnknownVariableType]
)
from sqlalchemy.orm import Session, sessionmaker


class Database:
    """Database connection singleton."""

    _instance: "Database | None" = None
    _engine = None
    _session_factory = None

    def __new__(cls) -> "Database":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        self._initialized = True

        # Get database URL from environment - required
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError(
                "DATABASE_URL environment variable is required but not set"
            )

        # Create engine with connection pooling
        self._engine = create_engine(
            database_url,
            pool_pre_ping=True,
            pool_recycle=300,
            echo=False,  # Set to True for SQL query logging
        )

        # Create session factory
        self._session_factory = sessionmaker(
            bind=self._engine, expire_on_commit=False
        )

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Get a database session with automatic cleanup."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")

        session = self._session_factory()
        try:
            yield session
        finally:
            session.close()

    def get_sync_session(self) -> Session:
        """Get a synchronous database session (manual cleanup required)."""
        if self._session_factory is None:
            raise RuntimeError("Database not initialized")
        return self._session_factory()


# Global database instance
database = Database()
