from __future__ import annotations

from services.llm.abstractions import LLMResponse
from services.llm.cost_model import CostTracker


class MockLLMClient:
    """Mock LLM client for testing: deterministic, no API calls, realistic costs."""

    def __init__(self) -> None:
        self.cost_tracker = CostTracker()
        self.call_count: int = 0

    def classify_signal_noise(
        self,
        domain: str,
        exposures: list[str],
        http_titles: list[str],
    ) -> LLMResponse:
        self.call_count += 1

        is_signal = len(exposures) > 0
        response_text = "signal" if is_signal else "noise"

        input_tokens = 150 + len(domain) + sum(len(e) for e in exposures)
        output_tokens = 50

        cost = self.cost_tracker.add_call(
            "claude-haiku-4-5-20251001",
            input_tokens,
            output_tokens,
        )

        return LLMResponse(
            content=response_text,
            model="claude-haiku-4-5-20251001",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

    def infer_company_name(
        self,
        domain: str,
        http_titles: list[str],
        products: list[str],
    ) -> LLMResponse:
        self.call_count += 1

        company = domain.split(".")[0].title()

        input_tokens = 120 + len(domain) + sum(len(t) for t in http_titles)
        output_tokens = 30

        cost = self.cost_tracker.add_call(
            "claude-haiku-4-5-20251001",
            input_tokens,
            output_tokens,
        )

        return LLMResponse(
            content=company,
            model="claude-haiku-4-5-20251001",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

    def generate_risk_narrative(
        self,
        domain: str,
        risk_score: float,
        signal_tags: list[str],
        exposures: dict[str, int],
    ) -> LLMResponse:
        self.call_count += 1

        narrative = f"The domain {domain} has a risk score of {risk_score:.1f}/100."

        input_tokens = 300 + len(domain) + len(str(signal_tags))
        output_tokens = 150

        cost = self.cost_tracker.add_call(
            "claude-sonnet-5-20251022",
            input_tokens,
            output_tokens,
        )

        return LLMResponse(
            content=narrative,
            model="claude-sonnet-5-20251022",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

    def generate_outreach_draft(
        self,
        company_name: str,
        risk_score: float,
        narrative: str,
    ) -> LLMResponse:
        self.call_count += 1

        draft = (
            f"Subject: Security Alert for {company_name}\n\n"
            f"Hello {company_name} Team,\n\n"
            f"We've identified critical security risks in your infrastructure "
            f"with a risk score of {risk_score:.1f}/100.\n\n"
            f"Key findings: {narrative[:60]}...\n\n"
            f"We'd like to help you secure your environment.\n\n"
            f"Best regards"
        )

        input_tokens = 250 + len(company_name) + len(narrative)
        output_tokens = 200

        cost = self.cost_tracker.add_call(
            "claude-sonnet-5-20251022",
            input_tokens,
            output_tokens,
        )

        return LLMResponse(
            content=draft,
            model="claude-sonnet-5-20251022",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )

    def get_total_cost(self) -> float:
        return self.cost_tracker.get_total_cost()

    def reset_cost_tracking(self) -> None:
        self.cost_tracker.reset()

    def __repr__(self) -> str:
        return (
            f"MockLLMClient(calls={self.call_count}, "
            f"cost=${self.get_total_cost():.4f})"
        )
