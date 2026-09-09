from typing import Any

from sales_intel.services.pipeline.config import get_pipeline_config
from sales_intel.services.pipeline.schemas import TLSSecurityData


class TLSSecurityExtractor:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.weak_versions = config.weak_tls_versions.as_set()

    def extract(self, record: dict[str, Any]) -> TLSSecurityData:
        ssl_data = record.get("ssl")
        if not ssl_data:
            return TLSSecurityData()

        cert = ssl_data.get("cert") or {}
        issuer = cert.get("issuer", {})
        subject = cert.get("subject", {})
        is_self_signed = issuer == subject if issuer and subject else False

        tags = set(record.get("tags") or [])
        if "self-signed" in tags:
            is_self_signed = True

        versions = set(ssl_data.get("versions") or [])
        has_weak = bool(versions & self.weak_versions)

        return TLSSecurityData(
            has_ssl=True,
            is_self_signed=is_self_signed,
            has_weak_version=has_weak,
            jarm_fingerprint=ssl_data.get("jarm"),
        )
