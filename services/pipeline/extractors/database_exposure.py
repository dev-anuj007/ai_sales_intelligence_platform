from __future__ import annotations

from typing import Any

from services.pipeline.config import get_pipeline_config
from services.pipeline.schemas import DatabaseExposure


class DatabaseExposureExtractor:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.db_ports = config.database_ports.as_set()
        self.db_service_types = config.database_service_types.as_set()

    def extract(self, record: dict[str, Any]) -> DatabaseExposure:
        port = record.get("port")
        if port in self.db_ports:
            return DatabaseExposure(is_exposed=True, port=port)

        service_type = self._detect_by_subobject(record)
        if service_type:
            return DatabaseExposure(is_exposed=True, service_type=service_type)

        return DatabaseExposure()

    def _detect_by_subobject(self, record: dict[str, Any]) -> str | None:
        db_keys = {"mongodb", "redis", "mysql", "mysqlx", "mssql_ssrp", "postgres"}
        for key in db_keys:
            if key in record:
                return key
        return None
