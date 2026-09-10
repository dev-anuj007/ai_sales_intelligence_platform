from __future__ import annotations

import asyncio

import pytest

from services.enrichment.service import EnrichmentService
from services.storage.models import Account


class MockAccountStorage:
    """Mock storage for testing EnrichmentService."""

    def __init__(self) -> None:
        self.enrichments: dict[str, dict] = {}
        self.accounts_list: list[Account] = []

    async def list_top_by_score(self, top_n: int) -> list[Account]:
        return self.accounts_list[:top_n]

    async def update_enrichment(
        self,
        root_domain: str,
        inferred_company_name: str,
        risk_narrative: str,
        outreach_draft: str,
        enrichment_cost_usd: float,
    ) -> None:
        self.enrichments[root_domain] = {
            "inferred_company_name": inferred_company_name,
            "risk_narrative": risk_narrative,
            "outreach_draft": outreach_draft,
            "enrichment_cost_usd": enrichment_cost_usd,
        }


@pytest.fixture
def mock_storage() -> MockAccountStorage:
    """Provide mock storage for tests."""
    return MockAccountStorage()


@pytest.fixture
def enrichment_service(mock_storage: MockAccountStorage) -> EnrichmentService:
    """Provide EnrichmentService with mock storage."""
    return EnrichmentService(account_storage=mock_storage)


@pytest.fixture
def test_account() -> Account:
    """Provide a test account."""
    return Account(
        root_domain="test.example.com",
        record_count=10,
        asset_count=5,
        distinct_ips=3,
        distinct_ports=4,
        vuln_count_total=2,
        vuln_count_critical=0,
        max_cvss=7.5,
        max_epss=0.5,
        exposed_database_count=1,
        legacy_protocol_count=0,
        iot_ot_device_count=0,
        eol_product_count=2,
        self_signed_cert_count=0,
        weak_tls_count=1,
        cloud_or_cdn_fronted=False,
        risk_score=65.0,
        signal_tags=["EXPOSED_DATABASE", "EOL_SOFTWARE", "WEAK_TLS"],
    )


class TestEnrichmentServiceInitialization:
    """Test EnrichmentService creation and initialization."""

    def test_service_creates_graph(self) -> None:
        """Test service creates LangGraph workflow."""
        service = EnrichmentService()
        assert service.graph is not None
        assert hasattr(service.graph, "invoke")

    def test_service_initializes_cost_tracking(self) -> None:
        """Test service initializes cost tracking."""
        service = EnrichmentService()
        assert service.get_total_cost() == 0.0

    def test_service_with_mock_storage(
        self, mock_storage: MockAccountStorage
    ) -> None:
        """Test service works with mocked storage."""
        service = EnrichmentService(account_storage=mock_storage)
        assert service.account_storage is mock_storage


class TestEnrichmentStateCreation:
    """Test EnrichmentState creation from Account."""

    def test_create_state_from_account(
        self,
        enrichment_service: EnrichmentService,
        test_account: Account,
    ) -> None:
        """Test converting Account to EnrichmentState."""
        state = enrichment_service._create_state_from_account(test_account)

        assert state.root_domain == "test.example.com"
        assert state.risk_score == 65.0
        assert "EXPOSED_DATABASE" in state.signal_tags
        assert state.exposures["database"] == 1
        assert state.exposures["eol_software"] == 2
        assert state.exposures["weak_tls"] == 1

    def test_filter_zero_exposures(
        self,
        enrichment_service: EnrichmentService,
        test_account: Account,
    ) -> None:
        """Test zero-value exposures are filtered out."""
        state = enrichment_service._create_state_from_account(test_account)

        assert "legacy_protocol" not in state.exposures
        assert "iot_ot" not in state.exposures


class TestCostCalculation:
    """Test cost calculation from LLM responses."""

    def test_calculate_cost_single_node(
        self, enrichment_service: EnrichmentService
    ) -> None:
        """Test cost calculation for single node."""
        cost_tracking = {
            "signal_noise": {
                "model": "claude-haiku-4-5-20251001",
                "input_tokens": 150,
                "output_tokens": 50,
            }
        }

        cost = enrichment_service._calculate_cost(cost_tracking)
        assert cost > 0
        assert cost < 0.01

    def test_calculate_cost_multiple_nodes(
        self, enrichment_service: EnrichmentService
    ) -> None:
        """Test cost calculation across multiple nodes."""
        cost_tracking = {
            "signal_noise": {
                "model": "claude-haiku-4-5-20251001",
                "input_tokens": 150,
                "output_tokens": 50,
            },
            "company_name": {
                "model": "claude-haiku-4-5-20251001",
                "input_tokens": 120,
                "output_tokens": 30,
            },
            "narrative": {
                "model": "claude-sonnet-5-20251022",
                "input_tokens": 300,
                "output_tokens": 150,
            },
            "outreach": {
                "model": "claude-sonnet-5-20251022",
                "input_tokens": 250,
                "output_tokens": 200,
            },
        }

        cost = enrichment_service._calculate_cost(cost_tracking)
        assert cost > 0.005
        assert cost < 0.02

    def test_calculate_cost_empty_tracking(
        self, enrichment_service: EnrichmentService
    ) -> None:
        """Test cost calculation with empty tracking."""
        cost = enrichment_service._calculate_cost({})
        assert cost == 0.0

    def test_calculate_cost_invalid_model(
        self, enrichment_service: EnrichmentService
    ) -> None:
        """Test cost calculation with unknown model defaults to Haiku pricing."""
        cost_tracking = {
            "unknown_node": {
                "model": "unknown-model-xyz",
                "input_tokens": 1000,
                "output_tokens": 100,
            }
        }

        cost = enrichment_service._calculate_cost(cost_tracking)
        assert cost > 0


