"""Repository for staging_records table (raw Shodan scan data).

Handles bulk insert of normalized records during pipeline ingest.
"""

from typing import Any

import duckdb
import logfire

from sales_intel.data.models import StagingRecord
from sales_intel.data.repository import BaseRepository


class StagingRecordRepository(BaseRepository[StagingRecord]):
    """Repository for raw staging records."""

    def get_by_id(self, id_value: int) -> StagingRecord | None:
        """Retrieve a staging record by record_id."""
        row = self.fetch_one("SELECT * FROM staging_records WHERE record_id = ?", {"record_id": id_value})
        return StagingRecord(**row) if row else None

    def list(self, limit: int = 100, offset: int = 0) -> list[StagingRecord]:
        """List staging records with pagination."""
        rows = self.fetch_all(
            "SELECT * FROM staging_records ORDER BY record_id LIMIT ? OFFSET ?",
            {"limit": limit, "offset": offset},
        )
        return [StagingRecord(**row) for row in rows]

    def create(self, entity: StagingRecord) -> StagingRecord:
        """Insert a single staging record."""
        query = """
            INSERT INTO staging_records (
                record_id, ip, port, transport, root_domain, hostnames, domains, org, isp, asn,
                country_code, region, city, latitude, longitude, ts, product, version, os, device,
                devicetype, cpe, tags, is_infra_noise, has_vulns, vuln_count, max_cvss, max_epss,
                vuln_ids, has_ssl, ssl_self_signed, ssl_version_weak, ssl_jarm, http_title,
                http_server, http_status, has_securitytxt, is_database_port, is_legacy_protocol,
                is_iot_ot_device, is_eol_product, is_honeypot, data_snippet, shodan_module
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
        """
        self.execute(query, entity.model_dump())
        return entity

    def bulk_insert(self, records: list[dict[str, Any]]) -> int:
        """Bulk insert records via DuckDB Appender (fast, efficient).

        Args:
            records: List of record dicts (from normalizer).

        Returns:
            Number of records inserted.
        """
        if not records:
            return 0

        # Use DuckDB Appender for bulk insert (faster than individual inserts)
        try:
            appender = self.connection.appender("staging_records")
            for record in records:
                # Map dict keys to table columns in order
                row = (
                    record.get("record_id"),
                    record.get("ip"),
                    record.get("port"),
                    record.get("transport"),
                    record.get("root_domain"),
                    record.get("hostnames", []),
                    record.get("domains", []),
                    record.get("org"),
                    record.get("isp"),
                    record.get("asn"),
                    record.get("country_code"),
                    record.get("region"),
                    record.get("city"),
                    record.get("latitude"),
                    record.get("longitude"),
                    record.get("ts"),
                    record.get("product"),
                    record.get("version"),
                    record.get("os"),
                    record.get("device"),
                    record.get("devicetype"),
                    record.get("cpe", []),
                    record.get("tags", []),
                    record.get("is_infra_noise", False),
                    record.get("has_vulns", False),
                    record.get("vuln_count", 0),
                    record.get("max_cvss"),
                    record.get("max_epss"),
                    record.get("vuln_ids", []),
                    record.get("has_ssl", False),
                    record.get("ssl_self_signed", False),
                    record.get("ssl_version_weak", False),
                    record.get("ssl_jarm"),
                    record.get("http_title"),
                    record.get("http_server"),
                    record.get("http_status"),
                    record.get("has_securitytxt", False),
                    record.get("is_database_port", False),
                    record.get("is_legacy_protocol", False),
                    record.get("is_iot_ot_device", False),
                    record.get("is_eol_product", False),
                    record.get("is_honeypot", False),
                    record.get("data_snippet"),
                    record.get("shodan_module"),
                )
                appender.append(row)
            appender.close()
            logfire.info("staging_repo.bulk_insert", count=len(records))
            return len(records)
        except Exception as e:
            logfire.error("staging_repo.bulk_insert_failed", error=str(e))
            raise

    def count_by_root_domain(self, root_domain: str) -> int:
        """Count records for a given root_domain."""
        row = self.fetch_one(
            "SELECT COUNT(*) as cnt FROM staging_records WHERE root_domain = ?",
            {"root_domain": root_domain},
        )
        return row["cnt"] if row else 0

    def count_all(self) -> int:
        """Count all staging records."""
        row = self.fetch_one("SELECT COUNT(*) as cnt FROM staging_records")
        return row["cnt"] if row else 0

    def count_noise(self) -> int:
        """Count records marked as infra noise."""
        row = self.fetch_one("SELECT COUNT(*) as cnt FROM staging_records WHERE is_infra_noise = true")
        return row["cnt"] if row else 0

    def update(self, entity: StagingRecord) -> StagingRecord:
        """Update a staging record (rarely used; mostly for testing)."""
        raise NotImplementedError("StagingRecordRepository does not support update()")

    def delete(self, id_value: int) -> bool:
        """Delete a staging record (rarely used; mostly for testing)."""
        raise NotImplementedError("StagingRecordRepository does not support delete()")
