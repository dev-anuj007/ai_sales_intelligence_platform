from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from services.llm.prompts.v1 import OutreachDraftPromptV1
from services.llm.state import EnrichmentState


def outreach_node(state: EnrichmentState) -> EnrichmentState:
    """Generate professional outreach email draft."""
    try:
        llm = ChatAnthropic(model="claude-sonnet-5-20251022", temperature=0.7)

        prompt = OutreachDraftPromptV1()
        prompt_text = prompt.render(
            company_name=state.company_name or state.root_domain.split(".")[0].title(),
            risk_score=f"{state.risk_score:.1f}",
            narrative=state.risk_narrative,
        )

        message = HumanMessage(content=prompt_text)
        response = llm.invoke([message])

        state.outreach_draft = response.content.strip()

        if "usage_metadata" in response.response_metadata:
            usage = response.response_metadata["usage_metadata"]
            state.cost_tracking["outreach"] = {
                "model": "claude-sonnet-5-20251022",
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            }

    except Exception as e:
        state.errors.append(f"outreach_node failed: {str(e)}")

    return state
