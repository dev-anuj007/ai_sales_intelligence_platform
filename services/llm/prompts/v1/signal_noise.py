from __future__ import annotations

from services.llm.prompts.base import PromptTemplate


class SignalNoisePromptV1(PromptTemplate):
    """Classify exposures as signal (real security risk) or noise (false alarm)."""

    version = "v1"
    use_case = "signal_noise_classification"
    template = """You are a cybersecurity analyst. Your task is to determine whether the observed exposures represent real security risks (signal) or false alarms (noise).

Domain: {domain}

Exposures Detected:
{exposures_text}

HTTP Server Information:
{titles_text}

Analysis Guidelines:
- Real risks: Database ports exposed to internet, outdated protocols (Telnet, FTP), weak TLS versions, vulnerable services
- False alarms: Development/test servers, honeypots, CDN fronted services, cosmetic HTTP headers

Respond with ONLY one word: "signal" or "noise"

Do not include any explanation or reasoning, just the classification."""

    @staticmethod
    def render_exposures(exposures: list[str]) -> str:
        """Format exposures list for template."""
        if not exposures:
            return "- None detected"
        return "\n".join(f"- {exposure}" for exposure in exposures)

    @staticmethod
    def render_titles(titles: list[str]) -> str:
        """Format HTTP titles list for template."""
        if not titles:
            return "- None detected"
        return "\n".join(f"- {title}" for title in titles)
