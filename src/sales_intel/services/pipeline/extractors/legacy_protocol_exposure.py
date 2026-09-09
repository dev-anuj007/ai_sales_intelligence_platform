from typing import Any

from sales_intel.services.pipeline.config import get_pipeline_config
from sales_intel.services.pipeline.schemas import LegacyProtocolExposure


class LegacyProtocolExposureExtractor:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.ports = config.legacy_protocol_ports.as_set()
        self.service_types = config.legacy_protocol_types.as_set()

    def extract(self, record: dict[str, Any]) -> LegacyProtocolExposure:
        port = record.get("port")
        if port and port in self.ports:
            return LegacyProtocolExposure(is_exposed=True, port=port)

        for service in self.service_types:
            if record.get(service):
                return LegacyProtocolExposure(is_exposed=True, protocol_type=service)

        return LegacyProtocolExposure()
