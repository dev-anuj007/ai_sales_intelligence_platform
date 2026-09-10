from __future__ import annotations

from datetime import datetime
from typing import Any

from services.pipeline.config import get_pipeline_config
from services.pipeline.domain_utils import DomainExtractor
from services.pipeline.extractors.factory import extract_features
from services.pipeline.noise_filter import NoiseDetector


class RecordNormalizer:
    def __init__(
        self,
        domain_extractor: DomainExtractor | None = None,
        noise_detector: NoiseDetector | None = None,
    ) -> None:
        self.domain_extractor = domain_extractor or DomainExtractor()
        self.noise_detector = noise_detector or NoiseDetector()
        config = get_pipeline_config()
        self.banner_max_length = config.banner_text_max_length

    def normalize(self, raw_record: dict[str, Any], record_id: int) -> dict[str, Any]:
        root_domain = self.domain_extractor.extract(raw_record)
        location = raw_record.get("location") or {}
        shodan = raw_record.get("_shodan") or {}
        features = extract_features(raw_record)
        features_dict = features.to_db_dict()
        tags = raw_record.get("tags") or []
        is_noise = self.noise_detector.is_noise(tags)
        data_snippet = self._truncate_banner(raw_record.get("data"))
        ts = self._parse_timestamp(raw_record.get("timestamp"))
        return {
            "record_id": record_id,
            "ip": raw_record.get("ip_str") or raw_record.get("ip"),
            "port": raw_record.get("port"),
            "transport": raw_record.get("transport"),
            "root_domain": root_domain,
            "hostnames": raw_record.get("hostnames", []),
            "domains": raw_record.get("domains", []),
            "org": raw_record.get("org"),
            "isp": raw_record.get("isp"),
            "asn": raw_record.get("asn"),
            "country_code": location.get("country_code"),
            "region": location.get("region_code"),
            "city": location.get("city"),
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "ts": ts,
            "product": raw_record.get("product"),
            "version": raw_record.get("version"),
            "os": raw_record.get("os"),
            "device": raw_record.get("device"),
            "devicetype": raw_record.get("devicetype"),
            "cpe": raw_record.get("cpe", []),
            "tags": tags,
            "is_infra_noise": is_noise,
            "data_snippet": data_snippet,
            "shodan_module": shodan.get("module"),
            **features_dict,
        }

    def _truncate_banner(self, data: Any) -> str | None:
        if not isinstance(data, str):
            return None
        # Remove NUL bytes which can cause database errors
        cleaned = data.replace('\x00', '')
        return cleaned[: self.banner_max_length] if len(cleaned) > self.banner_max_length else cleaned

    def _parse_timestamp(self, ts_str: str | None) -> datetime | None:
        if not ts_str:
            return None
        try:
            return datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            return None


_default_normalizer = RecordNormalizer()


def normalize_record(raw_record: dict[str, Any], record_id: int) -> dict[str, Any]:
    return _default_normalizer.normalize(raw_record, record_id)
