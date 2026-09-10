from __future__ import annotations

from config import settings
from services.llm.prompts.v1 import CompanyInferencePromptV1
from services.llm.state import EnrichmentState


def company_name_node(state: EnrichmentState) -> EnrichmentState:
    """Infer company name from domain and HTTP metadata."""
    try:
        if not state.llm_client:
            state.errors.append("company_name_node failed: llm_client not provided")
            return state

        prompt = CompanyInferencePromptV1()
        prompt_text = prompt.render(
            domain=state.root_domain,
            titles_text=prompt.render_titles(state.http_titles),
            products_text=prompt.render_products(state.products),
        )

        response_text, metadata = state.llm_client.generate(prompt_text, settings.haiku_model)

        state.company_name = response_text.strip()

        state.cost_tracking["company_name"] = {
            "model": settings.haiku_model,
            "input_tokens": metadata.get("input_tokens", 0),
            "output_tokens": metadata.get("output_tokens", 0),
        }

    except Exception as e:
        state.errors.append(f"company_name_node failed: {str(e)}")

    return state
