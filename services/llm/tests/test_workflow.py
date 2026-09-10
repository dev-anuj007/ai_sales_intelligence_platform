from __future__ import annotations

import pytest

from services.llm.mock_client import MockLLMClient
from services.llm.state import EnrichmentState
from services.llm.workflow import create_enrichment_graph


class TestEnrichmentStateCreation:
    """Test EnrichmentState creation and serialization."""

    def test_create_state_minimal(self, mock_llm_client: MockLLMClient) -> None:
        """Test creating state with minimal data."""
        state = EnrichmentState(
            root_domain="example.com",
            risk_score=75.0,
            signal_tags=["CRITICAL_CVE"],
            exposures={"database": 1},
            http_titles=["Apache"],
            products=["nginx"],
            llm_client=mock_llm_client,
        )

        assert state.root_domain == "example.com"
        assert state.risk_score == 75.0
        assert state.signal_noise_result == ""
        assert state.company_name == ""

    def test_state_to_dict(self, mock_llm_client: MockLLMClient) -> None:
        """Test state serialization to dict."""
        state = EnrichmentState(
            root_domain="example.com",
            risk_score=85.0,
            signal_tags=["EXPOSED_DATABASE"],
            exposures={"database": 2},
            http_titles=["Nginx"],
            products=["MySQL"],
            signal_noise_result="signal",
            company_name="Example Corp",
            llm_client=mock_llm_client,
        )

        state_dict = state.to_dict()

        assert state_dict["root_domain"] == "example.com"
        assert state_dict["risk_score"] == 85.0
        assert state_dict["signal_noise_result"] == "signal"
        assert state_dict["company_name"] == "Example Corp"
        assert "llm_client" not in state_dict

    def test_state_from_dict(self, mock_llm_client: MockLLMClient) -> None:
        """Test state creation from dict."""
        data = {
            "root_domain": "test.com",
            "risk_score": 50.0,
            "signal_tags": ["WEAK_TLS"],
            "exposures": {},
            "http_titles": [],
            "products": [],
            "signal_noise_result": "noise",
            "company_name": "Test Inc",
            "risk_narrative": "Test narrative",
            "outreach_draft": "Test draft",
            "cost_tracking": {},
            "errors": [],
        }

        state = EnrichmentState.from_dict(data, mock_llm_client)

        assert state.root_domain == "test.com"
        assert state.risk_score == 50.0
        assert state.signal_noise_result == "noise"
        assert state.company_name == "Test Inc"
        assert state.llm_client == mock_llm_client

    def test_state_accumulates_errors(self, mock_llm_client: MockLLMClient) -> None:
        """Test state error tracking."""
        state = EnrichmentState(
            root_domain="example.com",
            risk_score=75.0,
            signal_tags=[],
            exposures={},
            http_titles=[],
            products=[],
            llm_client=mock_llm_client,
        )

        state.errors.append("Error 1")
        state.errors.append("Error 2")

        assert len(state.errors) == 2
        assert "Error 1" in state.errors


class TestEnrichmentWorkflowCreation:
    """Test enrichment workflow graph creation."""

    def test_workflow_compiles(self) -> None:
        """Test workflow graph compiles without errors."""
        graph = create_enrichment_graph()
        assert graph is not None

    def test_workflow_has_entry_point(self) -> None:
        """Test workflow has entry point defined."""
        graph = create_enrichment_graph()
        assert hasattr(graph, "invoke")

    def test_workflow_structure(self) -> None:
        """Test workflow has expected nodes."""
        graph = create_enrichment_graph()

        assert graph.nodes is not None
        node_names = list(graph.nodes.keys())

        assert "signal_noise" in node_names
        assert "company_name" in node_names
        assert "narrative" in node_names
        assert "outreach" in node_names


class TestEnrichmentWorkflowExecution:
    """Test enrichment workflow execution (mocked)."""

    def test_workflow_accepts_state(self, mock_llm_client: MockLLMClient) -> None:
        """Test workflow can be invoked with state."""
        graph = create_enrichment_graph()

        state = EnrichmentState(
            root_domain="test.example.com",
            risk_score=80.0,
            signal_tags=["CRITICAL_CVE", "EXPOSED_DATABASE"],
            exposures={"database": 1, "legacy_protocol": 2},
            http_titles=["Apache/2.4"],
            products=["OpenSSL", "MySQL"],
            llm_client=mock_llm_client,
        )

        initial_state = state.to_dict()
        assert initial_state["root_domain"] == "test.example.com"
        assert initial_state["company_name"] == ""

    def test_state_tracks_costs(self, mock_llm_client: MockLLMClient) -> None:
        """Test state can track costs per node."""
        state = EnrichmentState(
            root_domain="example.com",
            risk_score=75.0,
            signal_tags=[],
            exposures={},
            http_titles=[],
            products=[],
            llm_client=mock_llm_client,
        )

        state.cost_tracking["signal_noise"] = {
            "model": "claude-haiku-4-5-20251001",
            "input_tokens": 150,
            "output_tokens": 50,
        }

        assert state.cost_tracking["signal_noise"]["input_tokens"] == 150

    def test_state_accumulates_all_costs(self, mock_llm_client: MockLLMClient) -> None:
        """Test state accumulates costs from all nodes."""
        state = EnrichmentState(
            root_domain="example.com",
            risk_score=75.0,
            signal_tags=[],
            exposures={},
            http_titles=[],
            products=[],
            llm_client=mock_llm_client,
        )

        state.cost_tracking["signal_noise"] = {
            "model": "haiku",
            "input_tokens": 150,
            "output_tokens": 50,
        }
        state.cost_tracking["company_name"] = {
            "model": "haiku",
            "input_tokens": 120,
            "output_tokens": 30,
        }
        state.cost_tracking["narrative"] = {
            "model": "sonnet",
            "input_tokens": 300,
            "output_tokens": 150,
        }
        state.cost_tracking["outreach"] = {
            "model": "sonnet",
            "input_tokens": 250,
            "output_tokens": 200,
        }

        assert len(state.cost_tracking) == 4
        total_input = sum(
            v["input_tokens"] for v in state.cost_tracking.values()
        )
        assert total_input == 820


class TestEnrichmentWorkflowIntegration:
    """Integration tests for enrichment workflow."""

    def test_workflow_state_flow(self, mock_llm_client: MockLLMClient) -> None:
        """Test state flows through workflow correctly."""
        initial_state = EnrichmentState(
            root_domain="acme.example.com",
            risk_score=85.0,
            signal_tags=["CRITICAL_CVE"],
            exposures={"database": 1},
            http_titles=["Nginx/1.20"],
            products=["PostgreSQL"],
            llm_client=mock_llm_client,
        )

        assert initial_state.signal_noise_result == ""
        assert initial_state.company_name == ""
        assert initial_state.risk_narrative == ""
        assert initial_state.outreach_draft == ""

    def test_workflow_handles_empty_inputs(self, mock_llm_client: MockLLMClient) -> None:
        """Test workflow handles empty/minimal inputs."""
        state = EnrichmentState(
            root_domain="minimal.com",
            risk_score=0.0,
            signal_tags=[],
            exposures={},
            http_titles=[],
            products=[],
            llm_client=mock_llm_client,
        )

        assert state.root_domain == "minimal.com"
        assert len(state.signal_tags) == 0
        assert len(state.exposures) == 0
