from __future__ import annotations

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
]
