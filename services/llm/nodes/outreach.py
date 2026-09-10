from __future__ import annotations

from config import settings
from services.llm.prompts.v1 import OutreachDraftPromptV1
from services.llm.state import EnrichmentState


def outreach_node(state: EnrichmentState) -> EnrichmentState:
    """Generate professional outreach email draft."""
    try:
        if not state.llm_client:
            state.errors.append("outreach_node failed: llm_client not provided")
            return state

        prompt = OutreachDraftPromptV1()
        prompt_text = prompt.render(
            company_name=state.company_name or state.root_domain.split(".")[0].title(),
            risk_score=f"{state.risk_score:.1f}",
            narrative=state.risk_narrative,
        )

        response_text, metadata = state.llm_client.generate(prompt_text, settings.sonnet_model)

        state.outreach_draft = response_text.strip()

        state.cost_tracking["outreach"] = {
            "model": settings.sonnet_model,
            "input_tokens": metadata.get("input_tokens", 0),
            "output_tokens": metadata.get("output_tokens", 0),
        }

    except Exception as e:
        state.errors.append(f"outreach_node failed: {str(e)}")

    return state
