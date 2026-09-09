from datetime import datetime
from typing import Any

import duckdb
import logfire

from sales_intel.data.models import Account, StagingRecord
from sales_intel.data.repository import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def get_by_id(self, root_domain: str) -> Account | None:
        row = self.fetch_one("SELECT * FROM accounts WHERE root_domain = ?", {"root_domain": root_domain})
        return Account(**row) if row else None

    def list(self, limit: int = 100, offset: int = 0) -> list[Account]:
        rows = self.fetch_all(
            "SELECT * FROM accounts LIMIT ? OFFSET ?",
            {"limit": limit, "offset": offset},
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
        self.execute(
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
            },
        )
        return entity

    def delete(self, id_value: str) -> bool:
        """Delete an account (rarely used; mostly for testing)."""
        raise NotImplementedError("Deletion of accounts is not supported.")

    def list_by_score(
        self, min_score: float | None = None, max_score: float | None = None, limit: int = 100
    ) -> list[Account]:
        """List accounts filtered and sorted by risk_score."""
        query = "SELECT * FROM accounts WHERE excluded_as_honeypot = false"
        params: dict[str, Any] = {"limit": limit}

        if min_score is not None:
            query += " AND risk_score >= :min_score"
            params["min_score"] = min_score

        if max_score is not None:
            query += " AND risk_score <= :max_score"
            params["max_score"] = max_score

        query += " ORDER BY risk_score DESC LIMIT :limit"

        rows = self.fetch_all(query, params)
        return [Account(**row) for row in rows]

    def list_by_country(self, country_code: str, limit: int = 100) -> list[Account]:
        """List accounts filtered by primary country, sorted by risk_score."""
        rows = self.fetch_all(
            "SELECT * FROM accounts WHERE primary_country_code = ? AND excluded_as_honeypot = false "
            "ORDER BY risk_score DESC LIMIT ?",
            {"country_code": country_code, "limit": limit},
        )
        return [Account(**row) for row in rows]

    def list_by_tag(self, tag: str, limit: int = 100) -> list[Account]:
        """List accounts containing a signal tag, sorted by risk_score."""
        rows = self.fetch_all(
            "SELECT * FROM accounts WHERE list_contains(signal_tags, ?) AND excluded_as_honeypot = false "
            "ORDER BY risk_score DESC LIMIT ?",
            {"tag": tag, "limit": limit},
        )
        return [Account(**row) for row in rows]

    def list_unscored(self, limit: int = 100) -> list[Account]:
        """List accounts that have not been scored yet."""
        rows = self.fetch_all(
            "SELECT * FROM accounts WHERE risk_score IS NULL AND excluded_as_honeypot = false "
            "LIMIT ?",
            {"limit": limit},
        )
        return [Account(**row) for row in rows]

    def list_unenriched(self, score_version: str | None = None, limit: int = 100) -> list[Account]:
        """List accounts that have not been enriched yet (no narrative).

        Optionally filter by a specific score_version.
        """
        query = (
            "SELECT * FROM accounts WHERE enriched_at IS NULL AND excluded_as_honeypot = false "
            "AND risk_score IS NOT NULL"
        )
        params: dict[str, Any] = {"limit": limit}

        if score_version:
            query += " AND score_version = :score_version"
            params["score_version"] = score_version

        query += " ORDER BY risk_score DESC LIMIT :limit"

        rows = self.fetch_all(query, params)
        return [Account(**row) for row in rows]

    def list_top_by_score(self, top_n: int = 50) -> list[Account]:
        """List top N accounts by risk_score (excluding honeypots)."""
        rows = self.fetch_all(
            "SELECT * FROM accounts WHERE excluded_as_honeypot = false AND risk_score IS NOT NULL "
            "ORDER BY risk_score DESC LIMIT ?",
            {"top_n": top_n},
        )
        return [Account(**row) for row in rows]

    def get_top_records(self, root_domain: str, limit: int = 20) -> list[StagingRecord]:
        """Get the top N staging records for a given account (for LLM grounding)."""
        query = """
            SELECT sr.* FROM staging_records sr
            JOIN account_top_records atr ON sr.record_id = atr.record_id
            WHERE atr.root_domain = ?
            ORDER BY atr.rank
            LIMIT ?
        """
        rows = self.fetch_all(query, {"root_domain": root_domain, "limit": limit})
        return [StagingRecord(**row) for row in rows]

    def count_scored(self) -> int:
        """Count accounts that have been scored."""
        row = self.fetch_one("SELECT COUNT(*) as cnt FROM accounts WHERE risk_score IS NOT NULL")
        return row["cnt"] if row else 0

    def count_enriched(self) -> int:
        """Count accounts that have been enriched (have narrative)."""
        row = self.fetch_one("SELECT COUNT(*) as cnt FROM accounts WHERE enriched_at IS NOT NULL")
        return row["cnt"] if row else 0

    def count_all(self) -> int:
        """Count all accounts (excluding honeypots)."""
        row = self.fetch_one("SELECT COUNT(*) as cnt FROM accounts WHERE excluded_as_honeypot = false")
        return row["cnt"] if row else 0

    def count_excluded_honeypot(self) -> int:
        """Count accounts excluded as pure honeypots."""
        row = self.fetch_one("SELECT COUNT(*) as cnt FROM accounts WHERE excluded_as_honeypot = true")
        return row["cnt"] if row else 0

    def update_score(
        self,
        root_domain: str,
        risk_score: float,
        score_version: str,
        signal_tags: list[str],
        score_explanation: str,
    ) -> None:
        """Update score fields for an account.

        Args:
            root_domain: Account primary key.
            risk_score: Computed risk score (0-100).
            score_version: Score version (e.g., 'v1').
            signal_tags: List of signal tags (e.g., ['CRITICAL_CVE', 'EXPOSED_DATABASE']).
            score_explanation: JSON string with sub-score breakdown.
        """
        query = """
            UPDATE accounts
            SET risk_score = ?, score_version = ?, signal_tags = ?, score_explanation = ?, scored_at = ?
            WHERE root_domain = ?
        """
        self.execute(
            query,
            {
                "risk_score": risk_score,
                "score_version": score_version,
                "signal_tags": signal_tags,
                "score_explanation": score_explanation,
                "scored_at": datetime.utcnow(),
                "root_domain": root_domain,
            },
        )
        logfire.info("account_repo.score_updated", root_domain=root_domain, risk_score=risk_score)

    def update_enrichment(
        self,
        root_domain: str,
        inferred_company_name: str | None,
        inferred_industry: str | None,
        narrative: str | None,
        outreach_draft: str | None,
    ) -> None:
        """Update enrichment fields for an account.

        Args:
            root_domain: Account primary key.
            inferred_company_name: Company name inferred by LLM.
            inferred_industry: Industry inferred by LLM.
            narrative: Risk narrative (Sonnet output).
            outreach_draft: Outreach email draft (Sonnet output).
        """
        query = """
            UPDATE accounts
            SET inferred_company_name = ?, inferred_industry = ?, narrative = ?,
                outreach_draft = ?, enriched_at = ?
            WHERE root_domain = ?
        """
        self.execute(
            query,
            {
                "inferred_company_name": inferred_company_name,
                "inferred_industry": inferred_industry,
                "narrative": narrative,
                "outreach_draft": outreach_draft,
                "enriched_at": datetime.utcnow(),
                "root_domain": root_domain,
            },
        )
        logfire.info("account_repo.enrichment_updated", root_domain=root_domain)
