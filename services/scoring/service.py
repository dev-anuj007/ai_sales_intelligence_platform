from __future__ import annotations

import json
from typing import Any

import logfire

from services.storage import AccountStorageService


class ScoringService:
    def __init__(self, account_storage: AccountStorageService | None = None) -> None:
        self.account_storage = account_storage or AccountStorageService()

    async def score_accounts(self, score_version: str = "v1") -> dict[str, Any]:
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
        """Composite risk score (0–100): weighted sum of sub-scores."""
        vuln_score = self._vuln_score(account)
        exposure_score = self._exposure_score(account)
        tls_hygiene_score = self._tls_hygiene_score(account)
        eol_legacy_score = self._eol_legacy_score(account)
        attack_surface_score = self._attack_surface_score(account)

        composite = (
            0.35 * vuln_score
            + 0.25 * exposure_score
            + 0.15 * tls_hygiene_score
            + 0.15 * eol_legacy_score
            + 0.10 * attack_surface_score
        )
        return min(100.0, max(0.0, composite))

    def _vuln_score(self, account: Any) -> float:
        """Vulnerability severity: CVSS×EPSS + critical CVE count."""
        max_cvss = account.max_cvss or 0.0
        max_epss = account.max_epss or 0.0
        critical_count = account.vuln_count_critical or 0
        return min(100.0, 100 * (0.5 * max_cvss / 10 + 0.5 * max_epss) + min(20, 4 * critical_count))

    def _exposure_score(self, account: Any) -> float:
        """Exposable attack surface: DB + legacy + IoT/OT."""
        score = 0.0
        if account.exposed_database_count and account.exposed_database_count > 0:
            score += 35
        if account.legacy_protocol_count and account.legacy_protocol_count > 0:
            score += 30
        if account.iot_ot_device_count and account.iot_ot_device_count > 0:
            score += 25
        return min(100.0, score)

    def _tls_hygiene_score(self, account: Any) -> float:
        """TLS/SSL hygiene: ratio of weak/self-signed certs."""
        asset_count = account.asset_count or 0
        if asset_count == 0:
            return 0.0
        weak_or_self_signed = (account.self_signed_cert_count or 0) + (account.weak_tls_count or 0)
        ratio = weak_or_self_signed / asset_count
        return 100.0 * (1.0 - ratio)

    def _eol_legacy_score(self, account: Any) -> float:
        """EOL/legacy software prevalence."""
        asset_count = account.asset_count or 0
        if asset_count == 0:
            return 0.0
        eol_count = account.eol_product_count or 0
        ratio = eol_count / asset_count
        return min(100.0, 100.0 * ratio * 2)

    def _attack_surface_score(self, account: Any) -> float:
        """Raw attack surface: logarithmic scale by asset count."""
        asset_count = account.asset_count or 0
        if asset_count == 0:
            return 0.0
        import math
        return min(100.0, 15 * math.log2(asset_count + 1))

    def _extract_signals(self, account: Any) -> list[str]:
        """Extract human-readable risk signal tags."""
        signals = []

        if account.max_cvss and account.max_cvss >= 9.0:
            signals.append("CRITICAL_CVE")
        elif account.vuln_count_total and account.vuln_count_total > 0:
            signals.append("KNOWN_VULNERABILITIES")

        if account.exposed_database_count and account.exposed_database_count > 0:
            signals.append("EXPOSED_DATABASE")

        if account.legacy_protocol_count and account.legacy_protocol_count > 0:
            signals.append("LEGACY_PROTOCOL")

        if account.iot_ot_device_count and account.iot_ot_device_count > 0:
            signals.append("IOT_OT_EXPOSURE")

        if account.eol_product_count and account.eol_product_count > 0:
            signals.append("EOL_SOFTWARE")

        if account.self_signed_cert_count and account.self_signed_cert_count > 0:
            signals.append("WEAK_TLS")

        if account.cloud_or_cdn_fronted:
            signals.append("CDN_FRONTED")

        if account.asset_count and account.asset_count >= 20:
            signals.append("LARGE_ATTACK_SURFACE")

        return signals or ["UNKNOWN_RISK"]

    def _explain_score(self, account: Any, score: float) -> str:
        """Generate JSON explanation of score breakdown."""
        explanation = {
            "total_score": round(score, 2),
            "sub_scores": {
                "vulnerability": round(self._vuln_score(account), 2),
                "exposure": round(self._exposure_score(account), 2),
                "tls_hygiene": round(self._tls_hygiene_score(account), 2),
                "eol_legacy": round(self._eol_legacy_score(account), 2),
                "attack_surface": round(self._attack_surface_score(account), 2),
            },
            "weights": {
                "vulnerability": 0.35,
                "exposure": 0.25,
                "tls_hygiene": 0.15,
                "eol_legacy": 0.15,
                "attack_surface": 0.10,
            },
            "evidence": {
                "asset_count": account.asset_count,
                "vuln_count_total": account.vuln_count_total,
                "max_cvss": account.max_cvss,
                "exposed_database_count": account.exposed_database_count,
                "legacy_protocol_count": account.legacy_protocol_count,
                "iot_ot_device_count": account.iot_ot_device_count,
                "eol_product_count": account.eol_product_count,
            },
        }
        return json.dumps(explanation)
