from typing import Any

from sales_intel.services.pipeline.config import get_pipeline_config


class NoiseDetector:
    def __init__(self) -> None:
        config = get_pipeline_config()
        self.noise_tags = config.infra_noise_tags.as_set()

    def is_noise(self, tags: list[str] | None) -> bool:
        if not tags:
            return False

        return bool(self.noise_tags & set(tags))

    def should_include(self, record: dict[str, Any]) -> bool:
        tags = record.get("tags") or []
        return not self.is_noise(tags)


_default_detector = NoiseDetector()


def is_infra_noise_tags(tags: list[str] | None) -> bool:
    return _default_detector.is_noise(tags)
