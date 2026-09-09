from typing import Any

from sales_intel.services.pipeline.schemas import HTTPWebData


class HTTPWebExtractor:
    def extract(self, record: dict[str, Any]) -> HTTPWebData:
        http_data = record.get("http") or {}

        return HTTPWebData(
            title=http_data.get("title"),
            server=http_data.get("server"),
            status_code=http_data.get("status"),
            has_securitytxt=bool(http_data.get("securitytxt")),
        )
