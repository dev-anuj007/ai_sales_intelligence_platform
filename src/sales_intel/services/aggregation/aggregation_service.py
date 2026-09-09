"""Aggregation service: groups staging records into accounts.

Executes SQL to aggregate per-root-domain, creating the accounts table
and the account_top_records index for LLM grounding.
"""

from typing import Any

import duckdb
import logfire

from sales_intel.data.account_repo import AccountRepository


class AggregationService:
    """Service for aggregating staging records into accounts."""

    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        """Initialize aggregation service.

        Args:
            connection: DuckDB connection.
        """
        self.connection = connection
        self.account_repo = AccountRepository(connection)

    def aggregate_staging_to_accounts(self) -> dict[str, Any]:
        """Aggregate staging_records → accounts and account_top_records via SQL.

        Returns:
            Summary dict with counts.
        """
        logfire.info("aggregation_service.start")

        try:
            # Aggregate staging_records into accounts
            self._aggregate_accounts_sql()

            # Build account_top_records index
            self._build_account_top_records_index()

            # Mark honeypot-only accounts
            self._mark_excluded_honeypots()

            # Get summary counts
            account_count = self.account_repo.count_all()
            excluded_honeypot = self.account_repo.count_excluded_honeypot()

            summary = {
                "status": "success",
                "accounts_created": account_count,
                "excluded_as_honeypot": excluded_honeypot,
            }

            logfire.info("aggregation_service.complete", **summary)
            return summary

        except Exception as e:
            logfire.error("aggregation_service.failed", error=str(e))
            raise

    def _aggregate_accounts_sql(self) -> None:
        """Execute SQL to aggregate staging_records → accounts."""
        sql = """
            INSERT INTO accounts (
                root_domain, record_count, asset_count, distinct_ips, distinct_ports,
                port_list, countries, primary_country_code, primary_org, cloud_or_cdn_fronted,
                vuln_count_total, vuln_count_critical, max_cvss, max_epss, top_cve_ids,
                exposed_database_count, legacy_protocol_count, weak_tls_count,
                self_signed_cert_count, eol_product_count, iot_ot_device_count,
                honeypot_flagged, sample_http_titles, sample_products,
                first_seen, last_seen, snapshot_date
            )
            SELECT
                root_domain,
                COUNT(*) as record_count,
                COUNT(*) FILTER (WHERE NOT is_infra_noise) as asset_count,
                COUNT(DISTINCT ip) as distinct_ips,
                COUNT(DISTINCT port) as distinct_ports,
                array_agg(DISTINCT port) as port_list,
                array_agg(DISTINCT country_code) FILTER (WHERE country_code IS NOT NULL) as countries,
                mode(country_code) as primary_country_code,
                mode(org) as primary_org,
                bool_or(list_contains(tags, 'cdn') OR list_contains(tags, 'cloud')) as cloud_or_cdn_fronted,
                COALESCE(SUM(vuln_count), 0) as vuln_count_total,
                COALESCE(SUM(CASE WHEN max_cvss >= 9 OR (max_cvss >= 7 AND max_epss >= 0.5) THEN 1 ELSE 0 END), 0) as vuln_count_critical,
                MAX(max_cvss) as max_cvss,
                MAX(max_epss) as max_epss,
                array_agg(DISTINCT vuln_ids[1:1]) FILTER (WHERE vuln_ids IS NOT NULL AND list_length(vuln_ids) > 0) as top_cve_ids,
                SUM(CASE WHEN is_database_port THEN 1 ELSE 0 END) as exposed_database_count,
                SUM(CASE WHEN is_legacy_protocol THEN 1 ELSE 0 END) as legacy_protocol_count,
                SUM(CASE WHEN ssl_version_weak THEN 1 ELSE 0 END) as weak_tls_count,
                SUM(CASE WHEN ssl_self_signed THEN 1 ELSE 0 END) as self_signed_cert_count,
                SUM(CASE WHEN is_eol_product THEN 1 ELSE 0 END) as eol_product_count,
                SUM(CASE WHEN is_iot_ot_device THEN 1 ELSE 0 END) as iot_ot_device_count,
                bool_or(is_honeypot) as honeypot_flagged,
                array_slice(array_agg(DISTINCT http_title) FILTER (WHERE http_title IS NOT NULL), 1, 5) as sample_http_titles,
                array_slice(array_agg(DISTINCT product) FILTER (WHERE product IS NOT NULL), 1, 5) as sample_products,
                MIN(ts) as first_seen,
                MAX(ts) as last_seen,
                '2026-09-07'::VARCHAR as snapshot_date
            FROM staging_records
            WHERE root_domain IS NOT NULL
            GROUP BY root_domain
            ON CONFLICT (root_domain) DO UPDATE SET
                record_count = EXCLUDED.record_count,
                asset_count = EXCLUDED.asset_count,
                distinct_ips = EXCLUDED.distinct_ips,
                distinct_ports = EXCLUDED.distinct_ports,
                port_list = EXCLUDED.port_list,
                countries = EXCLUDED.countries,
                primary_country_code = EXCLUDED.primary_country_code,
                primary_org = EXCLUDED.primary_org,
                cloud_or_cdn_fronted = EXCLUDED.cloud_or_cdn_fronted,
                vuln_count_total = EXCLUDED.vuln_count_total,
                vuln_count_critical = EXCLUDED.vuln_count_critical,
                max_cvss = EXCLUDED.max_cvss,
                max_epss = EXCLUDED.max_epss,
                top_cve_ids = EXCLUDED.top_cve_ids,
                exposed_database_count = EXCLUDED.exposed_database_count,
                legacy_protocol_count = EXCLUDED.legacy_protocol_count,
                weak_tls_count = EXCLUDED.weak_tls_count,
                self_signed_cert_count = EXCLUDED.self_signed_cert_count,
                eol_product_count = EXCLUDED.eol_product_count,
                iot_ot_device_count = EXCLUDED.iot_ot_device_count,
                honeypot_flagged = EXCLUDED.honeypot_flagged,
                sample_http_titles = EXCLUDED.sample_http_titles,
                sample_products = EXCLUDED.sample_products,
                first_seen = EXCLUDED.first_seen,
                last_seen = EXCLUDED.last_seen
        """
        self.connection.execute(sql)
        logfire.info("aggregation_service.accounts_aggregated")

    def _build_account_top_records_index(self) -> None:
        """Build index of top 20 most-interesting records per account for LLM grounding."""
        sql = """
            INSERT INTO account_top_records (root_domain, record_id, rank)
            SELECT root_domain, record_id, rn FROM (
                SELECT
                    root_domain, record_id,
                    row_number() OVER (
                        PARTITION BY root_domain
                        ORDER BY has_vulns DESC, max_cvss DESC NULLS LAST,
                                 is_database_port DESC, is_legacy_protocol DESC,
                                 is_iot_ot_device DESC, is_eol_product DESC
                    ) AS rn
                FROM staging_records
                WHERE root_domain IS NOT NULL AND NOT is_infra_noise
            )
            WHERE rn <= 20
            ON CONFLICT (root_domain, record_id) DO NOTHING
        """
        self.connection.execute(sql)
        logfire.info("aggregation_service.account_top_records_built")

    def _mark_excluded_honeypots(self) -> None:
        """Mark accounts as excluded if all their assets are honeypots."""
        sql = """
            UPDATE accounts
            SET excluded_as_honeypot = true
            WHERE asset_count = 0 AND honeypot_flagged = true
        """
        self.connection.execute(sql)
        count = self.connection.execute(
            "SELECT COUNT(*) as cnt FROM accounts WHERE excluded_as_honeypot = true"
        ).fetchall()[0][0]
        logfire.info("aggregation_service.honeypots_marked", count=count)