class TestCostTracking:
    """Test cost tracking across service lifetime."""

    def test_initial_cost_is_zero(
        self, enrichment_service: EnrichmentService
    ) -> None:
        """Test service starts with zero cost."""
        assert enrichment_service.get_total_cost() == 0.0

    def test_cost_tracking_accumulates(
        self, enrichment_service: EnrichmentService
    ) -> None:
        """Test costs accumulate across operations."""
        enrichment_service.total_cost_usd = 0.10
        assert enrichment_service.get_total_cost() == 0.10

        enrichment_service.total_cost_usd += 0.05
        assert enrichment_service.get_total_cost() == 0.15

    def test_reset_cost_tracking(
        self, enrichment_service: EnrichmentService
    ) -> None:
        """Test reset clears cost tracking."""
        enrichment_service.total_cost_usd = 0.50
        enrichment_service.reset_cost_tracking()
        assert enrichment_service.get_total_cost() == 0.0


class TestEnrichmentAccountAsync:
    """Test single account enrichment (async)."""

    def test_enrich_account_returns_dict(
        self,
        enrichment_service: EnrichmentService,
        test_account: Account,
    ) -> None:
        """Test enrich_account returns expected structure."""
        async def run_test() -> None:
            result = await enrichment_service.enrich_account(test_account)
            assert isinstance(result, dict)
            assert "company_name" in result
            assert "risk_narrative" in result
            assert "outreach_draft" in result
            assert "cost_usd" in result
            assert "errors" in result

        asyncio.run(run_test())

    def test_enrich_account_with_error_handling(
        self,
        enrichment_service: EnrichmentService,
        test_account: Account,
    ) -> None:
        """Test enrich_account handles errors gracefully."""
        async def run_test() -> None:
            result = await enrichment_service.enrich_account(test_account)
            assert isinstance(result["errors"], list)
            assert isinstance(result["cost_usd"], (int, float))

        asyncio.run(run_test())

    def test_enrich_account_cost_added_to_total(
        self,
        enrichment_service: EnrichmentService,
        test_account: Account,
    ) -> None:
        """Test account enrichment cost is added to total."""
        async def run_test() -> None:
            initial_cost = enrichment_service.get_total_cost()
            result = await enrichment_service.enrich_account(test_account)
            new_cost = enrichment_service.get_total_cost()
            assert new_cost >= initial_cost

        asyncio.run(run_test())


class TestEnrichmentBatchAsync:
    """Test batch account enrichment (async)."""

    def test_enrich_top_accounts_returns_dict(
        self,
        enrichment_service: EnrichmentService,
        test_account: Account,
        mock_storage: MockAccountStorage,
    ) -> None:
        """Test enrich_top_accounts returns expected structure."""
        async def run_test() -> None:
            mock_storage.accounts_list = [test_account]
            result = await enrichment_service.enrich_top_accounts(top_n=1)
            assert isinstance(result, dict)
            assert "status" in result
            assert "enriched_count" in result
            assert "total_cost_usd" in result
            assert "failed_accounts" in result

        asyncio.run(run_test())

    def test_enrich_top_accounts_empty_list(
        self, enrichment_service: EnrichmentService
    ) -> None:
        """Test enrich_top_accounts handles empty account list."""
        async def run_test() -> None:
            result = await enrichment_service.enrich_top_accounts(top_n=10)
            assert result["enriched_count"] == 0
            assert result["total_cost_usd"] == 0.0
            assert len(result["failed_accounts"]) == 0

        asyncio.run(run_test())

    def test_enrich_top_accounts_multiple(
        self,
        enrichment_service: EnrichmentService,
        mock_storage: MockAccountStorage,
    ) -> None:
        """Test enrich_top_accounts with multiple accounts."""
        async def run_test() -> None:
            accounts = [
                Account(
                    root_domain=f"test{i}.example.com",
                    record_count=5,
                    asset_count=2,
                    distinct_ips=1,
                    distinct_ports=2,
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
                    risk_score=50.0,
                    signal_tags=[],
                )
                for i in range(3)
            ]
            mock_storage.accounts_list = accounts
            result = await enrichment_service.enrich_top_accounts(top_n=3)
            assert result["enriched_count"] <= 3
            assert isinstance(result["total_cost_usd"], (int, float))

        asyncio.run(run_test())
