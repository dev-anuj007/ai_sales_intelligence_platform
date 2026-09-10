from __future__ import annotations

from typing import Any

from services.pipeline.config import (
    DatabasePortsConfig,
    LegacyProtocolPortsConfig,
    WeakTLSVersionsConfig,
)
from services.pipeline.extractors import (
    DatabaseExposureExtractor,
    FeatureExtractor,
    HTTPWebExtractor,
    IoTOTExposureExtractor,
    LegacyProtocolExposureExtractor,
    SoftwareMaturityExtractor,
    TLSSecurityExtractor,
    VulnerabilityExtractor,
)
from services.pipeline.schemas import ExtractedFeatures

DATABASE_PORTS = DatabasePortsConfig().as_set()
LEGACY_PROTOCOL_PORTS = LegacyProtocolPortsConfig().as_set()
WEAK_TLS_VERSIONS = WeakTLSVersionsConfig().as_set()

HTTPFeaturesExtractor = HTTPWebExtractor
TLSFeaturesExtractor = TLSSecurityExtractor
VulnerabilityFeaturesExtractor = VulnerabilityExtractor
EOLLegacyFeaturesExtractor = SoftwareMaturityExtractor


def is_iot_ot_device(record: dict[str, Any]) -> bool:
    extractor = IoTOTExposureExtractor()
    result = extractor.extract(record)
    return result.is_exposed


def is_eol_product(record: dict[str, Any]) -> bool:
    extractor = SoftwareMaturityExtractor()
    result = extractor.extract(record)
    return result.is_eol


def is_honeypot(record: dict[str, Any]) -> bool:
    extractor = SoftwareMaturityExtractor()
    result = extractor.extract(record)
    return result.is_honeypot


def extract_ssl_features(record: dict[str, Any]) -> tuple[bool, bool, bool, str | None]:
    extractor = TLSSecurityExtractor()
    result = extractor.extract(record)
    return (result.has_ssl, result.is_self_signed, result.has_weak_version, result.jarm_fingerprint)


def extract_vuln_features(record: dict[str, Any]) -> tuple[bool, int, float | None, float | None, list[str]]:
    extractor = VulnerabilityExtractor()
    result = extractor.extract(record)
    return (result.has_vulns, result.count, result.max_cvss, result.max_epss, result.cve_ids)


def extract_http_features(record: dict[str, Any]) -> tuple[str | None, str | None, int | None, bool]:
    extractor = HTTPWebExtractor()
    result = extractor.extract(record)
    return (result.title, result.server, result.status_code, result.has_securitytxt)


def extract_all_features(record: dict[str, Any]) -> dict[str, Any]:
    extractor = FeatureExtractor()
    result = extractor.extract(record)
    return result.to_db_dict()


__all__ = [
    "DATABASE_PORTS",
    "LEGACY_PROTOCOL_PORTS",
    "WEAK_TLS_VERSIONS",
    "DatabaseExposureExtractor",
    "LegacyProtocolExposureExtractor",
    "IoTOTExposureExtractor",
    "VulnerabilityFeaturesExtractor",
    "TLSFeaturesExtractor",
    "HTTPFeaturesExtractor",
    "EOLLegacyFeaturesExtractor",
    "FeatureExtractor",
    "ExtractedFeatures",
    "is_iot_ot_device",
    "is_eol_product",
    "is_honeypot",
    "extract_ssl_features",
    "extract_vuln_features",
    "extract_http_features",
    "extract_all_features",
]
