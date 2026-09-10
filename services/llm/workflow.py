from __future__ import annotations

from typing import Any

from langgraph.graph import StateGraph

from services.llm.nodes import (
    signal_noise_node,
    company_name_node,
    narrative_node,
    outreach_node,
)
from services.llm.state import EnrichmentState


def build_enrichment_workflow() -> Any:
    """Build LangGraph workflow for account enrichment.

    Workflow:
    1. Classify signal/noise (Haiku)
    2. Infer company name (Haiku)
    3. Generate risk narrative (Sonnet)
    4. Generate outreach draft (Sonnet)
    """
    workflow = StateGraph(EnrichmentState)

    workflow.add_node("signal_noise", signal_noise_node)
    workflow.add_node("company_name", company_name_node)
    workflow.add_node("narrative", narrative_node)
    workflow.add_node("outreach", outreach_node)

    workflow.add_edge("signal_noise", "company_name")
    workflow.add_edge("company_name", "narrative")
    workflow.add_edge("narrative", "outreach")

    workflow.set_entry_point("signal_noise")
    workflow.set_finish_point("outreach")

    return workflow.compile()


def create_enrichment_graph() -> Any:
    """Create and compile enrichment workflow."""
    return build_enrichment_workflow()
