from typing import Any

from sales_intel.services.pipeline.schemas import SoftwareMaturityData


class SoftwareMaturityExtractor:
    def __init__(self) -> None:
        self.eol_tags = {"eol-product", "eol-os"}
        self.honeypot_tag = "honeypot"

    def extract(self, record: dict[str, Any]) -> SoftwareMaturityData:
        tags = set(record.get("tags") or [])

        return SoftwareMaturityData(
            is_eol=bool(tags & self.eol_tags),
            is_honeypot=self.honeypot_tag in tags,
        )
