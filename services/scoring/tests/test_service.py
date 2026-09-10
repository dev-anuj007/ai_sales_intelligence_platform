from __future__ import annotations

import json
from typing import Any

import pytest

from services.scoring.service import ScoringService
from services.storage.models import Account
from services.scoring.tests.conftest import MockAsyncAccountStorage


class TestComputeScore:
    def test_low_risk_account(self, account_no_risk: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_no_risk)
        assert 0 <= score < 30

    def test_critical_vuln_account(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_critical_vuln)
        assert 50 < score < 100

    def test_exposure_account(self, account_exposure: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_exposure)
        assert 30 < score < 80

    def test_complex_account(self, account_complex: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_complex)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_score_bounds(self, account_complex: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_complex)
        assert 0.0 <= score <= 100.0


class TestVulnScore:
    def test_no_vulns(self, account_no_risk: Account) -> None:
        service = ScoringService()
        score = service._vuln_score(account_no_risk)
        assert score == 0.0

    def test_high_cvss(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        score = service._vuln_score(account_critical_vuln)
        assert score > 50.0

    def test_with_critical_cves(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        score = service._vuln_score(account_critical_vuln)
        assert 50 < score <= 100

    def test_vuln_score_bounds(self, account_complex: Account) -> None:
        service = ScoringService()
        score = service._vuln_score(account_complex)
        assert 0.0 <= score <= 100.0


class TestExposureScore:
    def test_no_exposure(self, account_no_risk: Account) -> None:
        service = ScoringService()
        score = service._exposure_score(account_no_risk)
        assert score == 0.0

    def test_database_exposure(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        score = service._exposure_score(account_critical_vuln)
        assert score == 35.0

    def test_multiple_exposures(self, account_exposure: Account) -> None:
        service = ScoringService()
        score = service._exposure_score(account_exposure)
        assert score == 90.0

    def test_exposure_capped_at_100(self, account_complex: Account) -> None:
        service = ScoringService()
        score = service._exposure_score(account_complex)
        assert score == 90.0


class TestTLSScore:
    def test_no_asset_count(self) -> None:
        account = Account(
            root_domain="test.com",
            record_count=0,
            asset_count=0,
            distinct_ips=0,
            distinct_ports=0,
            vuln_count_total=0,
            vuln_count_critical=0,
            max_cvss=None,
            max_epss=None,
            exposed_database_count=0,
            legacy_protocol_count=0,
            iot_ot_device_count=0,
            eol_product_count=0,
            self_signed_cert_count=0,
            weak_tls_count=0,
            cloud_or_cdn_fronted=False,
        )
        service = ScoringService()
        score = service._tls_hygiene_score(account)
        assert score == 0.0

    def test_all_weak_tls(self) -> None:
        account = Account(
            root_domain="test.com",
            record_count=10,
            asset_count=10,
            distinct_ips=8,
            distinct_ports=5,
            vuln_count_total=0,
            vuln_count_critical=0,
            max_cvss=None,
            max_epss=None,
            exposed_database_count=0,
            legacy_protocol_count=0,
            iot_ot_device_count=0,
            eol_product_count=0,
            self_signed_cert_count=5,
            weak_tls_count=5,
            cloud_or_cdn_fronted=False,
        )
        service = ScoringService()
        score = service._tls_hygiene_score(account)
        assert score == 0.0

    def test_no_weak_tls(self, account_no_risk: Account) -> None:
        service = ScoringService()
        score = service._tls_hygiene_score(account_no_risk)
        assert score == 100.0

    def test_half_weak_tls(self, account_exposure: Account) -> None:
        service = ScoringService()
        score = service._tls_hygiene_score(account_exposure)
        assert score == pytest.approx(80.0, abs=1.0)


class TestEOLScore:
    def test_no_asset_count(self) -> None:
        account = Account(
            root_domain="test.com",
            record_count=0,
            asset_count=0,
            distinct_ips=0,
            distinct_ports=0,
            vuln_count_total=0,
            vuln_count_critical=0,
            max_cvss=None,
            max_epss=None,
            exposed_database_count=0,
            legacy_protocol_count=0,
            iot_ot_device_count=0,
            eol_product_count=5,
            self_signed_cert_count=0,
            weak_tls_count=0,
            cloud_or_cdn_fronted=False,
        )
        service = ScoringService()
        score = service._eol_legacy_score(account)
        assert score == 0.0

    def test_no_eol_products(self, account_no_risk: Account) -> None:
        service = ScoringService()
        score = service._eol_legacy_score(account_no_risk)
        assert score == 0.0

    def test_half_eol_products(self) -> None:
        account = Account(
            root_domain="test.com",
            record_count=10,
            asset_count=10,
            distinct_ips=8,
            distinct_ports=5,
            vuln_count_total=0,
            vuln_count_critical=0,
            max_cvss=None,
            max_epss=None,
            exposed_database_count=0,
            legacy_protocol_count=0,
            iot_ot_device_count=0,
            eol_product_count=5,
            self_signed_cert_count=0,
            weak_tls_count=0,
            cloud_or_cdn_fronted=False,
        )
        service = ScoringService()
        score = service._eol_legacy_score(account)
        assert score == 100.0

    def test_eol_score_capped(self, account_complex: Account) -> None:
        service = ScoringService()
        score = service._eol_legacy_score(account_complex)
        assert 0 <= score <= 100.0


class TestAttackSurfaceScore:
    def test_no_assets(self) -> None:
        account = Account(
            root_domain="test.com",
            record_count=0,
            asset_count=0,
            distinct_ips=0,
            distinct_ports=0,
            vuln_count_total=0,
            vuln_count_critical=0,
            max_cvss=None,
            max_epss=None,
            exposed_database_count=0,
            legacy_protocol_count=0,
            iot_ot_device_count=0,
            eol_product_count=0,
            self_signed_cert_count=0,
            weak_tls_count=0,
            cloud_or_cdn_fronted=False,
        )
        service = ScoringService()
        score = service._attack_surface_score(account)
        assert score == 0.0

    def test_single_asset(self, account_no_risk: Account) -> None:
        service = ScoringService()
        score = service._attack_surface_score(account_no_risk)
        assert 0 < score < 20

    def test_large_asset_count(self, account_complex: Account) -> None:
        service = ScoringService()
        score = service._attack_surface_score(account_complex)
        assert 50 < score <= 100.0

    def test_logarithmic_scaling(self) -> None:
        service = ScoringService()

        account_10 = Account(
            root_domain="test.com",
            record_count=10,
            asset_count=10,
            distinct_ips=8,
            distinct_ports=5,
            vuln_count_total=0, vuln_count_critical=0, max_cvss=None, max_epss=None,
            exposed_database_count=0, legacy_protocol_count=0, iot_ot_device_count=0,
            eol_product_count=0, self_signed_cert_count=0, weak_tls_count=0,
            cloud_or_cdn_fronted=False,
        )
        account_100 = Account(
            root_domain="test.com",
            record_count=100,
            asset_count=100,
            distinct_ips=80,
            distinct_ports=50,
            vuln_count_total=0, vuln_count_critical=0, max_cvss=None, max_epss=None,
            exposed_database_count=0, legacy_protocol_count=0, iot_ot_device_count=0,
            eol_product_count=0, self_signed_cert_count=0, weak_tls_count=0,
            cloud_or_cdn_fronted=False,
        )

        score_10 = service._attack_surface_score(account_10)
        score_100 = service._attack_surface_score(account_100)
        assert score_100 > score_10


class TestExtractSignals:
    def test_no_signals(self, account_no_risk: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_no_risk)
        assert signals == ["UNKNOWN_RISK"]

    def test_critical_cve_signal(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_critical_vuln)
        assert "CRITICAL_CVE" in signals

    def test_known_vulnerabilities_signal(self) -> None:
        account = Account(
            root_domain="test.com",
            record_count=1,
            asset_count=1,
            distinct_ips=1,
            distinct_ports=1,
            vuln_count_total=5, vuln_count_critical=0,
            max_cvss=7.5, max_epss=0.5,
            exposed_database_count=0, legacy_protocol_count=0, iot_ot_device_count=0,
            eol_product_count=0, self_signed_cert_count=0, weak_tls_count=0,
            cloud_or_cdn_fronted=False,
        )
        service = ScoringService()
        signals = service._extract_signals(account)
        assert "KNOWN_VULNERABILITIES" in signals

    def test_exposed_database_signal(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_critical_vuln)
        assert "EXPOSED_DATABASE" in signals

    def test_legacy_protocol_signal(self, account_exposure: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_exposure)
        assert "LEGACY_PROTOCOL" in signals

    def test_iot_ot_signal(self, account_exposure: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_exposure)
        assert "IOT_OT_EXPOSURE" in signals

    def test_eol_software_signal(self, account_exposure: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_exposure)
        assert "EOL_SOFTWARE" in signals

    def test_weak_tls_signal(self, account_exposure: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_exposure)
        assert "WEAK_TLS" in signals

    def test_cdn_signal(self, account_complex: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_complex)
        assert "CDN_FRONTED" in signals

    def test_large_attack_surface_signal(self, account_complex: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_complex)
        assert "LARGE_ATTACK_SURFACE" in signals

    def test_multiple_signals(self, account_complex: Account) -> None:
        service = ScoringService()
        signals = service._extract_signals(account_complex)
        assert len(signals) >= 5


class TestExplainScore:
    def test_explanation_structure(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_critical_vuln)
        explanation_json = service._explain_score(account_critical_vuln, score)
        explanation = json.loads(explanation_json)

        assert "total_score" in explanation
        assert "sub_scores" in explanation
        assert "weights" in explanation
        assert "evidence" in explanation

    def test_explanation_sub_scores(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_critical_vuln)
        explanation_json = service._explain_score(account_critical_vuln, score)
        explanation = json.loads(explanation_json)

        sub_scores = explanation["sub_scores"]
        assert "vulnerability" in sub_scores
        assert "exposure" in sub_scores
        assert "tls_hygiene" in sub_scores
        assert "eol_legacy" in sub_scores
        assert "attack_surface" in sub_scores

    def test_explanation_weights(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_critical_vuln)
        explanation_json = service._explain_score(account_critical_vuln, score)
        explanation = json.loads(explanation_json)

        weights = explanation["weights"]
        assert weights["vulnerability"] == 0.35
        assert weights["exposure"] == 0.25
        assert weights["tls_hygiene"] == 0.15
        assert weights["eol_legacy"] == 0.15
        assert weights["attack_surface"] == 0.10

    def test_explanation_evidence(self, account_critical_vuln: Account) -> None:
        service = ScoringService()
        score = service._compute_score(account_critical_vuln)
        explanation_json = service._explain_score(account_critical_vuln, score)
        explanation = json.loads(explanation_json)

        evidence = explanation["evidence"]
        assert evidence["asset_count"] == account_critical_vuln.asset_count
        assert evidence["max_cvss"] == account_critical_vuln.max_cvss


class TestScoreAccountsAsync:
    def test_empty_unscored_accounts(self, mock_account_storage: MockAsyncAccountStorage) -> None:
        async def run_test() -> None:
            service = ScoringService(mock_account_storage)
            result = await service.score_accounts(score_version="v1")

            assert result["status"] == "success"
            assert result["scores_applied"] == 0
            assert result["score_version"] == "v1"

        import asyncio
        asyncio.run(run_test())

    def test_score_single_account(
        self,
        mock_account_storage: MockAsyncAccountStorage,
        account_critical_vuln: Account,
    ) -> None:
        async def run_test() -> None:
            mock_account_storage.unscored_accounts = [account_critical_vuln]

            service = ScoringService(mock_account_storage)
            result = await service.score_accounts(score_version="v1")

            assert result["status"] == "success"
            assert result["scores_applied"] == 1
            assert account_critical_vuln.root_domain in mock_account_storage.updated_scores

        import asyncio
        asyncio.run(run_test())

    def test_score_multiple_accounts(
        self,
        mock_account_storage: MockAsyncAccountStorage,
        account_no_risk: Account,
        account_critical_vuln: Account,
        account_exposure: Account,
    ) -> None:
        async def run_test() -> None:
            mock_account_storage.unscored_accounts = [
                account_no_risk,
                account_critical_vuln,
                account_exposure,
            ]

            service = ScoringService(mock_account_storage)
            result = await service.score_accounts(score_version="v1")

            assert result["scores_applied"] == 3
            assert len(mock_account_storage.updated_scores) == 3

        import asyncio
        asyncio.run(run_test())

    def test_score_version_stored(
        self,
        mock_account_storage: MockAsyncAccountStorage,
        account_critical_vuln: Account,
    ) -> None:
        async def run_test() -> None:
            mock_account_storage.unscored_accounts = [account_critical_vuln]

            service = ScoringService(mock_account_storage)
            await service.score_accounts(score_version="v2")

            updated = mock_account_storage.updated_scores[account_critical_vuln.root_domain]
            assert updated["score_version"] == "v2"

        import asyncio
        asyncio.run(run_test())

    def test_signal_tags_stored(
        self,
        mock_account_storage: MockAsyncAccountStorage,
        account_critical_vuln: Account,
    ) -> None:
        async def run_test() -> None:
            mock_account_storage.unscored_accounts = [account_critical_vuln]

            service = ScoringService(mock_account_storage)
            await service.score_accounts()

            updated = mock_account_storage.updated_scores[account_critical_vuln.root_domain]
            assert len(updated["signal_tags"]) > 0
            assert "CRITICAL_CVE" in updated["signal_tags"]

        import asyncio
        asyncio.run(run_test())

    def test_score_explanation_stored(
        self,
        mock_account_storage: MockAsyncAccountStorage,
        account_critical_vuln: Account,
    ) -> None:
        async def run_test() -> None:
            mock_account_storage.unscored_accounts = [account_critical_vuln]

            service = ScoringService(mock_account_storage)
            await service.score_accounts()

            updated = mock_account_storage.updated_scores[account_critical_vuln.root_domain]
            explanation = json.loads(updated["score_explanation"])

            assert "total_score" in explanation
            assert "sub_scores" in explanation
            assert "weights" in explanation

        import asyncio
        asyncio.run(run_test())

    def test_risk_scores_are_deterministic(
        self,
        mock_account_storage: MockAsyncAccountStorage,
        account_critical_vuln: Account,
    ) -> None:
        async def run_test() -> None:
            mock_account_storage.unscored_accounts = [account_critical_vuln]

            service1 = ScoringService(mock_account_storage)
            await service1.score_accounts()
            score1 = mock_account_storage.updated_scores[account_critical_vuln.root_domain]["risk_score"]

            mock_account_storage.updated_scores.clear()

            service2 = ScoringService(mock_account_storage)
            await service2.score_accounts()
            score2 = mock_account_storage.updated_scores[account_critical_vuln.root_domain]["risk_score"]

            assert score1 == score2

        import asyncio
        asyncio.run(run_test())
