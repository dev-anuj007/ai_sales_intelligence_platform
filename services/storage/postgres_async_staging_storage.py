from __future__ import annotations

from typing import Any

import logfire
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.storage.enums import StorageType, TableType
from services.storage.models import StagingRecord
from services.storage.postgres_connection import get_pool
from services.storage.sqlmodel_models import StagingRecordSQL


class PostgresAsyncStagingStorageService:
	"""Async PostgreSQL implementation of staging record storage using SQLModel."""

	storage_type = StorageType.DATABASE
	table_type = TableType.STAGING_RECORDS

	def __init__(self, session: AsyncSession | None = None) -> None:
		self.session = session
		self._owns_session = session is None

	async def _get_session(self) -> AsyncSession:
		"""Get or create an async session."""
		if self.session is not None:
			return self.session
		return await get_pool().get_async_connection()

	async def get(self, record_id: int) -> StagingRecord | None:
		"""Get staging record by ID."""
		session = await self._get_session()
		try:
			stmt = select(StagingRecordSQL).where(StagingRecordSQL.record_id == record_id)
			result = await session.execute(stmt)
			record_sql = result.scalars().first()
			return self._to_pydantic(record_sql) if record_sql else None
		finally:
			if self._owns_session:
				await session.close()

	async def list(self, limit: int = 100, offset: int = 0) -> list[StagingRecord]:
		"""List staging records with pagination."""
		session = await self._get_session()
		try:
			stmt = select(StagingRecordSQL).offset(offset).limit(limit)
			result = await session.execute(stmt)
			records_sql = result.scalars().all()
			return [self._to_pydantic(r) for r in records_sql]
		finally:
			if self._owns_session:
				await session.close()

	async def create(self, entity: StagingRecord) -> StagingRecord:
		"""Create is not supported (use bulk_insert)."""
		raise NotImplementedError("Use bulk_insert for performance.")

	async def update(self, entity: StagingRecord) -> StagingRecord:
		"""Update is not supported (staging records are immutable)."""
		raise NotImplementedError("Staging records are immutable after insert.")

	async def delete(self, record_id: int) -> bool:
		"""Delete is not supported."""
		raise NotImplementedError("Staging records are not deleted.")

	async def count(self) -> int:
		"""Count total staging records."""
		session = await self._get_session()
		try:
			stmt = select(StagingRecordSQL)
			result = await session.execute(stmt)
			records = result.scalars().all()
			return len(records)
		finally:
			if self._owns_session:
				await session.close()

	async def bulk_insert(self, records: list[dict[str, Any]]) -> int:
		"""Bulk insert staging records."""
		if not records:
			return 0

		session = await self._get_session()
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

			await session.commit()
			return inserted
		finally:
			if self._owns_session:
				await session.close()

	async def list_by_domain(self, root_domain: str, limit: int = 1000) -> list[StagingRecord]:
		"""List staging records by root domain."""
		session = await self._get_session()
		try:
			stmt = select(StagingRecordSQL).where(
				StagingRecordSQL.root_domain == root_domain
			).limit(limit)
			result = await session.execute(stmt)
			records_sql = result.scalars().all()
			return [self._to_pydantic(r) for r in records_sql]
		finally:
			if self._owns_session:
				await session.close()

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
