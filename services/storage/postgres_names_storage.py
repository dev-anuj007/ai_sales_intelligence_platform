from __future__ import annotations

from datetime import datetime
from typing import Any

import logfire
from sqlalchemy.orm import Session

from services.storage.abstractions import NamesStorageService
from services.storage.enums import StorageType, TableType
from services.storage.postgres_connection import get_pool
from services.storage.sqlmodel_models import AccountSQL


class PostgresNamesStorageServiceImpl:
    """PostgreSQL implementation of names storage using SQLModel."""

    storage_type = StorageType.DATABASE
    table_type = TableType.ACCOUNTS

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self._owns_session = session is None
        self._cache: dict[str, str] = {}

    def _get_session(self) -> Session:
        """Get or create a session."""
        if self.session is not None:
            return self.session
        return get_pool().get_connection()

    def store_name(self, root_domain: str, company_name: str, source: str) -> None:
        """Store company name for a domain."""
        session = self._get_session()
        try:
            account = session.query(AccountSQL).filter(
                AccountSQL.root_domain == root_domain
            ).first()
            if account:
                account.inferred_company_name = company_name
                account.enriched_at = datetime.utcnow()
                session.commit()
                self._cache[root_domain] = company_name
                logfire.info("names_storage.stored", root_domain=root_domain, source=source)
        finally:
            if self._owns_session:
                session.close()

    def get_name(self, root_domain: str) -> str | None:
        """Get company name for a domain."""
        if root_domain in self._cache:
            return self._cache[root_domain]

        session = self._get_session()
        try:
            account = session.query(AccountSQL).filter(
                AccountSQL.root_domain == root_domain
            ).first()

            if account and account.inferred_company_name:
                self._cache[root_domain] = account.inferred_company_name
                return account.inferred_company_name

            return None
        finally:
            if self._owns_session:
                session.close()

    def list_by_pattern(self, pattern: str, limit: int = 100) -> dict[str, str]:
        """List domains by company name pattern."""
        session = self._get_session()
        try:
            accounts = session.query(AccountSQL).filter(
                AccountSQL.inferred_company_name.ilike(f"%{pattern}%"),
                AccountSQL.inferred_company_name.isnot(None),
            ).limit(limit).all()

            result = {}
            for account in accounts:
                if account.inferred_company_name:
                    result[account.root_domain] = account.inferred_company_name
                    self._cache[account.root_domain] = account.inferred_company_name

            return result
        finally:
            if self._owns_session:
                session.close()

    def clear_cache(self) -> None:
        """Clear the in-memory cache."""
        self._cache.clear()
        logfire.info("names_storage.cache_cleared")
