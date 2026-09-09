from __future__ import annotations

from typing import Any

from services.pipeline.config import get_pipeline_config
from services.pipeline.schemas import IoTOTExposure


class IoTOTExposureExtractor:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.iot_ot_device_types = config.iot_ot_device_types.as_set()

    def extract(self, record: dict[str, Any]) -> IoTOTExposure:
        tags = record.get("tags", [])
        if tags:
            if "iot" in tags or "ics" in tags:
                return IoTOTExposure(is_exposed=True, device_type="iot/ics")

        device_type = self._detect_by_subobject(record)
        if device_type:
            return IoTOTExposure(is_exposed=True, device_type=device_type)

        return IoTOTExposure()

    def _detect_by_subobject(self, record: dict[str, Any]) -> str | None:
        iot_keys = {
            "hikvision", "dahua", "dahua_dvr_web", "draytek_vigor",
            "mikrotik_routeros", "mikrotik_winbox", "hp_ilo", "ipmi",
            "qnap", "synology_dsm",
        }
        for key in iot_keys:
            if key in record:
                return key
        return None
