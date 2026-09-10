from __future__ import annotations

from services.llm.prompts.base import PromptTemplate


class RiskNarrativePromptV1(PromptTemplate):
    """Generate a business-oriented explanation of security risks."""

    version = "v1"
    use_case = "risk_narrative_generation"
    template = """You are a security consultant preparing a risk summary for a business stakeholder.

    Domain: {domain}
    Risk Score: {risk_score}/100 (0=lowest, 100=highest)

    Risk Indicators:
    {signal_tags_text}

    Exposure Breakdown:
    {exposures_text}

    Your task: Write a brief, business-oriented explanation of why this domain is a security concern.

    Guidelines:
    - Use business language, NOT technical jargon
    - Focus on business impact and likelihood
    - 2-3 sentences maximum
    - Avoid acronyms (no CVSS, EPSS, CVE)
    - Examples of GOOD narratives:
    * "This domain hosts a publicly accessible database with millions of customer records at risk of theft."
    * "The infrastructure runs outdated protocols vulnerable to credential theft and lateral movement."
    * "This domain has known vulnerabilities in critical software with active exploits in the wild."

    Risk narrative:"""

    @staticmethod
    def render_signal_tags(tags: list[str]) -> str:
        if not tags:
            return "- None"
        tag_descriptions = {
            "CRITICAL_CVE": "Known critical vulnerabilities (CVSS ≥ 9.0)",
            "KNOWN_VULNERABILITIES": "Known vulnerabilities with public exploits",
            "EXPOSED_DATABASE": "Database exposed to internet (MongoDB, MySQL, PostgreSQL, etc.)",
            "LEGACY_PROTOCOL": "Outdated protocols (Telnet, FTP, SMB, RDP without VPN)",
            "IOT_OT_EXPOSURE": "IoT/OT devices exposed (cameras, industrial systems, etc.)",
            "EOL_SOFTWARE": "End-of-life software versions (no security patches)",
            "WEAK_TLS": "Weak TLS versions (SSLv3, TLSv1.0, self-signed certs)",
            "CDN_FRONTED": "Behind CDN or proxy (may indicate hidden infrastructure)",
            "LARGE_ATTACK_SURFACE": "Very large asset count (many potential entry points)",
        }
        lines = []
        for tag in tags:
            desc = tag_descriptions.get(tag, tag)
            lines.append(f"- {desc}")
        return "\n".join(lines)

    @staticmethod
    def render_exposures(exposures: dict[str, int]) -> str:
        if not exposures:
            return "- None"
        lines = []
        for exposure_type, count in sorted(exposures.items()):
            lines.append(f"- {exposure_type}: {count} instance(s)")
        return "\n".join(lines)
