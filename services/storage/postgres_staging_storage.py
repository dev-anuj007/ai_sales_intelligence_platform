from __future__ import annotations

from typing import Any

import logfire
from sqlalchemy.orm import Session

from services.storage.enums import StorageType, TableType
from services.storage.models import StagingRecord
from services.storage.postgres_connection import get_pool
from services.storage.sqlmodel_models import StagingRecordSQL


class PostgresStagingStorageService:
    """PostgreSQL implementation of staging record storage using SQLModel."""

    storage_type = StorageType.DATABASE
    table_type = TableType.STAGING_RECORDS

    def __init__(self, session: Session | None = None) -> None:
        self.session = session
        self._owns_session = session is None

    def _get_session(self) -> Session:
        """Get or create a session."""
        if self.session is not None:
            return self.session
        return get_pool().get_connection()

    def get(self, record_id: int) -> StagingRecord | None:
        """Get staging record by ID."""
        session = self._get_session()
        try:
            record_sql = session.query(StagingRecordSQL).filter(
                StagingRecordSQL.record_id == record_id
            ).first()
            return self._to_pydantic(record_sql) if record_sql else None
        finally:
            if self._owns_session:
                session.close()

    def list(self, limit: int = 100, offset: int = 0) -> list[StagingRecord]:
        """List staging records with pagination."""
        session = self._get_session()
        try:
            records_sql = session.query(StagingRecordSQL).offset(offset).limit(limit).all()
            return [self._to_pydantic(r) for r in records_sql]
        finally:
            if self._owns_session:
                session.close()

    def create(self, entity: StagingRecord) -> StagingRecord:
        """Create is not supported (use bulk_insert)."""
        raise NotImplementedError("Use bulk_insert for performance.")

    def update(self, entity: StagingRecord) -> StagingRecord:
        """Update is not supported (staging records are immutable)."""
        raise NotImplementedError("Staging records are immutable after insert.")

    def delete(self, record_id: int) -> bool:
        """Delete is not supported."""
        raise NotImplementedError("Staging records are not deleted.")

    def count(self) -> int:
        """Count total staging records."""
        session = self._get_session()
        try:
            return session.query(StagingRecordSQL).count()
        finally:
            if self._owns_session:
                session.close()

    def bulk_insert(self, records: list[dict[str, Any]]) -> int:
        """Bulk insert staging records."""
        if not records:
            return 0

        session = self._get_session()
        try:
            inserted = 0
            for record in records:
                try:
                    record_sql = StagingRecordSQL(**record)
                    session.add(record_sql)
                    inserted += 1
                except Exception as e:
                    logfire.warning("staging_storage.insert_failed", error=str(e), record_id=record.get("record_id"))
                    continue

            session.commit()
            return inserted
        finally:
            if self._owns_session:
                session.close()

    def list_by_domain(self, root_domain: str, limit: int = 1000) -> list[StagingRecord]:
        """List staging records by root domain."""
        session = self._get_session()
        try:
            records_sql = session.query(StagingRecordSQL).filter(
                StagingRecordSQL.root_domain == root_domain
            ).limit(limit).all()
            return [self._to_pydantic(r) for r in records_sql]
        finally:
            if self._owns_session:
                session.close()

    @staticmethod
    def _to_pydantic(record_sql: StagingRecordSQL | None) -> StagingRecord | None:
        """Convert SQLModel to Pydantic model."""
        if not record_sql:
            return None
        return StagingRecord(
            record_id=record_sql.record_id,
            ip=record_sql.ip,
            port=record_sql.port,
            transport=record_sql.transport,
            root_domain=record_sql.root_domain,
            hostnames=record_sql.hostnames,
            domains=record_sql.domains,
            org=record_sql.org,
            isp=record_sql.isp,
            asn=record_sql.asn,
            country_code=record_sql.country_code,
            region=record_sql.region,
            city=record_sql.city,
            latitude=record_sql.latitude,
            longitude=record_sql.longitude,
            ts=record_sql.ts,
            product=record_sql.product,
            version=record_sql.version,
            os=record_sql.os,
            device=record_sql.device,
            devicetype=record_sql.devicetype,
            cpe=record_sql.cpe,
            tags=record_sql.tags,
            is_infra_noise=record_sql.is_infra_noise,
            has_vulns=record_sql.has_vulns,
            vuln_count=record_sql.vuln_count,
            max_cvss=record_sql.max_cvss,
            max_epss=record_sql.max_epss,
            vuln_ids=record_sql.vuln_ids,
            has_ssl=record_sql.has_ssl,
            ssl_self_signed=record_sql.ssl_self_signed,
            ssl_version_weak=record_sql.ssl_version_weak,
            ssl_jarm=record_sql.ssl_jarm,
            http_title=record_sql.http_title,
            http_server=record_sql.http_server,
            http_status=record_sql.http_status,
            has_securitytxt=record_sql.has_securitytxt,
            is_database_port=record_sql.is_database_port,
            is_legacy_protocol=record_sql.is_legacy_protocol,
            is_iot_ot_device=record_sql.is_iot_ot_device,
            is_eol_product=record_sql.is_eol_product,
            is_honeypot=record_sql.is_honeypot,
            data_snippet=record_sql.data_snippet,
            shodan_module=record_sql.shodan_module,
            ingested_at=record_sql.ingested_at,
        )
