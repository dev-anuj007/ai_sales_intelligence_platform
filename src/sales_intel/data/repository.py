"""Base repository pattern for data access.

All repositories inherit from BaseRepository and provide type-safe CRUD operations.
Repositories are dependency-injected into services, enabling easy mocking for tests.
"""

from abc import ABC, abstractmethod
from typing import Generic, TypeVar

import duckdb

T = TypeVar("T")


class BaseRepository(ABC, Generic[T]):
    """Abstract base class for all repositories.

    Repositories provide a data access abstraction layer.
    All SQL queries should be written in repository methods, never in services.
    Services depend on repositories via dependency injection.
    """

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Initialize repository with a DuckDB connection.

        Args:
            connection: DuckDB connection instance.
        """
        self.connection = connection

    @abstractmethod
    def get_by_id(self, id_value: str | int) -> T | None:
        """Retrieve a single record by primary key."""
        ...

    @abstractmethod
    def list(self, limit: int = 100, offset: int = 0) -> list[T]:
        """List records with pagination."""
        ...

    @abstractmethod
    def create(self, entity: T) -> T:
        """Create and persist a new record."""
        ...

    @abstractmethod
    def update(self, entity: T) -> T:
        """Update an existing record."""
        ...

    @abstractmethod
    def delete(self, id_value: str | int) -> bool:
        """Delete a record by primary key."""
        ...

    def execute(self, query: str, params: dict[str, object] | None = None) -> duckdb.DuckDBPyRelation:
        """Execute a raw SQL query.

        Used for complex queries that don't fit standard CRUD.

        Args:
            query: SQL query string.
            params: Optional parameter dict for parameterized queries.

        Returns:
            DuckDB query result.
        """
        if params:
            return self.connection.execute(query, params)
        return self.connection.execute(query)

    def fetch_one(self, query: str, params: dict[str, object] | None = None) -> dict[str, object] | None:
        """Fetch a single record as a dict.

        Args:
            query: SQL query string.
            params: Optional parameter dict.

        Returns:
            First row as dict, or None if no results.
        """
        result = self.execute(query, params)
        rows = result.fetchall()
        if not rows:
            return None
        col_names = [desc[0] for desc in result.description]
        return dict(zip(col_names, rows[0]))

    def fetch_all(self, query: str, params: dict[str, object] | None = None) -> list[dict[str, object]]:
        """Fetch all results as a list of dicts.

        Args:
            query: SQL query string.
            params: Optional parameter dict.

        Returns:
            List of rows as dicts.
        """
        result = self.execute(query, params)
        rows = result.fetchall()
        if not rows:
            return []
        col_names = [desc[0] for desc in result.description]
        return [dict(zip(col_names, row)) for row in rows]
