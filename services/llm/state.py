from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from services.llm.client import LLMClient


@dataclass
class EnrichmentState:
    """LangGraph state for enrichment workflow."""

    root_domain: str
    risk_score: float
    signal_tags: list[str]
    exposures: dict[str, int]
    http_titles: list[str]
    products: list[str]

    signal_noise_result: str = ""
    company_name: str = ""
    risk_narrative: str = ""
    outreach_draft: str = ""

    cost_tracking: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    llm_client: LLMClient | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dict for serialization (excludes llm_client)."""
        return {
            "root_domain": self.root_domain,
            "risk_score": self.risk_score,
            "signal_tags": self.signal_tags,
            "exposures": self.exposures,
            "http_titles": self.http_titles,
            "products": self.products,
            "signal_noise_result": self.signal_noise_result,
            "company_name": self.company_name,
            "risk_narrative": self.risk_narrative,
            "outreach_draft": self.outreach_draft,
            "cost_tracking": self.cost_tracking,
            "errors": self.errors,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any], llm_client: LLMClient | None = None) -> EnrichmentState:
        """Create state from dict and optionally inject llm_client."""
        return cls(llm_client=llm_client, **data)
