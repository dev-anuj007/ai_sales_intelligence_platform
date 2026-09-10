#!/usr/bin/env python
"""Setup PostgreSQL database for AI Sales Intelligence Platform."""

from __future__ import annotations

import sys

import logfire
from sqlalchemy import create_engine, text

from config import settings
from services.storage.migrate import apply_schema
from services.storage.postgres_connection import init_pool

logfire.configure()


def create_database() -> None:
    """Create the PostgreSQL database if it doesn't exist."""
    # Connect to default postgres database to create the target database
    default_url = (
        f"postgresql+psycopg2://{settings.postgres_user}:{settings.postgres_password}@"
        f"{settings.postgres_host}:{settings.postgres_port}/postgres"
    )

    try:
        engine = create_engine(default_url)
        with engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text(f"SELECT 1 FROM pg_database WHERE datname = '{settings.postgres_database}'")
            )
            if not result.fetchone():
                # Autocommit is required for CREATE DATABASE
                conn.connection.autocommit = True
                conn.execute(text(f"CREATE DATABASE {settings.postgres_database}"))
                conn.connection.autocommit = False
                print(f"✓ Database '{settings.postgres_database}' created")
            else:
                print(f"✓ Database '{settings.postgres_database}' already exists")
        engine.dispose()
    except Exception as e:
        print(f"✗ Failed to create database: {e}")
        sys.exit(1)


def setup_pool() -> None:
    """Initialize the connection pool."""
    try:
        pool = init_pool()
        print("✓ Connection pool initialized")

        # Test connection
        if pool.health_check():
            print("✓ Database connection successful")
        else:
            print("✗ Database connection failed")
            sys.exit(1)
    except Exception as e:
        print(f"✗ Failed to initialize connection pool: {e}")
        sys.exit(1)


def setup_tables() -> None:
    """Create all tables using SQLModel."""
    try:
        apply_schema()
        print("✓ All tables created successfully")
    except Exception as e:
        print(f"✗ Failed to create tables: {e}")
        sys.exit(1)


def main() -> None:
    """Run full setup process."""
    print("\n🚀 Setting up PostgreSQL for AI Sales Intelligence Platform\n")

    print(f"Database Host: {settings.postgres_host}:{settings.postgres_port}")
    print(f"Database Name: {settings.postgres_database}")
    print(f"Database User: {settings.postgres_user}\n")

    create_database()
    setup_pool()
    setup_tables()

    print("\n✅ Setup complete!\n")


if __name__ == "__main__":
    main()
