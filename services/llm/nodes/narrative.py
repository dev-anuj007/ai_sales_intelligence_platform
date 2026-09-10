from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from services.llm.prompts.v1 import RiskNarrativePromptV1
from services.llm.state import EnrichmentState


def narrative_node(state: EnrichmentState) -> EnrichmentState:
    """Generate business-oriented risk narrative."""
    try:
        llm = ChatAnthropic(model="claude-sonnet-5-20251022", temperature=0.7)

        prompt = RiskNarrativePromptV1()
        prompt_text = prompt.render(
            domain=state.root_domain,
            risk_score=f"{state.risk_score:.1f}",
            signal_tags_text=prompt.render_signal_tags(state.signal_tags),
            exposures_text=prompt.render_exposures(state.exposures),
        )

        message = HumanMessage(content=prompt_text)
        response = llm.invoke([message])

        state.risk_narrative = response.content.strip()

        if "usage_metadata" in response.response_metadata:
            usage = response.response_metadata["usage_metadata"]
            state.cost_tracking["narrative"] = {
                "model": "claude-sonnet-5-20251022",
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            }

    except Exception as e:
        state.errors.append(f"narrative_node failed: {str(e)}")

    return state
