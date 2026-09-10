from __future__ import annotations

from services.llm.prompts.base import PromptTemplate


class CompanyInferencePromptV1(PromptTemplate):
    """Infer the company name from domain and HTTP server metadata."""

    version = "v1"
    use_case = "company_name_inference"
    template = """You are an analyst identifying companies from their internet-facing infrastructure.

    Domain: {domain}

    HTTP Server Metadata:
    {titles_text}

    Products/Software Detected:
    {products_text}

    Based on the domain and metadata above, infer the actual company name.

    Response Requirements:
    - Respond with ONLY the company name
    - No quotation marks, no explanation
    - Capitalize first letter (e.g., "Acme" not "ACME" or "acme")
    - If multiple entities exist, use the parent/parent organization
    - Examples: "amazon.com" → "Amazon", "mail.google.com" → "Google"

    Company name:"""

    @staticmethod
    def render_titles(titles: list[str]) -> str:
        if not titles:
            return "- None detected"
        return "\n".join(f"- {title}" for title in titles)

    @staticmethod
    def render_products(products: list[str]) -> str:
        if not products:
            return "- None detected"
        return "\n".join(f"- {product}" for product in products)
