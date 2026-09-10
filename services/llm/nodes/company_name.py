from __future__ import annotations

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage

from services.llm.prompts.v1 import CompanyInferencePromptV1
from services.llm.state import EnrichmentState


def company_name_node(state: EnrichmentState) -> EnrichmentState:
    """Infer company name from domain and HTTP metadata."""
    try:
        llm = ChatAnthropic(model="claude-haiku-4-5-20251001", temperature=0.0)

        prompt = CompanyInferencePromptV1()
        prompt_text = prompt.render(
            domain=state.root_domain,
            titles_text=prompt.render_titles(state.http_titles),
            products_text=prompt.render_products(state.products),
        )

        message = HumanMessage(content=prompt_text)
        response = llm.invoke([message])

        state.company_name = response.content.strip()

        if "usage_metadata" in response.response_metadata:
            usage = response.response_metadata["usage_metadata"]
            state.cost_tracking["company_name"] = {
                "model": "claude-haiku-4-5-20251001",
                "input_tokens": usage.get("input_tokens", 0),
                "output_tokens": usage.get("output_tokens", 0),
            }

    except Exception as e:
        state.errors.append(f"company_name_node failed: {str(e)}")

    return state
