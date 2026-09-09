from __future__ import annotations

from services.pipeline.extractors.database_exposure import DatabaseExposureExtractor
from services.pipeline.extractors.factory import FeatureExtractor, extract_features
from services.pipeline.extractors.http_web import HTTPWebExtractor
from services.pipeline.extractors.iot_ot_exposure import IoTOTExposureExtractor
from services.pipeline.extractors.legacy_protocol_exposure import (
    LegacyProtocolExposureExtractor,
)
from services.pipeline.extractors.software_maturity import SoftwareMaturityExtractor
from services.pipeline.extractors.tls_security import TLSSecurityExtractor
from services.pipeline.extractors.vulnerability import VulnerabilityExtractor

__all__ = [
    "DatabaseExposureExtractor",
    "LegacyProtocolExposureExtractor",
    "IoTOTExposureExtractor",
    "VulnerabilityExtractor",
    "TLSSecurityExtractor",
    "HTTPWebExtractor",
    "SoftwareMaturityExtractor",
    "FeatureExtractor",
    "extract_features",
]
