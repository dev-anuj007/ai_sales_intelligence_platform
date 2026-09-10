from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from services.llm.prompts.v1 import SignalNoisePromptV1
from services.llm.state import EnrichmentState


def signal_noise_node(state: EnrichmentState) -> EnrichmentState:
    """Classify exposures as signal (real risk) or noise (false alarm)."""
    try:
        llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.0)

        prompt = SignalNoisePromptV1()
        prompt_text = prompt.render(
            domain=state.root_domain,
            exposures_text=prompt.render_exposures(state.signal_tags),
            titles_text=prompt.render_titles(state.http_titles),
        )

        message = HumanMessage(content=prompt_text)
        response = llm.invoke([message])

        state.signal_noise_result = response.content.strip().lower()

        if "usage_metadata" in response.response_metadata:
            usage = response.response_metadata["usage_metadata"]
            state.cost_tracking["signal_noise"] = {
                "model": "claude-haiku-4-5-20251001",
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            }

    except Exception as e:
        state.errors.append(f"signal_noise_node failed: {str(e)}")

    return state
