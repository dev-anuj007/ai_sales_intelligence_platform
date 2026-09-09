from __future__ import annotations

from typing import Any, Protocol

from services.pipeline.schemas import (
    DatabaseExposure,
    ExtractedFeatures,
    HTTPWebData,
    IoTOTExposure,
    LegacyProtocolExposure,
    SoftwareMaturityData,
    TLSSecurityData,
    VulnerabilityData,
)


class DatabaseExposureExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> DatabaseExposure: ...


class LegacyProtocolExposureExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> LegacyProtocolExposure: ...


class IoTOTExposureExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> IoTOTExposure: ...


class VulnerabilityExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> VulnerabilityData: ...


class TLSSecurityExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> TLSSecurityData: ...


class HTTPWebExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> HTTPWebData: ...


class SoftwareMaturityExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> SoftwareMaturityData: ...


class FeatureExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> ExtractedFeatures: ...


class DomainExtractorInterface(Protocol):
    def extract(self, record: dict[str, Any]) -> str | None: ...


class NoiseDetectorInterface(Protocol):
    def is_noise(self, tags: list[str] | None) -> bool: ...
    def should_include(self, record: dict[str, Any]) -> bool: ...


class RecordNormalizerInterface(Protocol):
    def normalize(self, raw_record: dict[str, Any], record_id: int) -> dict[str, Any]: ...
