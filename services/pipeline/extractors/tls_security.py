from __future__ import annotations

from typing import Any

from services.pipeline.config import get_pipeline_config
from services.pipeline.schemas import TLSSecurityData


class TLSSecurityExtractor:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.weak_tls_versions = config.weak_tls_versions.as_set()

    def extract(self, record: dict[str, Any]) -> TLSSecurityData:
        ssl = record.get("ssl")
        if not ssl:
            return TLSSecurityData()

        is_self_signed = self._check_self_signed(record)
        has_weak_version = self._check_weak_version(ssl)
        jarm_fingerprint = ssl.get("jarm")

        return TLSSecurityData(
            has_ssl=True,
            is_self_signed=is_self_signed,
            has_weak_version=has_weak_version,
            jarm_fingerprint=jarm_fingerprint,
        )

    def _check_self_signed(self, record: dict[str, Any]) -> bool:
        tags = record.get("tags", [])
        if "self-signed" in tags:
            return True

        ssl = record.get("ssl", {})
        cert = ssl.get("cert", {})
        issuer = cert.get("issuer", {})
        subject = cert.get("subject", {})

        issuer_cn = issuer.get("CN")
        subject_cn = subject.get("CN")

        if issuer_cn and subject_cn and issuer_cn == subject_cn:
            return True

        return False

    def _check_weak_version(self, ssl: dict[str, Any]) -> bool:
        versions = ssl.get("versions", [])
        if not versions:
            return False
        return any(v in self.weak_tls_versions for v in versions)
