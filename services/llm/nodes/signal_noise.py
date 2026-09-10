from __future__ import annotations

from config import settings
from services.llm.prompts.v1 import SignalNoisePromptV1
from services.llm.state import EnrichmentState


def signal_noise_node(state: EnrichmentState) -> EnrichmentState:
    """Classify exposures as signal (real risk) or noise (false alarm)."""
    try:
        if not state.llm_client:
            state.errors.append("signal_noise_node failed: llm_client not provided")
            return state

        prompt = SignalNoisePromptV1()
        prompt_text = prompt.render(
            domain=state.root_domain,
            exposures_text=prompt.render_exposures(state.signal_tags),
            titles_text=prompt.render_titles(state.http_titles),
        )

        response_text, metadata = state.llm_client.generate(prompt_text, settings.haiku_model)

        state.signal_noise_result = response_text.strip().lower()

        state.cost_tracking["signal_noise"] = {
            "model": settings.haiku_model,
            "input_tokens": metadata.get("input_tokens", 0),
            "output_tokens": metadata.get("output_tokens", 0),
        }

    except Exception as e:
        state.errors.append(f"signal_noise_node failed: {str(e)}")

    return state
