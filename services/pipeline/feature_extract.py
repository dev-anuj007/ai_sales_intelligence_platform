from __future__ import annotations

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

HTTPFeaturesExtractor = HTTPWebExtractor
TLSFeaturesExtractor = TLSSecurityExtractor
VulnerabilityFeaturesExtractor = VulnerabilityExtractor
EOLLegacyFeaturesExtractor = SoftwareMaturityExtractor

__all__ = [
    "DatabaseExposureExtractor",
    "LegacyProtocolExposureExtractor",
    "IoTOTExposureExtractor",
    "VulnerabilityFeaturesExtractor",
    "TLSFeaturesExtractor",
    "HTTPFeaturesExtractor",
    "EOLLegacyFeaturesExtractor",
    "FeatureExtractor",
]
