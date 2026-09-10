from __future__ import annotations

from typing import Any, Protocol


class LLMClient(Protocol):
    """Protocol for LLM clients (mock or real)."""

    def generate(self, prompt: str, model: str) -> tuple[str, dict[str, Any]]:
        """Generate response from LLM.

        Args:
            prompt: The prompt text
            model: Model name (e.g., claude-haiku-4-5-20251001)

        Returns:
            Tuple of (response_text, metadata dict with input_tokens, output_tokens)
        """
        ...
