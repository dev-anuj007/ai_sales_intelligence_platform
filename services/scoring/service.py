from typing import Any

import duckdb
import logfire

from sales_intel.services.storage.account_storage import AccountStorageService


class ScoringService:
    def __init__(self, connection: duckdb.DuckDBPyConnection) -> None:
        self.connection = connection
        self.account_storage = AccountStorageService(connection)

    def score_accounts(self, score_version: str = "v1") -> dict[str, Any]:
        logfire.info("scoring_service.start", score_version=score_version)

        try:
            unscored = self.account_storage.list_unscored(limit=10000)
            logfire.info("scoring_service.fetched", count=len(unscored))

            scores_applied = 0
            for account in unscored:
                risk_score = self._compute_score(account)
                signal_tags = self._extract_signals(account)
                score_explanation = self._explain_score(account, risk_score)

                self.account_storage.update_score(
                    root_domain=account.root_domain,
                    risk_score=risk_score,
                    score_version=score_version,
                    signal_tags=signal_tags,
                    score_explanation=score_explanation,
                )
                scores_applied += 1

            logfire.info("scoring_service.complete", scores_applied=scores_applied)
            return {
                "status": "success",
                "scores_applied": scores_applied,
                "score_version": score_version,
            }

        except Exception as e:
            logfire.error("scoring_service.failed", error=str(e))
            raise

    def _compute_score(self, account: Any) -> float:
        return 0.0

    def _extract_signals(self, account: Any) -> list[str]:
        return []

    def _explain_score(self, account: Any, score: float) -> str:
        return "{}"
