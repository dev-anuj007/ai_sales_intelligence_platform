from __future__ import annotations

from typing import Any

from services.llm.client import LLMClient


class MockLLMClient:
    """Mock LLM client for testing (zero API calls, deterministic responses)."""

    def __init__(self) -> None:
        self.call_count = 0
        self.calls: list[dict[str, Any]] = []

    def generate(self, prompt: str, model: str) -> tuple[str, dict[str, Any]]:
        """Return deterministic mock response."""
        self.call_count += 1
        self.calls.append({"prompt": prompt, "model": model})

        response_text = f"Mock response {self.call_count}"

        metadata: dict[str, Any] = {
            "input_tokens": 10,
            "output_tokens": 20,
        }

        return response_text, metadata
