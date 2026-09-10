from __future__ import annotations

from services.llm.prompts.base import PromptTemplate


class OutreachDraftPromptV1(PromptTemplate):
    """Generate a professional outreach email draft for a prospect."""

    version = "v1"
    use_case = "outreach_draft_generation"
    template = """You are writing a professional outreach email to a prospect about a critical security finding.

Company Name: {company_name}
Risk Score: {risk_score}/100

Security Finding Summary:
{narrative}

Email Goals:
1. Introduce the finding in a credible, non-alarmist way
2. Explain business impact (what could happen)
3. Create urgency without panic
4. Suggest next steps (brief call to understand their infrastructure)

Email Template:
Subject: [SUBJECT]

[EMAIL BODY]

Requirements:
- Keep total length under 150 words
- Professional but not corporate-speak
- Personalized to {company_name} (use company name once)
- Include specific finding (not generic security advice)
- End with a clear, low-friction next step (e.g., "We'd like to brief your team")
- Do NOT mention price, licensing, or sales pitch
- Do NOT use exclamation marks or aggressive language
- Focus on their risk, not our product

Email draft:"""
