from __future__ import annotations

from typing import Any

import pytest

from services.storage.models import Account
from services.storage.postgres_async_account_storage import PostgresAsyncAccountStorageService


class MockAsyncAccountStorage(PostgresAsyncAccountStorageService):
    def __init__(self) -> None:
        self.unscored_accounts: list[Account] = []
        self.updated_scores: dict[str, Any] = {}

    async def list_unscored(self, limit: int = 100) -> list[Account]:
        return self.unscored_accounts[:limit]

    async def update_score(
        self,
        root_domain: str,
        risk_score: float,
        score_version: str,
        signal_tags: list[str],
        score_explanation: str,
    ) -> None:
        self.updated_scores[root_domain] = {
            "risk_score": risk_score,
            "score_version": score_version,
            "signal_tags": signal_tags,
            "score_explanation": score_explanation,
        }


@pytest.fixture
def mock_account_storage() -> MockAsyncAccountStorage:
    return MockAsyncAccountStorage()


@pytest.fixture
def account_no_risk() -> Account:
    return Account(
        root_domain="safe.example.com",
        record_count=1,
        asset_count=1,
        distinct_ips=1,
        distinct_ports=1,
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


@pytest.fixture
def account_critical_vuln() -> Account:
    return Account(
        root_domain="critical.example.com",
        record_count=5,
        asset_count=5,
        distinct_ips=3,
        distinct_ports=4,
        vuln_count_total=3,
        vuln_count_critical=1,
        max_cvss=9.8,
        max_epss=0.95,
        exposed_database_count=1,
        legacy_protocol_count=0,
        iot_ot_device_count=0,
        eol_product_count=0,
        self_signed_cert_count=0,
        weak_tls_count=0,
        cloud_or_cdn_fronted=False,
    )


@pytest.fixture
def account_exposure() -> Account:
    return Account(
        root_domain="exposed.example.com",
        record_count=25,
        asset_count=25,
        distinct_ips=20,
        distinct_ports=15,
        vuln_count_total=0,
        vuln_count_critical=0,
        max_cvss=None,
        max_epss=None,
        exposed_database_count=1,
        legacy_protocol_count=2,
        iot_ot_device_count=1,
        eol_product_count=5,
        self_signed_cert_count=3,
        weak_tls_count=2,
        cloud_or_cdn_fronted=False,
    )


@pytest.fixture
def account_complex() -> Account:
    return Account(
        root_domain="complex.example.com",
        record_count=100,
        asset_count=100,
        distinct_ips=80,
        distinct_ports=50,
        vuln_count_total=15,
        vuln_count_critical=3,
        max_cvss=8.5,
        max_epss=0.72,
        exposed_database_count=2,
        legacy_protocol_count=5,
        iot_ot_device_count=3,
        eol_product_count=20,
        self_signed_cert_count=10,
        weak_tls_count=8,
        cloud_or_cdn_fronted=True,
    )
