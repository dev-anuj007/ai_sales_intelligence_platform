from __future__ import annotations

from config import settings
from services.llm.prompts.v1 import RiskNarrativePromptV1
from services.llm.state import EnrichmentState


def narrative_node(state: EnrichmentState) -> EnrichmentState:
    """Generate business-oriented risk narrative."""
    try:
        if not state.llm_client:
            state.errors.append("narrative_node failed: llm_client not provided")
            return state

        prompt = RiskNarrativePromptV1()
        prompt_text = prompt.render(
            domain=state.root_domain,
            risk_score=f"{state.risk_score:.1f}",
            signal_tags_text=prompt.render_signal_tags(state.signal_tags),
            exposures_text=prompt.render_exposures(state.exposures),
        )

        response_text, metadata = state.llm_client.generate(prompt_text, settings.sonnet_model)

        state.risk_narrative = response_text.strip()

        state.cost_tracking["narrative"] = {
            "model": settings.sonnet_model,
            "input_tokens": metadata.get("input_tokens", 0),
            "output_tokens": metadata.get("output_tokens", 0),
        }

    except Exception as e:
        state.errors.append(f"narrative_node failed: {str(e)}")

    return state
