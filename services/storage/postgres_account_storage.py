from __future__ import annotations

from datetime import datetime
from typing import Any

import logfire
from sqlalchemy.orm import Session

from services.storage.enums import StorageType, TableType
from services.storage.models import Account
from services.storage.postgres_connection import get_pool
from services.storage.sqlmodel_models import AccountSQL


class PostgresAccountStorageService:
    """PostgreSQL implementation of account storage using SQLModel."""

    storage_type = StorageType.DATABASE
    table_type = TableType.ACCOUNTS

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self._owns_session = session is None

    def _get_session(self) -> Session:
        """Get or create a session."""
        if self.session is not None:
            return self.session
        return get_pool().get_connection()

    def _close_session(self) -> None:
        """Close session if we created it."""
        if self._owns_session and self.session is not None:
            self.session.close()

    def get(self, root_domain: str) -> Account | None:
        """Get account by root domain."""
        session = self._get_session()
        try:
            account_sql = session.query(AccountSQL).filter(
                AccountSQL.root_domain == root_domain
            ).first()
            return self._to_pydantic(account_sql) if account_sql else None
        finally:
            if self._owns_session:
                session.close()

    def list(self, limit: int = 100, offset: int = 0) -> list[Account]:
        """List accounts with pagination."""
        session = self._get_session()
        try:
            accounts_sql = session.query(AccountSQL).offset(offset).limit(limit).all()
            return [self._to_pydantic(a) for a in accounts_sql]
        finally:
            if self._owns_session:
                session.close()

    def create(self, entity: Account) -> Account:
        """Create is not supported for accounts (created via aggregation)."""
        raise NotImplementedError("Accounts are created via aggregation, not direct insert.")

    def update(self, entity: Account) -> Account:
        """Update account."""
        session = self._get_session()
        try:
            account_sql = session.query(AccountSQL).filter(
                AccountSQL.root_domain == entity.root_domain
            ).first()
            if not account_sql:
                raise ValueError(f"Account {entity.root_domain} not found")

            account_sql.risk_score = entity.risk_score
            account_sql.score_version = entity.score_version
            account_sql.signal_tags = entity.signal_tags
            account_sql.score_explanation = entity.score_explanation
            account_sql.scored_at = entity.scored_at
            account_sql.inferred_company_name = entity.inferred_company_name
            account_sql.inferred_industry = entity.inferred_industry
            account_sql.narrative = entity.narrative
            account_sql.outreach_draft = entity.outreach_draft
            account_sql.enriched_at = entity.enriched_at

            session.commit()
            return entity
        finally:
            if self._owns_session:
                session.close()

    def delete(self, root_domain: str) -> bool:
        """Delete is not supported."""
        raise NotImplementedError("Deletion of accounts is not supported.")

    def count(self) -> int:
        """Count non-honeypot accounts."""
        session = self._get_session()
        try:
            return session.query(AccountSQL).filter(
                AccountSQL.excluded_as_honeypot == False  # noqa: E712
            ).count()
        finally:
            if self._owns_session:
                session.close()

    def list_by_score(
        self, min_score: float | None = None, max_score: float | None = None, limit: int = 100
    ) -> list[Account]:
        """List accounts filtered by risk score."""
        session = self._get_session()
        try:
            query = session.query(AccountSQL).filter(
                AccountSQL.excluded_as_honeypot == False  # noqa: E712
            )

            if min_score is not None:
                query = query.filter(AccountSQL.risk_score >= min_score)

            if max_score is not None:
                query = query.filter(AccountSQL.risk_score <= max_score)

            accounts_sql = query.order_by(AccountSQL.risk_score.desc()).limit(limit).all()
            return [self._to_pydantic(a) for a in accounts_sql]
        finally:
            if self._owns_session:
                session.close()

    def list_unscored(self, limit: int = 10000) -> list[Account]:
        """Get unscored accounts (risk_score is NULL)."""
        session = self._get_session()
        try:
            accounts_sql = session.query(AccountSQL).filter(
                AccountSQL.excluded_as_honeypot == False,  # noqa: E712
                AccountSQL.risk_score.is_(None),
            ).limit(limit).all()
            return [self._to_pydantic(a) for a in accounts_sql]
        finally:
            if self._owns_session:
                session.close()

    def list_top_by_score(self, top_n: int = 50) -> list[Account]:
        """Get top N accounts by risk score."""
        session = self._get_session()
        try:
            accounts_sql = session.query(AccountSQL).filter(
                AccountSQL.excluded_as_honeypot == False,  # noqa: E712
                AccountSQL.risk_score.isnot(None),
            ).order_by(AccountSQL.risk_score.desc()).limit(top_n).all()
            return [self._to_pydantic(a) for a in accounts_sql]
        finally:
            if self._owns_session:
                session.close()

    def update_score(
        self,
        root_domain: str,
        risk_score: float,
        score_version: str,
        signal_tags: list[str],
        score_explanation: str,
    ) -> None:
        """Update account score."""
        session = self._get_session()
        try:
            account_sql = session.query(AccountSQL).filter(
                AccountSQL.root_domain == root_domain
            ).first()
            if not account_sql:
                raise ValueError(f"Account {root_domain} not found")

            account_sql.risk_score = risk_score
            account_sql.score_version = score_version
            account_sql.signal_tags = signal_tags
            account_sql.score_explanation = score_explanation
            account_sql.scored_at = datetime.utcnow()

            session.commit()
            logfire.info("account_storage.score_updated", root_domain=root_domain, risk_score=risk_score)
        finally:
            if self._owns_session:
                session.close()

    def update_enrichment(
        self,
        root_domain: str,
        inferred_company_name: str | None,
        inferred_industry: str | None,
        narrative: str | None,
        outreach_draft: str | None,
    ) -> None:
        """Update account enrichment."""
        session = self._get_session()
        try:
            account_sql = session.query(AccountSQL).filter(
                AccountSQL.root_domain == root_domain
            ).first()
            if not account_sql:
                raise ValueError(f"Account {root_domain} not found")

            account_sql.inferred_company_name = inferred_company_name
            account_sql.inferred_industry = inferred_industry
            account_sql.narrative = narrative
            account_sql.outreach_draft = outreach_draft
            account_sql.enriched_at = datetime.utcnow()

            session.commit()
            logfire.info("account_storage.enrichment_updated", root_domain=root_domain)
        finally:
            if self._owns_session:
                session.close()

    def get_top_records_for_account(self, root_domain: str, limit: int = 20) -> list[dict]:
        """Get top N records (staging records) for an account ordered by rank."""
        from services.storage.sqlmodel_models import AccountTopRecordSQL, StagingRecordSQL

        session = self._get_session()
        try:
            top_records_sql = (
                session.query(AccountTopRecordSQL, StagingRecordSQL)
                .join(StagingRecordSQL, AccountTopRecordSQL.record_id == StagingRecordSQL.record_id)
                .filter(AccountTopRecordSQL.root_domain == root_domain)
                .order_by(AccountTopRecordSQL.rank)
                .limit(limit)
                .all()
            )

            top_records = []
            for top_record_sql, staging_record_sql in top_records_sql:
                top_records.append({
                    "rank": top_record_sql.rank,
                    "ip": staging_record_sql.ip,
                    "port": staging_record_sql.port,
                    "transport": staging_record_sql.transport,
                    "product": staging_record_sql.product,
                    "version": staging_record_sql.version,
                    "os": staging_record_sql.os,
                    "device": staging_record_sql.device,
                    "tags": staging_record_sql.tags,
                    "has_vulns": staging_record_sql.has_vulns,
                    "vuln_count": staging_record_sql.vuln_count,
                    "max_cvss": staging_record_sql.max_cvss,
                    "max_epss": staging_record_sql.max_epss,
                    "is_database_port": staging_record_sql.is_database_port,
                    "is_legacy_protocol": staging_record_sql.is_legacy_protocol,
                    "is_iot_ot_device": staging_record_sql.is_iot_ot_device,
                    "is_eol_product": staging_record_sql.is_eol_product,
                    "http_title": staging_record_sql.http_title,
                    "http_server": staging_record_sql.http_server,
                    "http_status": staging_record_sql.http_status,
                })
            return top_records
        finally:
            if self._owns_session:
                session.close()

    @staticmethod
    def _to_pydantic(account_sql: AccountSQL | None) -> Account | None:
        """Convert SQLModel to Pydantic model."""
        if not account_sql:
            return None
        return Account(
            root_domain=account_sql.root_domain,
            record_count=account_sql.record_count,
            asset_count=account_sql.asset_count,
            distinct_ips=account_sql.distinct_ips,
            distinct_ports=account_sql.distinct_ports,
            port_list=account_sql.port_list or [],
            countries=account_sql.countries or [],
            primary_country_code=account_sql.primary_country_code,
            primary_org=account_sql.primary_org,
            cloud_or_cdn_fronted=account_sql.cloud_or_cdn_fronted,
            vuln_count_total=account_sql.vuln_count_total,
            vuln_count_critical=account_sql.vuln_count_critical,
            max_cvss=account_sql.max_cvss,
            max_epss=account_sql.max_epss,
            top_cve_ids=account_sql.top_cve_ids or [],
            exposed_database_count=account_sql.exposed_database_count,
            legacy_protocol_count=account_sql.legacy_protocol_count,
            weak_tls_count=account_sql.weak_tls_count,
            self_signed_cert_count=account_sql.self_signed_cert_count,
            eol_product_count=account_sql.eol_product_count,
            iot_ot_device_count=account_sql.iot_ot_device_count,
            honeypot_flagged=account_sql.honeypot_flagged,
            excluded_as_honeypot=account_sql.excluded_as_honeypot,
            sample_http_titles=account_sql.sample_http_titles or [],
            sample_products=account_sql.sample_products or [],
            first_seen=account_sql.first_seen,
            last_seen=account_sql.last_seen,
            snapshot_date=account_sql.snapshot_date,
            risk_score=account_sql.risk_score,
            score_version=account_sql.score_version,
            signal_tags=account_sql.signal_tags or [],
            score_explanation=account_sql.score_explanation,
            scored_at=account_sql.scored_at,
            inferred_company_name=account_sql.inferred_company_name,
            inferred_industry=account_sql.inferred_industry,
            narrative=account_sql.narrative,
            outreach_draft=account_sql.outreach_draft,
            enriched_at=account_sql.enriched_at,
        )

    @staticmethod
    def _from_pydantic(account: Account) -> AccountSQL:
        """Convert Pydantic to SQLModel."""
        return AccountSQL(
            root_domain=account.root_domain,
            record_count=account.record_count,
            asset_count=account.asset_count,
            distinct_ips=account.distinct_ips,
            distinct_ports=account.distinct_ports,
            port_list=account.port_list,
            countries=account.countries,
            primary_country_code=account.primary_country_code,
            primary_org=account.primary_org,
            cloud_or_cdn_fronted=account.cloud_or_cdn_fronted,
            vuln_count_total=account.vuln_count_total,
            vuln_count_critical=account.vuln_count_critical,
            max_cvss=account.max_cvss,
            max_epss=account.max_epss,
            top_cve_ids=account.top_cve_ids,
            exposed_database_count=account.exposed_database_count,
            legacy_protocol_count=account.legacy_protocol_count,
            weak_tls_count=account.weak_tls_count,
            self_signed_cert_count=account.self_signed_cert_count,
            eol_product_count=account.eol_product_count,
            iot_ot_device_count=account.iot_ot_device_count,
            honeypot_flagged=account.honeypot_flagged,
            excluded_as_honeypot=account.excluded_as_honeypot,
            sample_http_titles=account.sample_http_titles,
            sample_products=account.sample_products,
            first_seen=account.first_seen,
            last_seen=account.last_seen,
            snapshot_date=account.snapshot_date,
            risk_score=account.risk_score,
            score_version=account.score_version,
            signal_tags=account.signal_tags,
            score_explanation=account.score_explanation,
            scored_at=account.scored_at,
            inferred_company_name=account.inferred_company_name,
            inferred_industry=account.inferred_industry,
            narrative=account.narrative,
            outreach_draft=account.outreach_draft,
            enriched_at=account.enriched_at,
        )
