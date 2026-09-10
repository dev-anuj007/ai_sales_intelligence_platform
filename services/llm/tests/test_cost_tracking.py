from __future__ import annotations

import pytest

from services.llm.cost_model import CostTracker


class TestCostCalculation:
    """Test cost calculation from token counts and model pricing."""

    def test_haiku_input_only(self) -> None:
        """Test Haiku pricing for input tokens only."""
        cost = CostTracker.calculate_cost("claude-haiku-4-5-20251001", 1000, 0)
        expected = (1000 / 1_000_000) * 0.80
        assert abs(cost - expected) < 0.00001

    def test_haiku_output_only(self) -> None:
        """Test Haiku pricing for output tokens only."""
        cost = CostTracker.calculate_cost("claude-haiku-4-5-20251001", 0, 100)
        expected = (100 / 1_000_000) * 4.00
        assert abs(cost - expected) < 0.00001

    def test_haiku_combined(self) -> None:
        """Test Haiku pricing for input + output tokens."""
        cost = CostTracker.calculate_cost("claude-haiku-4-5-20251001", 1000, 100)
        input_cost = (1000 / 1_000_000) * 0.80
        output_cost = (100 / 1_000_000) * 4.00
        expected = round(input_cost + output_cost, 4)
        assert abs(cost - expected) < 0.00001

    def test_sonnet_input_only(self) -> None:
        """Test Sonnet pricing for input tokens only."""
        cost = CostTracker.calculate_cost("claude-sonnet-5-20251022", 1000, 0)
        expected = (1000 / 1_000_000) * 3.00
        assert abs(cost - expected) < 0.00001

    def test_sonnet_output_only(self) -> None:
        """Test Sonnet pricing for output tokens only."""
        cost = CostTracker.calculate_cost("claude-sonnet-5-20251022", 0, 100)
        expected = (100 / 1_000_000) * 15.00
        assert abs(cost - expected) < 0.00001

    def test_sonnet_combined(self) -> None:
        """Test Sonnet pricing for input + output tokens."""
        cost = CostTracker.calculate_cost("claude-sonnet-5-20251022", 1000, 100)
        input_cost = (1000 / 1_000_000) * 3.00
        output_cost = (100 / 1_000_000) * 15.00
        expected = round(input_cost + output_cost, 4)
        assert abs(cost - expected) < 0.00001

    def test_unknown_model_defaults_to_haiku(self) -> None:
        """Test unknown model defaults to Haiku pricing."""
        cost = CostTracker.calculate_cost("unknown-model", 1000, 100)
        haiku_cost = CostTracker.calculate_cost("claude-haiku-4-5-20251001", 1000, 100)
        assert cost == haiku_cost

    def test_cost_is_zero_for_zero_tokens(self) -> None:
        """Test cost is zero when both token counts are zero."""
        cost = CostTracker.calculate_cost("claude-haiku-4-5-20251001", 0, 0)
        assert cost == 0.0

    def test_cost_rounding_to_4_decimals(self) -> None:
        """Test cost is rounded to 4 decimal places."""
        cost = CostTracker.calculate_cost("claude-haiku-4-5-20251001", 123, 456)
        assert len(str(cost).split(".")[-1]) <= 4


