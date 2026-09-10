from __future__ import annotations

from typing import Any

import logfire
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from services.storage.enums import StorageType, TableType
from services.storage.models import Account
from services.storage.postgres_connection import get_pool
from services.storage.sqlmodel_models import AccountSQL


class PostgresAsyncAccountStorageService:
    """Async PostgreSQL implementation of account storage using SQLModel."""

    storage_type = StorageType.DATABASE
    table_type = TableType.ACCOUNTS

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session
        self._owns_session = session is None

    async def _get_session(self) -> AsyncSession:
        """Get or create an async session."""
        if self.session is not None:
            return self.session
        return await get_pool().get_async_connection()

    async def _close_session(self) -> None:
        """Close session if we created it."""
        if self._owns_session and self.session is not None:
            await self.session.close()

    async def get(self, root_domain: str) -> Account | None:
        """Get account by root domain."""
        session = await self._get_session()
        try:
            stmt = select(AccountSQL).where(AccountSQL.root_domain == root_domain)
            result = await session.execute(stmt)
            account_sql = result.scalars().first()
            return self._to_pydantic(account_sql) if account_sql else None
        finally:
            if self._owns_session:
                await session.close()

    async def list(self, limit: int = 100, offset: int = 0) -> list[Account]:
        """List accounts with pagination."""
        session = await self._get_session()
        try:
            stmt = select(AccountSQL).offset(offset).limit(limit)
            result = await session.execute(stmt)
            accounts_sql = result.scalars().all()
            return [self._to_pydantic(a) for a in accounts_sql]
        finally:
            if self._owns_session:
                await session.close()

    async def create(self, entity: Account) -> Account:
        """Create is not supported for accounts (created via aggregation)."""
        raise NotImplementedError("Accounts are created via aggregation, not direct insert.")

    async def update(self, entity: Account) -> Account:
        """Update account."""
        session = await self._get_session()
        try:
            stmt = select(AccountSQL).where(AccountSQL.root_domain == entity.root_domain)
            result = await session.execute(stmt)
            account_sql = result.scalars().first()

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

            await session.commit()
            return entity
        finally:
            if self._owns_session:
                await session.close()

    async def delete(self, root_domain: str) -> bool:
        """Delete is not supported."""
        raise NotImplementedError("Deletion of accounts is not supported.")

    async def count(self) -> int:
        """Count non-honeypot accounts."""
        session = await self._get_session()
        try:
            stmt = select(func.count()).select_from(AccountSQL).where(
                AccountSQL.excluded_as_honeypot == False  # noqa: E712
            )
            result = await session.execute(stmt)
            return result.scalar() or 0
        finally:
            if self._owns_session:
                await session.close()

    async def list_by_score(
        self, min_score: float | None = None, max_score: float | None = None, limit: int = 100
    ) -> list[Account]:
        """List accounts filtered by risk score."""
        session = await self._get_session()
        try:
            stmt = select(AccountSQL).where(
                AccountSQL.excluded_as_honeypot == False  # noqa: E712
            )

            if min_score is not None:
                stmt = stmt.where(AccountSQL.risk_score >= min_score)

            if max_score is not None:
                stmt = stmt.where(AccountSQL.risk_score <= max_score)

            stmt = stmt.order_by(AccountSQL.risk_score.desc()).limit(limit)
            result = await session.execute(stmt)
            accounts_sql = result.scalars().all()
            return [self._to_pydantic(a) for a in accounts_sql]
        finally:
            if self._owns_session:
                await session.close()

    async def list_unscored(self, limit: int = 10000) -> list[Account]:
        """Get unscored accounts (risk_score is NULL)."""
        session = await self._get_session()
        try:
            stmt = select(AccountSQL).where(
                AccountSQL.excluded_as_honeypot == False,  # noqa: E712
                AccountSQL.risk_score.is_(None),
            ).limit(limit)
            result = await session.execute(stmt)
            accounts_sql = result.scalars().all()
            return [self._to_pydantic(a) for a in accounts_sql]
        finally:
            if self._owns_session:
                await session.close()

    async def list_top_by_score(self, top_n: int = 50) -> list[Account]:
        """Get top N accounts by risk score."""
        session = await self._get_session()
        try:
            stmt = select(AccountSQL).where(
                AccountSQL.excluded_as_honeypot == False,  # noqa: E712
                AccountSQL.risk_score.isnot(None),
            ).order_by(AccountSQL.risk_score.desc()).limit(top_n)
            result = await session.execute(stmt)
            accounts_sql = result.scalars().all()
            return [self._to_pydantic(a) for a in accounts_sql]
        finally:
            if self._owns_session:
                await session.close()

    async def update_score(
        self,
        root_domain: str,
        risk_score: float,
        score_version: str,
        signal_tags: list[str],
        score_explanation: str,
    ) -> None:
        """Update account risk score and explanation."""
        session = await self._get_session()
        try:
            stmt = select(AccountSQL).where(AccountSQL.root_domain == root_domain)
            result = await session.execute(stmt)
            account_sql = result.scalars().first()

            if account_sql:
                account_sql.risk_score = risk_score
                account_sql.score_version = score_version
                account_sql.signal_tags = signal_tags
                account_sql.score_explanation = score_explanation
                await session.commit()
                logfire.info("account_storage.score_updated", root_domain=root_domain, score=risk_score)
        finally:
            if self._owns_session:
                await session.close()

    async def update_enrichment(
        self,
        root_domain: str,
        inferred_company_name: str | None,
        inferred_industry: str | None,
        narrative: str | None,
        outreach_draft: str | None,
    ) -> None:
        """Update account enrichment data."""
        session = await self._get_session()
        try:
            stmt = select(AccountSQL).where(AccountSQL.root_domain == root_domain)
            result = await session.execute(stmt)
            account_sql = result.scalars().first()

            if account_sql:
                account_sql.inferred_company_name = inferred_company_name
                account_sql.inferred_industry = inferred_industry
                account_sql.narrative = narrative
                account_sql.outreach_draft = outreach_draft
                await session.commit()
                logfire.info("account_storage.enrichment_updated", root_domain=root_domain)
        finally:
            if self._owns_session:
                await session.close()

    async def get_top_records_for_account(self, root_domain: str, limit: int = 20) -> list[dict]:
        """Get top N records (staging records) for an account ordered by rank."""
        from services.storage.sqlmodel_models import AccountTopRecordSQL, StagingRecordSQL

        session = await self._get_session()
        try:
            stmt = (
                select(AccountTopRecordSQL, StagingRecordSQL)
                .join(StagingRecordSQL, AccountTopRecordSQL.record_id == StagingRecordSQL.record_id)
                .where(AccountTopRecordSQL.root_domain == root_domain)
                .order_by(AccountTopRecordSQL.rank)
                .limit(limit)
            )
            result = await session.execute(stmt)
            rows = result.all()

            top_records = []
            for top_record_sql, staging_record_sql in rows:
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
                await session.close()

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
            port_list=account_sql.port_list,
            countries=account_sql.countries,
            primary_country_code=account_sql.primary_country_code,
            primary_org=account_sql.primary_org,
            cloud_or_cdn_fronted=account_sql.cloud_or_cdn_fronted,
            vuln_count_total=account_sql.vuln_count_total,
            vuln_count_critical=account_sql.vuln_count_critical,
            max_cvss=account_sql.max_cvss,
            max_epss=account_sql.max_epss,
            exposed_database_count=account_sql.exposed_database_count,
            legacy_protocol_count=account_sql.legacy_protocol_count,
            weak_tls_count=account_sql.weak_tls_count,
            self_signed_cert_count=account_sql.self_signed_cert_count,
            eol_product_count=account_sql.eol_product_count,
            iot_ot_device_count=account_sql.iot_ot_device_count,
            honeypot_flagged=account_sql.honeypot_flagged,
            excluded_as_honeypot=account_sql.excluded_as_honeypot,
            sample_http_titles=account_sql.sample_http_titles,
            sample_products=account_sql.sample_products,
            first_seen=account_sql.first_seen,
            last_seen=account_sql.last_seen,
            snapshot_date=account_sql.snapshot_date,
            risk_score=account_sql.risk_score,
            score_version=account_sql.score_version,
            signal_tags=account_sql.signal_tags,
            score_explanation=account_sql.score_explanation,
            scored_at=account_sql.scored_at,
            inferred_company_name=account_sql.inferred_company_name,
            inferred_industry=account_sql.inferred_industry,
            narrative=account_sql.narrative,
            outreach_draft=account_sql.outreach_draft,
            enriched_at=account_sql.enriched_at,
        )
