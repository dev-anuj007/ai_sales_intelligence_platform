from __future__ import annotations

HAIKU_INPUT_COST_PER_1M: float = 0.80
HAIKU_OUTPUT_COST_PER_1M: float = 4.00
SONNET_INPUT_COST_PER_1M: float = 3.00
SONNET_OUTPUT_COST_PER_1M: float = 15.00


class CostTracker:
    """Track LLM API costs in USD with exact token counts."""

    def __init__(self) -> None:
        self.total_input_tokens: int = 0
        self.total_output_tokens: int = 0
        self.total_calls: int = 0
        self.calls_by_model: dict[str, int] = {}
        self.total_cost_usd: float = 0.0

    def add_call(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Record a single LLM call and return cost in USD."""
        cost = self.calculate_cost(model, input_tokens, output_tokens)

        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.total_calls += 1
        self.calls_by_model[model] = self.calls_by_model.get(model, 0) + 1
        self.total_cost_usd += cost

        return cost

    @staticmethod
    def calculate_cost(
        model: str,
        input_tokens: int,
        output_tokens: int,
    ) -> float:
        """Deterministic cost calculation from token counts and model pricing."""
        if "haiku" in model.lower():
            input_cost = (input_tokens / 1_000_000) * HAIKU_INPUT_COST_PER_1M
            output_cost = (output_tokens / 1_000_000) * HAIKU_OUTPUT_COST_PER_1M
        elif "sonnet" in model.lower():
            input_cost = (input_tokens / 1_000_000) * SONNET_INPUT_COST_PER_1M
            output_cost = (output_tokens / 1_000_000) * SONNET_OUTPUT_COST_PER_1M
        else:
            input_cost = (input_tokens / 1_000_000) * HAIKU_INPUT_COST_PER_1M
            output_cost = (output_tokens / 1_000_000) * HAIKU_OUTPUT_COST_PER_1M

        return round(input_cost + output_cost, 4)

    def get_total_cost(self) -> float:
        """Return cumulative cost in USD."""
        return round(self.total_cost_usd, 4)

    def reset(self) -> None:
        """Clear all tracking for next batch."""
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        self.total_calls = 0
        self.calls_by_model = {}
        self.total_cost_usd = 0.0

    def __repr__(self) -> str:
        return (
            f"CostTracker(calls={self.total_calls}, "
            f"tokens={self.total_input_tokens + self.total_output_tokens}, "
            f"cost=${self.total_cost_usd:.4f})"
        )
