from typing import Any

from sales_intel.services.pipeline.config import get_pipeline_config
from sales_intel.services.pipeline.schemas import DatabaseExposure


class DatabaseExposureExtractor:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.ports = config.database_ports.as_set()
        self.service_types = config.database_service_types.as_set()

    def extract(self, record: dict[str, Any]) -> DatabaseExposure:
        port = record.get("port")
        if port and port in self.ports:
            return DatabaseExposure(is_exposed=True, port=port)

        for service in self.service_types:
            if record.get(service):
                return DatabaseExposure(is_exposed=True, service_type=service)

        return DatabaseExposure()
