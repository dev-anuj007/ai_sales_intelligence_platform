from __future__ import annotations

from typing import Any

from services.pipeline.config import get_pipeline_config
from services.pipeline.schemas import LegacyProtocolExposure


class LegacyProtocolExposureExtractor:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.legacy_ports = config.legacy_protocol_ports.as_set()
        self.legacy_service_types = config.legacy_protocol_types.as_set()

    def extract(self, record: dict[str, Any]) -> LegacyProtocolExposure:
        port = record.get("port")
        if port in self.legacy_ports:
            return LegacyProtocolExposure(is_exposed=True, port=port)

        protocol_type = self._detect_by_subobject(record)
        if protocol_type:
            return LegacyProtocolExposure(is_exposed=True, protocol_type=protocol_type)

        return LegacyProtocolExposure()

    def _detect_by_subobject(self, record: dict[str, Any]) -> str | None:
        legacy_keys = {"ftp", "telnet", "rdp_encryption", "vnc"}
        for key in legacy_keys:
            if key in record:
                return key
        return None
