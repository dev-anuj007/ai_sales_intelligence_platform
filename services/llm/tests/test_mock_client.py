from __future__ import annotations

import pytest

from services.llm.mock_client import MockLLMClient


class TestMockLLMClientDeterminism:
    """Test MockLLMClient produces deterministic outputs."""

    def test_signal_noise_deterministic(self) -> None:
        """Test signal/noise classification is deterministic."""
        client1 = MockLLMClient()
        client2 = MockLLMClient()

        resp1 = client1.classify_signal_noise(
            "example.com", ["exposed_database"], ["Apache"]
        )
        resp2 = client2.classify_signal_noise(
            "example.com", ["exposed_database"], ["Apache"]
        )

        assert resp1.content == resp2.content
        assert resp1.cost_usd == resp2.cost_usd
        assert resp1.input_tokens == resp2.input_tokens

    def test_company_inference_deterministic(self) -> None:
        """Test company name inference is deterministic."""
        client1 = MockLLMClient()
        client2 = MockLLMClient()

        resp1 = client1.infer_company_name(
            "acme.com", ["ACME Corp"], ["nginx"]
        )
        resp2 = client2.infer_company_name(
            "acme.com", ["ACME Corp"], ["nginx"]
        )

        assert resp1.content == resp2.content
        assert resp1.cost_usd == resp2.cost_usd

    def test_risk_narrative_deterministic(self) -> None:
        """Test risk narrative generation is deterministic."""
        client1 = MockLLMClient()
        client2 = MockLLMClient()

        resp1 = client1.generate_risk_narrative(
            "example.com",
            85.0,
            ["CRITICAL_CVE", "EXPOSED_DATABASE"],
            {"database": 2, "legacy_protocol": 1},
        )
        resp2 = client2.generate_risk_narrative(
            "example.com",
            85.0,
            ["CRITICAL_CVE", "EXPOSED_DATABASE"],
            {"database": 2, "legacy_protocol": 1},
        )

        assert resp1.content == resp2.content
        assert resp1.cost_usd == resp2.cost_usd

    def test_outreach_draft_deterministic(self) -> None:
        """Test outreach draft generation is deterministic."""
        client1 = MockLLMClient()
        client2 = MockLLMClient()

        narrative = "Your infrastructure has critical vulnerabilities."

        resp1 = client1.generate_outreach_draft(
            "Acme Corp", 85.0, narrative
        )
        resp2 = client2.generate_outreach_draft(
            "Acme Corp", 85.0, narrative
        )

        assert resp1.content == resp2.content
        assert resp1.cost_usd == resp2.cost_usd


class TestMockLLMClientSignalNoise:
    """Test signal/noise classification logic."""

    def test_empty_exposures_returns_noise(self) -> None:
        """Test no exposures classified as noise."""
        client = MockLLMClient()
        resp = client.classify_signal_noise("example.com", [], ["Apache"])
        assert resp.content == "noise"

    def test_any_exposure_returns_signal(self) -> None:
        """Test any exposure classified as signal."""
        client = MockLLMClient()
        resp = client.classify_signal_noise(
            "example.com", ["exposed_database"], ["Apache"]
        )
        assert resp.content == "signal"

    def test_multiple_exposures_returns_signal(self) -> None:
        """Test multiple exposures classified as signal."""
        client = MockLLMClient()
        resp = client.classify_signal_noise(
            "example.com",
            ["exposed_database", "legacy_protocol", "weak_tls"],
            ["Apache"],
        )
        assert resp.content == "signal"

    def test_signal_noise_token_counts_vary_by_input(self) -> None:
        """Test token counts scale with input size."""
        client = MockLLMClient()

        resp_small = client.classify_signal_noise(
            "a.co", ["db"], []
        )
        resp_large = client.classify_signal_noise(
            "verylongdomainname.example.com",
            ["exposed_database", "legacy_protocol"],
            ["Apache", "Nginx"],
        )

        assert resp_large.input_tokens > resp_small.input_tokens


class TestMockLLMClientCompanyInference:
    """Test company name inference logic."""

    def test_infers_company_name_from_domain(self) -> None:
        """Test company name extracted from domain."""
        client = MockLLMClient()
        resp = client.infer_company_name("acme.com", [], [])
        assert resp.content == "Acme"

    def test_company_name_title_cased(self) -> None:
        """Test company name is title cased."""
        client = MockLLMClient()
        resp = client.infer_company_name("amazon.com", [], [])
        assert resp.content == "Amazon"

    def test_multi_word_domain_takes_first_part(self) -> None:
        """Test multi-word domain takes first part."""
        client = MockLLMClient()
        resp = client.infer_company_name("mycompany.example.com", [], [])
        assert resp.content == "Mycompany"

    def test_company_inference_uses_haiku(self) -> None:
        """Test company inference uses Haiku model."""
        client = MockLLMClient()
        resp = client.infer_company_name("example.com", [], [])
        assert "haiku" in resp.model.lower()


class TestMockLLMClientRiskNarrative:
    """Test risk narrative generation logic."""

    def test_narrative_includes_domain(self) -> None:
        """Test narrative includes domain name."""
        client = MockLLMClient()
        resp = client.generate_risk_narrative(
            "example.com", 75.0, [], {}
        )
        assert "example.com" in resp.content

    def test_narrative_includes_risk_score(self) -> None:
        """Test narrative includes risk score."""
        client = MockLLMClient()
        resp = client.generate_risk_narrative(
            "example.com", 75.0, [], {}
        )
        assert "75.0" in resp.content

    def test_narrative_uses_sonnet(self) -> None:
        """Test narrative generation uses Sonnet model."""
        client = MockLLMClient()
        resp = client.generate_risk_narrative(
            "example.com", 50.0, [], {}
        )
        assert "sonnet" in resp.model.lower()

    def test_narrative_output_tokens(self) -> None:
        """Test narrative has reasonable output tokens."""
        client = MockLLMClient()
        resp = client.generate_risk_narrative(
            "example.com", 75.0, ["CRITICAL_CVE"], {}
        )
        assert resp.output_tokens == 150


