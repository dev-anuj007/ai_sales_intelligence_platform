from __future__ import annotations

import logfire


def apply_schema() -> None:
    """Apply PostgreSQL schema using SQLModel."""
    from services.storage.postgres_connection import get_pool

    pool = get_pool()
    pool.create_all_tables()
    logfire.info("storage.postgres_schema_applied")
