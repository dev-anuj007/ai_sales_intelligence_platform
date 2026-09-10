from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from typing import AsyncGenerator, Generator

import logfire
from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from config import settings
from services.storage.abstractions import ConnectionPool


class PostgresConnectionPool:
    """PostgreSQL connection pool using SQLAlchemy."""

    def __init__(
        self,
        host: str | None = None,
        port: int | None = None,
        database: str | None = None,
        user: str | None = None,
        password: str | None = None,
        pool_size: int = 10,
        max_overflow: int = 20,
    ) -> None:
        self.host = host or settings.postgres_host
        self.port = port or settings.postgres_port
        self.database = database or settings.postgres_database
        self.user = user or settings.postgres_user
        self.password = password or settings.postgres_password
        self.pool_size = pool_size
        self.max_overflow = max_overflow

        database_url = (
            f"postgresql+psycopg2://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )

        self.engine = create_engine(
            database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=False,
        )

        self.session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )

        async_database_url = (
            f"postgresql+asyncpg://{self.user}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
        )
        self.async_engine = create_async_engine(
            async_database_url,
            pool_size=pool_size,
            max_overflow=max_overflow,
            pool_pre_ping=True,
            echo=False,
        )

        self.async_session_local = sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )

        # Log SQL queries in debug mode
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(
            conn: any, cursor: any, statement: str, parameters: any, context: any, executemany: any
        ) -> None:
            if settings.log_level == "DEBUG":
                logfire.debug("sql_execute", statement=statement)

    def get_connection(self) -> Session:
        """Get a new database session."""
        return self.session_local()

    async def get_async_connection(self) -> AsyncSession:
        """Get a new async database session."""
        return self.async_session_local()

    @contextmanager
    def context(self) -> Generator[Session, None, None]:
        """Context manager for database sessions."""
        session = self.session_local()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    @asynccontextmanager
    async def async_context(self) -> AsyncGenerator[AsyncSession, None]:
        """Async context manager for database sessions."""
        session = self.async_session_local()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    def close(self) -> None:
        """Close all connections in the pool."""
        self.engine.dispose()
        logfire.info("postgres_pool.closed")

    async def close_async(self) -> None:
        """Close all async connections in the pool."""
        await self.async_engine.dispose()
        logfire.info("postgres_pool.async_closed")

    def create_all_tables(self) -> None:
        """Create all tables from SQLModel definitions."""
        from services.storage.sqlmodel_models import (
            AccountSQL,
            AccountTopRecordSQL,
            StagingRecordSQL,
            TraceRecordSQL,
        )

        # Import to register models
        _ = [AccountSQL, AccountTopRecordSQL, StagingRecordSQL, TraceRecordSQL]

        from sqlmodel import SQLModel

        SQLModel.metadata.create_all(self.engine)
        logfire.info("postgres_pool.all_tables_created")

    def health_check(self) -> bool:
        """Check if database is accessible."""
        try:
            from sqlalchemy import text

            with self.context() as session:
                session.execute(text("SELECT 1"))
            return True
        except Exception as e:
            logfire.error("postgres_pool.health_check_failed", error=str(e))
            return False


_global_pool: PostgresConnectionPool | None = None


def init_pool(
    host: str | None = None,
    port: int | None = None,
    database: str | None = None,
    user: str | None = None,
    password: str | None = None,
) -> PostgresConnectionPool:
    """Initialize the global PostgreSQL connection pool."""
    global _global_pool
    if _global_pool is None:
        _global_pool = PostgresConnectionPool(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password,
        )
    return _global_pool


def get_pool() -> PostgresConnectionPool:
    """Get the global PostgreSQL connection pool."""
    if _global_pool is None:
        raise RuntimeError("Connection pool not initialized. Call init_pool() first.")
    return _global_pool


def close_pool() -> None:
    """Close the global PostgreSQL connection pool."""
    global _global_pool
    if _global_pool is not None:
        _global_pool.close()
        _global_pool = None


async def close_pool_async() -> None:
    """Close the global PostgreSQL connection pool (async)."""
    global _global_pool
    if _global_pool is not None:
        await _global_pool.close_async()
        _global_pool = None
