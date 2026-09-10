from __future__ import annotations

from typing import Any

import logfire

from services.storage.postgres_async_account_storage import PostgresAsyncAccountStorageService
from services.storage.postgres_names_storage import PostgresNamesStorageServiceImpl


class EnrichmentService:
	def __init__(self, account_storage: PostgresAsyncAccountStorageService | None = None, names_storage: PostgresNamesStorageServiceImpl | None = None) -> None:
		self.account_storage = account_storage or PostgresAsyncAccountStorageService()
		self.names_storage = names_storage or PostgresNamesStorageServiceImpl()

	async def enrich_top_accounts(self, top_n: int = 50, score_version: str = "v1") -> dict[str, Any]:
		logfire.info("enrichment_service.start", top_n=top_n, score_version=score_version)

		try:
			accounts = await self.account_storage.list_top_by_score(top_n=top_n)
			logfire.info("enrichment_service.fetched", count=len(accounts))

			enriched_count = 0
			for account in accounts:
				inferred_name = self._infer_company_name(account)
				inferred_industry = self._infer_industry(account)
				narrative = self._generate_narrative(account)
				outreach_draft = self._generate_outreach(account)

				await self.account_storage.update_enrichment(
					root_domain=account.root_domain,
					inferred_company_name=inferred_name,
					inferred_industry=inferred_industry,
					narrative=narrative,
					outreach_draft=outreach_draft,
				)

				if inferred_name:
					self.names_storage.store_name(
						account.root_domain, inferred_name, "enrichment"
					)

				enriched_count += 1

			logfire.info("enrichment_service.complete", enriched_count=enriched_count)
			return {
				"status": "success",
				"enriched_count": enriched_count,
				"score_version": score_version,
			}

		except Exception as e:
			logfire.error("enrichment_service.failed", error=str(e))
			raise

	def _infer_company_name(self, account: Any) -> str | None:
		return None

	def _infer_industry(self, account: Any) -> str | None:
		return None

	def _generate_narrative(self, account: Any) -> str:
		return ""

	def _generate_outreach(self, account: Any) -> str:
		return ""