class TestMockLLMClientOutreachDraft:
    """Test outreach draft generation logic."""

    def test_draft_includes_company_name(self) -> None:
        """Test draft includes company name."""
        client = MockLLMClient()
        resp = client.generate_outreach_draft(
            "Acme Corp", 85.0, "Infrastructure at risk."
        )
        assert "Acme Corp" in resp.content

    def test_draft_includes_risk_score(self) -> None:
        """Test draft includes risk score."""
        client = MockLLMClient()
        resp = client.generate_outreach_draft(
            "Acme Corp", 85.0, "Infrastructure at risk."
        )
        assert "85.0" in resp.content

    def test_draft_includes_narrative_excerpt(self) -> None:
        """Test draft includes excerpt from narrative."""
        client = MockLLMClient()
        resp = client.generate_outreach_draft(
            "Acme Corp", 85.0, "Infrastructure is very vulnerable."
        )
        assert "Infrastructure is" in resp.content

    def test_draft_uses_sonnet(self) -> None:
        """Test draft generation uses Sonnet model."""
        client = MockLLMClient()
        resp = client.generate_outreach_draft(
            "Acme Corp", 50.0, "Some risk narrative."
        )
        assert "sonnet" in resp.model.lower()

    def test_draft_has_email_format(self) -> None:
        """Test draft has email-like structure."""
        client = MockLLMClient()
        resp = client.generate_outreach_draft(
            "Acme Corp", 85.0, "Some risk narrative."
        )
        assert "Subject:" in resp.content
        assert "Hello" in resp.content


class TestMockLLMClientCostTracking:
    """Test cost tracking functionality."""

    def test_initial_cost_is_zero(self) -> None:
        """Test new client has zero cost."""
        client = MockLLMClient()
        assert client.get_total_cost() == 0.0

    def test_classify_signal_noise_has_cost(self) -> None:
        """Test signal/noise classification incurs cost."""
        client = MockLLMClient()
        resp = client.classify_signal_noise("example.com", ["db"], [])
        assert resp.cost_usd > 0
        assert client.get_total_cost() == resp.cost_usd

    def test_accumulate_costs_across_calls(self) -> None:
        """Test costs accumulate across multiple calls."""
        client = MockLLMClient()
        cost1 = client.classify_signal_noise(
            "a.com", ["db"], []
        ).cost_usd
        cost2 = client.infer_company_name("b.com", [], []).cost_usd

        total = client.get_total_cost()
        expected = cost1 + cost2
        assert abs(total - expected) < 0.0001

    def test_sonnet_calls_cost_more_than_haiku(self) -> None:
        """Test Sonnet calls cost more than Haiku for similar tokens."""
        client1 = MockLLMClient()
        client2 = MockLLMClient()

        haiku_resp = client1.classify_signal_noise(
            "example.com", ["db"], []
        )
        sonnet_resp = client2.generate_risk_narrative(
            "example.com", 50.0, [], {}
        )

        assert sonnet_resp.cost_usd > haiku_resp.cost_usd

    def test_reset_cost_tracking(self) -> None:
        """Test reset_cost_tracking clears costs."""
        client = MockLLMClient()
        client.classify_signal_noise("example.com", ["db"], [])
        assert client.get_total_cost() > 0

        client.reset_cost_tracking()
        assert client.get_total_cost() == 0.0

    def test_cost_tracking_does_not_clear_call_count(self) -> None:
        """Test reset_cost_tracking clears cost but not call metadata."""
        client = MockLLMClient()
        client.classify_signal_noise("example.com", ["db"], [])
        initial_call_count = client.call_count

        client.reset_cost_tracking()

        assert client.call_count == initial_call_count
        assert client.get_total_cost() == 0.0


class TestMockLLMClientCallTracking:
    """Test call counting functionality."""

    def test_initial_call_count_is_zero(self) -> None:
        """Test new client has zero call count."""
        client = MockLLMClient()
        assert client.call_count == 0

    def test_increment_call_count(self) -> None:
        """Test call count increments with each call."""
        client = MockLLMClient()
        assert client.call_count == 0

        client.classify_signal_noise("a.com", [], [])
        assert client.call_count == 1

        client.infer_company_name("b.com", [], [])
        assert client.call_count == 2

        client.generate_risk_narrative("c.com", 50.0, [], {})
        assert client.call_count == 3

        client.generate_outreach_draft("D", 50.0, "narrative")
        assert client.call_count == 4

    def test_all_methods_increment_call_count(self) -> None:
        """Test all methods increment call count."""
        client = MockLLMClient()

        client.classify_signal_noise("a.com", [], [])
        client.infer_company_name("b.com", [], [])
        client.generate_risk_narrative("c.com", 50.0, [], {})
        client.generate_outreach_draft("D", 50.0, "narrative")

        assert client.call_count == 4


class TestMockLLMClientRepr:
    """Test string representation."""

    def test_repr_empty_client(self) -> None:
        """Test repr for empty client."""
        client = MockLLMClient()
        repr_str = repr(client)
        assert "MockLLMClient" in repr_str
        assert "calls=0" in repr_str
        assert "cost=$0.0000" in repr_str

    def test_repr_with_calls(self) -> None:
        """Test repr with tracked calls."""
        client = MockLLMClient()
        client.classify_signal_noise("example.com", ["db"], [])
        repr_str = repr(client)
        assert "calls=1" in repr_str
        assert "cost=$" in repr_str
