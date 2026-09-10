from __future__ import annotations

from typing import Any

import logfire

from config import settings
from services.llm.anthropic_client import AnthropicLLMClient
from services.llm.client import LLMClient
from services.llm.cost_model import CostTracker
from services.llm.state import EnrichmentState
from services.llm.workflow import create_enrichment_graph
from services.storage.models import Account
from services.storage.postgres_async_account_storage import (
    PostgresAsyncAccountStorageService,
)


class EnrichmentService:
    """Orchestrate LLM-based enrichment for accounts using LangGraph workflow."""

    def __init__(
        self,
        account_storage: PostgresAsyncAccountStorageService | None = None,
        llm_client: LLMClient | None = None,
    ) -> None:
        self.account_storage = account_storage or PostgresAsyncAccountStorageService()
        self.llm_client = llm_client or AnthropicLLMClient(settings.anthropic_api_key)
        self.graph = create_enrichment_graph()
        self.total_cost_usd: float = 0.0

    async def enrich_account(self, account: Account) -> dict[str, Any]:
        """Enrich a single account with LLM analysis.

        Returns:
            Dict with enrichment results:
            - company_name: Inferred company name
            - risk_narrative: Business-oriented risk explanation
            - outreach_draft: Professional email draft
            - cost_usd: Cost of LLM calls for this account
            - errors: List of any errors that occurred
        """
        try:
            state = self._create_state_from_account(account)

            state_dict = state.to_dict()
            state_dict["llm_client"] = self.llm_client

            result_dict = self.graph.invoke(state_dict)

            cost_usd = self._calculate_cost(result_dict.get("cost_tracking", {}))
            self.total_cost_usd += cost_usd

            enrichment_data = {
                "company_name": result_dict.get("company_name", ""),
                "risk_narrative": result_dict.get("risk_narrative", ""),
                "outreach_draft": result_dict.get("outreach_draft", ""),
                "cost_usd": cost_usd,
                "errors": result_dict.get("errors", []),
            }

            if not result_dict.get("errors"):
                await self.account_storage.update_enrichment(
                    root_domain=account.root_domain,
                    inferred_company_name=enrichment_data["company_name"],
                    inferred_industry=None,
                    narrative=enrichment_data["risk_narrative"],
                    outreach_draft=enrichment_data["outreach_draft"],
                )

            logfire.info(
                "enrichment.account_complete",
                domain=account.root_domain,
                cost_usd=cost_usd,
                has_errors=bool(enrichment_data["errors"]),
            )

            return enrichment_data

        except Exception as e:
            logfire.error(
                "enrichment.account_failed",
                domain=account.root_domain,
                error=str(e),
            )
            return {
                "company_name": "",
                "risk_narrative": "",
                "outreach_draft": "",
                "cost_usd": 0.0,
                "errors": [f"enrichment_failed: {str(e)}"],
            }

    async def enrich_top_accounts(self, top_n: int = 50) -> dict[str, Any]:
        """Enrich top N accounts by risk score.

        Returns:
            Dict with batch results:
            - status: "success" or "failed"
            - enriched_count: Number of accounts successfully enriched
            - total_cost_usd: Total cost for all enrichments
            - failed_accounts: List of (root_domain, error) tuples
        """
        logfire.info("enrichment.batch_start", top_n=top_n)

        accounts = await self.account_storage.list_top_by_score(top_n=top_n)
        logfire.info("enrichment.batch_fetched", count=len(accounts))

        enriched_count = 0
        failed_accounts: list[tuple[str, str]] = []

        for account in accounts:
            result = await self.enrich_account(account)

            if not result["errors"]:
                enriched_count += 1
            else:
                failed_accounts.append((account.root_domain, result["errors"][0]))

        total_cost = round(self.total_cost_usd, 4)

        logfire.info(
            "enrichment.batch_complete",
            enriched_count=enriched_count,
            failed_count=len(failed_accounts),
            total_cost_usd=total_cost,
        )

        return {
            "status": "success" if enriched_count > 0 else "failed",
            "enriched_count": enriched_count,
            "failed_count": len(failed_accounts),
            "total_cost_usd": total_cost,
            "failed_accounts": failed_accounts,
        }

    def _create_state_from_account(self, account: Account) -> EnrichmentState:
        """Convert Account model to EnrichmentState for workflow."""
        exposures = {
            "database": account.exposed_database_count,
            "legacy_protocol": account.legacy_protocol_count,
            "iot_ot": account.iot_ot_device_count,
            "eol_software": account.eol_product_count,
            "weak_tls": account.weak_tls_count,
        }

        return EnrichmentState(
            root_domain=account.root_domain,
            risk_score=account.risk_score or 0.0,
            signal_tags=account.signal_tags or [],
            exposures={k: v for k, v in exposures.items() if v > 0},
            http_titles=getattr(account, "sample_http_titles", []),
            products=getattr(account, "sample_products", []),
            llm_client=self.llm_client,
        )

    @staticmethod
    def _calculate_cost(cost_tracking: dict[str, Any]) -> float:
        """Calculate total cost from cost_tracking dict."""
        total_cost = 0.0
        for node_cost in cost_tracking.values():
            if isinstance(node_cost, dict):
                model = node_cost.get("model", "")
                input_tokens = node_cost.get("input_tokens", 0)
                output_tokens = node_cost.get("output_tokens", 0)
                cost = CostTracker.calculate_cost(model, input_tokens, output_tokens)
                total_cost += cost

        return round(total_cost, 4)

    def get_total_cost(self) -> float:
        """Return cumulative cost in USD."""
        return round(self.total_cost_usd, 4)

    def reset_cost_tracking(self) -> None:
        """Clear cost tracking for next batch."""
        self.total_cost_usd = 0.0