class TestCostTracking:
    """Test CostTracker state management and accumulation."""

    def test_initial_state(self, cost_tracker: CostTracker) -> None:
        """Test tracker starts with zero state."""
        assert cost_tracker.total_input_tokens == 0
        assert cost_tracker.total_output_tokens == 0
        assert cost_tracker.total_calls == 0
        assert cost_tracker.total_cost_usd == 0.0
        assert cost_tracker.calls_by_model == {}

    def test_add_single_call(self, cost_tracker: CostTracker) -> None:
        """Test adding a single LLM call."""
        returned_cost = cost_tracker.add_call(
            "claude-haiku-4-5-20251001", 1000, 100
        )

        assert cost_tracker.total_input_tokens == 1000
        assert cost_tracker.total_output_tokens == 100
        assert cost_tracker.total_calls == 1
        assert cost_tracker.calls_by_model["claude-haiku-4-5-20251001"] == 1
        assert cost_tracker.get_total_cost() == returned_cost
        assert cost_tracker.get_total_cost() > 0

    def test_accumulate_multiple_calls(self, cost_tracker: CostTracker) -> None:
        """Test accumulating costs across multiple calls."""
        cost_tracker.add_call("claude-haiku-4-5-20251001", 1000, 100)
        cost_tracker.add_call("claude-haiku-4-5-20251001", 500, 50)

        assert cost_tracker.total_input_tokens == 1500
        assert cost_tracker.total_output_tokens == 150
        assert cost_tracker.total_calls == 2
        assert cost_tracker.calls_by_model["claude-haiku-4-5-20251001"] == 2

    def test_track_multiple_models(self, cost_tracker: CostTracker) -> None:
        """Test tracking calls across different models."""
        cost_tracker.add_call("claude-haiku-4-5-20251001", 1000, 100)
        cost_tracker.add_call("claude-sonnet-5-20251022", 2000, 200)

        assert cost_tracker.total_calls == 2
        assert cost_tracker.calls_by_model["claude-haiku-4-5-20251001"] == 1
        assert cost_tracker.calls_by_model["claude-sonnet-5-20251022"] == 1
        assert cost_tracker.total_input_tokens == 3000
        assert cost_tracker.total_output_tokens == 300

    def test_total_cost_accumulates(self, cost_tracker: CostTracker) -> None:
        """Test total cost accumulates correctly."""
        cost1 = cost_tracker.add_call("claude-haiku-4-5-20251001", 1000, 100)
        cost2 = cost_tracker.add_call("claude-haiku-4-5-20251001", 1000, 100)

        total = cost_tracker.get_total_cost()
        expected = cost1 + cost2
        assert abs(total - expected) < 0.00001

    def test_reset_clears_state(self, cost_tracker: CostTracker) -> None:
        """Test reset clears all tracking state."""
        cost_tracker.add_call("claude-haiku-4-5-20251001", 1000, 100)
        cost_tracker.reset()

        assert cost_tracker.total_input_tokens == 0
        assert cost_tracker.total_output_tokens == 0
        assert cost_tracker.total_calls == 0
        assert cost_tracker.total_cost_usd == 0.0
        assert cost_tracker.calls_by_model == {}
        assert cost_tracker.get_total_cost() == 0.0

    def test_cost_rounding_in_tracker(self, cost_tracker: CostTracker) -> None:
        """Test total cost is rounded to 4 decimal places."""
        cost_tracker.add_call("claude-haiku-4-5-20251001", 123, 456)
        cost_tracker.add_call("claude-haiku-4-5-20251001", 789, 321)

        total = cost_tracker.get_total_cost()
        assert len(str(total).split(".")[-1]) <= 4

    def test_get_total_cost_matches_added_costs(
        self, cost_tracker: CostTracker
    ) -> None:
        """Test get_total_cost matches sum of added call costs."""
        costs = []
        for i in range(5):
            cost = cost_tracker.add_call(
                "claude-haiku-4-5-20251001", 1000 + i * 100, 100 + i * 10
            )
            costs.append(cost)

        total = cost_tracker.get_total_cost()
        expected = sum(costs)
        assert abs(total - expected) < 0.00001


class TestCostTrackerRepr:
    """Test CostTracker string representation."""

    def test_repr_empty_tracker(self, cost_tracker: CostTracker) -> None:
        """Test repr for empty tracker."""
        repr_str = repr(cost_tracker)
        assert "CostTracker" in repr_str
        assert "calls=0" in repr_str
        assert "cost=$0.0000" in repr_str

    def test_repr_with_calls(self, cost_tracker: CostTracker) -> None:
        """Test repr with tracked calls."""
        cost_tracker.add_call("claude-haiku-4-5-20251001", 1000, 100)
        repr_str = repr(cost_tracker)
        assert "calls=1" in repr_str
        assert "tokens=1100" in repr_str
        assert "cost=$" in repr_str
