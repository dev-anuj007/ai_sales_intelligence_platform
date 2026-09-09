from typing import Any

from sales_intel.services.pipeline.config import get_pipeline_config
from sales_intel.services.pipeline.schemas import IoTOTExposure


class IoTOTExposureExtractor:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.iot_ot_tags = {"iot", "ics"}
        self.device_types = config.iot_ot_device_types.as_set()

    def extract(self, record: dict[str, Any]) -> IoTOTExposure:
        tags = set(record.get("tags") or [])
        if tags & self.iot_ot_tags:
            return IoTOTExposure(is_exposed=True, device_type="iot/ics")

        for device in self.device_types:
            if record.get(device):
                return IoTOTExposure(is_exposed=True, device_type=device)

        return IoTOTExposure()
