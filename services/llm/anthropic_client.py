from __future__ import annotations

from typing import Any

import anthropic

from services.llm.client import LLMClient


class AnthropicLLMClient:
    """Real Anthropic API client (raw SDK, not LangChain)."""

    def __init__(self, api_key: str) -> None:
        self.client = anthropic.Anthropic(api_key=api_key)

    def generate(self, prompt: str, model: str) -> tuple[str, dict[str, Any]]:
        """Call Anthropic API and return response + token counts."""
        response = self.client.messages.create(
            model=model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        text_blocks = [block for block in response.content if hasattr(block, "text")]
        response_text = text_blocks[0].text if text_blocks else ""

        metadata: dict[str, Any] = {
            "input_tokens": response.usage.input_tokens,
            "output_tokens": response.usage.output_tokens,
        }

        return response_text, metadata
