from __future__ import annotations

from typing import Any

from sqlalchemy import text

from services.logger.factory import get_logger
from services.logger.context import TraceContext
from services.storage import get_pool


class AggregationService:
	def __init__(self) -> None:
		self.pool = get_pool()
		self.logger = get_logger()

	async def aggregate_staging_to_accounts(self) -> dict[str, Any]:
		span_id = TraceContext.new_span_id("aggregation")
		self.logger.info("aggregation_service.start")

		connection = await self.pool.get_async_connection()

		try:
			await self._aggregate_accounts_sql(connection)
			await self._build_account_top_records_index(connection)
			await self._mark_excluded_honeypots(connection)

			result = await connection.execute(
				text("SELECT COUNT(*) as cnt FROM accounts WHERE excluded_as_honeypot = false")
			)
			account_count = result.fetchall()[0][0]

			result = await connection.execute(
				text("SELECT COUNT(*) as cnt FROM accounts WHERE excluded_as_honeypot = true")
			)
			excluded_honeypot = result.fetchall()[0][0]

			summary = {
				"status": "success",
				"accounts_created": account_count,
				"excluded_as_honeypot": excluded_honeypot,
			}

			self.logger.info("aggregation_service.complete", **summary)
			return summary

		except Exception as e:
			self.logger.error("aggregation_service.failed", error=e)
			raise
		finally:
			await connection.close()

	async def _aggregate_accounts_sql(self, connection: Any) -> None:
		TraceContext.new_span_id("aggregate_sql")
		sql = text("""
			INSERT INTO accounts (
				root_domain, record_count, asset_count, distinct_ips, distinct_ports,
				port_list, countries, primary_country_code, primary_org, cloud_or_cdn_fronted,
				vuln_count_total, vuln_count_critical, max_cvss, max_epss, top_cve_ids,
				exposed_database_count, legacy_protocol_count, weak_tls_count,
				self_signed_cert_count, eol_product_count, iot_ot_device_count,
				honeypot_flagged, excluded_as_honeypot, sample_http_titles, sample_products,
				first_seen, last_seen, snapshot_date
			)
			SELECT
				root_domain,
				COUNT(*) as record_count,
				SUM(CASE WHEN NOT is_infra_noise THEN 1 ELSE 0 END) as asset_count,
				COUNT(DISTINCT ip) as distinct_ips,
				COUNT(DISTINCT port) as distinct_ports,
				TO_JSON(ARRAY_AGG(DISTINCT port)) as port_list,
				TO_JSON(ARRAY_AGG(DISTINCT country_code) FILTER (WHERE country_code IS NOT NULL)) as countries,
				(ARRAY_AGG(country_code) FILTER (WHERE country_code IS NOT NULL))[1] as primary_country_code,
				(ARRAY_AGG(org) FILTER (WHERE org IS NOT NULL))[1] as primary_org,
				bool_or(tags::text LIKE '%cdn%' OR tags::text LIKE '%cloud%') as cloud_or_cdn_fronted,
				COALESCE(SUM(vuln_count), 0) as vuln_count_total,
				COALESCE(SUM(CASE WHEN max_cvss >= 9 OR (max_cvss >= 7 AND max_epss >= 0.5) THEN 1 ELSE 0 END), 0) as vuln_count_critical,
				MAX(max_cvss) as max_cvss,
				MAX(max_epss) as max_epss,
				'[]'::json as top_cve_ids,
				SUM(CASE WHEN is_database_port THEN 1 ELSE 0 END) as exposed_database_count,
				SUM(CASE WHEN is_legacy_protocol THEN 1 ELSE 0 END) as legacy_protocol_count,
				SUM(CASE WHEN ssl_version_weak THEN 1 ELSE 0 END) as weak_tls_count,
				SUM(CASE WHEN ssl_self_signed THEN 1 ELSE 0 END) as self_signed_cert_count,
				SUM(CASE WHEN is_eol_product THEN 1 ELSE 0 END) as eol_product_count,
				SUM(CASE WHEN is_iot_ot_device THEN 1 ELSE 0 END) as iot_ot_device_count,
				bool_or(is_honeypot) as honeypot_flagged,
				false as excluded_as_honeypot,
				'[]'::json as sample_http_titles,
				'[]'::json as sample_products,
				MIN(ts) as first_seen,
				MAX(ts) as last_seen,
				'2026-09-10'::VARCHAR as snapshot_date
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
				excluded_as_honeypot = EXCLUDED.excluded_as_honeypot,
				sample_http_titles = EXCLUDED.sample_http_titles,
				sample_products = EXCLUDED.sample_products,
				first_seen = EXCLUDED.first_seen,
				last_seen = EXCLUDED.last_seen
		""")
		await connection.execute(sql)
		await connection.commit()
		self.logger.info("aggregation_service.accounts_aggregated")

	async def _build_account_top_records_index(self, connection: Any) -> None:
		TraceContext.new_span_id("build_top_records")
		sql = text("""
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
		""")
		await connection.execute(sql)
		await connection.commit()
		self.logger.info("aggregation_service.account_top_records_built")

	async def _mark_excluded_honeypots(self, connection: Any) -> None:
		TraceContext.new_span_id("mark_honeypots")
		sql = text("""
			UPDATE accounts
			SET excluded_as_honeypot = true
			WHERE asset_count = 0 AND honeypot_flagged = true
		""")
		await connection.execute(sql)
		await connection.commit()
		result = await connection.execute(
			text("SELECT COUNT(*) as cnt FROM accounts WHERE excluded_as_honeypot = true")
		)
		count = result.fetchall()[0][0]
		self.logger.info("aggregation_service.honeypots_marked", count=count)
