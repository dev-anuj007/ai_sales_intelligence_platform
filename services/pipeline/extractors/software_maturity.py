from __future__ import annotations

from typing import Any

from services.pipeline.schemas import SoftwareMaturityData


class SoftwareMaturityExtractor:
    def extract(self, record: dict[str, Any]) -> SoftwareMaturityData:
        tags = record.get("tags", [])

        is_eol = "eol-product" in tags or "eol-os" in tags
        is_honeypot = "honeypot" in tags

        return SoftwareMaturityData(
            is_eol=is_eol,
            is_honeypot=is_honeypot,
        )
