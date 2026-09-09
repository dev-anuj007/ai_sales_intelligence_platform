from __future__ import annotations

from typing import Any

from services.pipeline.schemas import HTTPWebData


class HTTPWebExtractor:
    def extract(self, record: dict[str, Any]) -> HTTPWebData:
        http = record.get("http")
        if not http:
            return HTTPWebData()

        title = http.get("title")
        server = http.get("server")
        status_code = http.get("status")
        has_securitytxt = bool(http.get("securitytxt"))

        return HTTPWebData(
            title=title,
            server=server,
            status_code=status_code,
            has_securitytxt=has_securitytxt,
        )
