from __future__ import annotations

from typing import Protocol


class LLMResponse:
    """Standardized response from any LLM client with cost tracking."""

    def __init__(
        self,
        content: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
    ) -> None:
        self.content = content
        self.model = model
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens
        self.cost_usd = cost_usd

    def __repr__(self) -> str:
        return (
            f"LLMResponse(model={self.model}, "
            f"input_tokens={self.input_tokens}, "
            f"output_tokens={self.output_tokens}, "
            f"cost_usd=${self.cost_usd:.4f})"
        )


class LLMClient(Protocol):
    """Protocol for pluggable LLM clients (mock or real)."""

    def classify_signal_noise(
        self,
        domain: str,
        exposures: list[str],
        http_titles: list[str],
    ) -> LLMResponse:
        """Classify exposures as signal (real risk) or noise (false alarm)."""
        ...

    def infer_company_name(
        self,
        domain: str,
        http_titles: list[str],
        products: list[str],
    ) -> LLMResponse:
        """Infer company name from domain and HTTP server details."""
        ...

    def generate_risk_narrative(
        self,
        domain: str,
        risk_score: float,
        signal_tags: list[str],
        exposures: dict[str, int],
    ) -> LLMResponse:
        """Generate business-oriented risk narrative."""
        ...

    def generate_outreach_draft(
        self,
        company_name: str,
        risk_score: float,
        narrative: str,
    ) -> LLMResponse:
        """Generate professional outreach email draft."""
        ...

    def get_total_cost(self) -> float:
        """Return cumulative cost in USD."""
        ...

    def reset_cost_tracking(self) -> None:
        """Clear cost tracking for next batch."""
        ...
