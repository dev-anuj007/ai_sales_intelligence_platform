from __future__ import annotations

from datetime import datetime
from typing import Any

import duckdb
import logfire

from services.storage.abstractions import StorageService
from services.storage.duckdb_connection import get_pool
from services.storage.enums import StorageType, TableType
from services.storage.models import Account


class AccountStorageService:
    storage_type = StorageType.DATABASE
    table_type = TableType.ACCOUNTS

    def __init__(self, connection: duckdb.DuckDBPyConnection | None = None) -> None:
        self.connection = connection or get_pool().get_connection()

    def get(self, root_domain: str) -> Account | None:
        row = self._fetch_one(
            "SELECT * FROM accounts WHERE root_domain = ?",
            {"root_domain": root_domain}
        )
        return Account(**row) if row else None

    def list(self, limit: int = 100, offset: int = 0) -> list[Account]:
        rows = self._fetch_all(
            "SELECT * FROM accounts LIMIT ? OFFSET ?",
            {"limit": limit, "offset": offset}
        )
        return [Account(**row) for row in rows]

    def create(self, entity: Account) -> Account:
        raise NotImplementedError("Accounts are created via aggregation, not direct insert.")

    def update(self, entity: Account) -> Account:
        query = """
            UPDATE accounts
            SET risk_score = ?, score_version = ?, signal_tags = ?, score_explanation = ?,
                scored_at = ?, inferred_company_name = ?, inferred_industry = ?,
                narrative = ?, outreach_draft = ?, enriched_at = ?
            WHERE root_domain = ?
        """
        self._execute(
            query,
            {
                "risk_score": entity.risk_score,
                "score_version": entity.score_version,
                "signal_tags": entity.signal_tags,
                "score_explanation": entity.score_explanation,
                "scored_at": entity.scored_at,
                "inferred_company_name": entity.inferred_company_name,
                "inferred_industry": entity.inferred_industry,
                "narrative": entity.narrative,
                "outreach_draft": entity.outreach_draft,
                "enriched_at": entity.enriched_at,
                "root_domain": entity.root_domain,
            }
        )
        return entity

    def delete(self, root_domain: str) -> bool:
        raise NotImplementedError("Deletion of accounts is not supported.")

    def count(self) -> int:
        row = self._fetch_one("SELECT COUNT(*) as cnt FROM accounts WHERE excluded_as_honeypot = false")
        return row["cnt"] if row else 0

    def list_by_score(
        self, min_score: float | None = None, max_score: float | None = None, limit: int = 100
    ) -> list[Account]:
        query = "SELECT * FROM accounts WHERE excluded_as_honeypot = false"
        params: dict[str, Any] = {"limit": limit}

        if min_score is not None:
            query += " AND risk_score >= :min_score"
            params["min_score"] = min_score

        if max_score is not None:
            query += " AND risk_score <= :max_score"
            params["max_score"] = max_score

        query += " ORDER BY risk_score DESC LIMIT :limit"

        rows = self._fetch_all(query, params)
        return [Account(**row) for row in rows]

    def list_top_by_score(self, top_n: int = 50) -> list[Account]:
        rows = self._fetch_all(
            "SELECT * FROM accounts WHERE excluded_as_honeypot = false AND risk_score IS NOT NULL "
            "ORDER BY risk_score DESC LIMIT ?",
            {"top_n": top_n}
        )
        return [Account(**row) for row in rows]

    def update_score(
        self,
        root_domain: str,
        risk_score: float,
        score_version: str,
        signal_tags: list[str],
        score_explanation: str,
    ) -> None:
        query = """
            UPDATE accounts
            SET risk_score = ?, score_version = ?, signal_tags = ?, score_explanation = ?, scored_at = ?
            WHERE root_domain = ?
        """
        self._execute(
            query,
            {
                "risk_score": risk_score,
                "score_version": score_version,
                "signal_tags": signal_tags,
                "score_explanation": score_explanation,
                "scored_at": datetime.utcnow(),
                "root_domain": root_domain,
            }
        )
        logfire.info("account_storage.score_updated", root_domain=root_domain, risk_score=risk_score)

    def update_enrichment(
        self,
        root_domain: str,
        inferred_company_name: str | None,
        inferred_industry: str | None,
        narrative: str | None,
        outreach_draft: str | None,
    ) -> None:
        query = """
            UPDATE accounts
            SET inferred_company_name = ?, inferred_industry = ?, narrative = ?,
                outreach_draft = ?, enriched_at = ?
            WHERE root_domain = ?
        """
        self._execute(
            query,
            {
                "inferred_company_name": inferred_company_name,
                "inferred_industry": inferred_industry,
                "narrative": narrative,
                "outreach_draft": outreach_draft,
                "enriched_at": datetime.utcnow(),
                "root_domain": root_domain,
            }
        )
        logfire.info("account_storage.enrichment_updated", root_domain=root_domain)

    def _fetch_one(self, query: str, params: dict[str, Any]) -> dict[str, Any] | None:
        result = self.connection.execute(query, params).fetchall()
        return result[0] if result else None

    def _fetch_all(self, query: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        return self.connection.execute(query, params).fetchall()

    def _execute(self, query: str, params: dict[str, Any]) -> None:
        self.connection.execute(query, params)
