"""Feature extractors module with proper module-level SRP.

Each extractor is in its own file. This module re-exports them for convenience.
Clients can either:
  - Import from this package: `from sales_intel.services.pipeline.extractors import extract_features`
  - Import specific extractors: `from sales_intel.services.pipeline.extractors.database_exposure import DatabaseExposureExtractor`
"""

from sales_intel.services.pipeline.extractors.database_exposure import DatabaseExposureExtractor
from sales_intel.services.pipeline.extractors.factory import FeatureExtractorFactory, extract_features
from sales_intel.services.pipeline.extractors.http_web import HTTPWebExtractor
from sales_intel.services.pipeline.extractors.iot_ot_exposure import IoTOTExposureExtractor
from sales_intel.services.pipeline.extractors.legacy_protocol_exposure import (
    LegacyProtocolExposureExtractor,
)
from sales_intel.services.pipeline.extractors.software_maturity import SoftwareMaturityExtractor
from sales_intel.services.pipeline.extractors.tls_security import TLSSecurityExtractor
from sales_intel.services.pipeline.extractors.vulnerability import VulnerabilityExtractor

__all__ = [
    "DatabaseExposureExtractor",
    "LegacyProtocolExposureExtractor",
    "IoTOTExposureExtractor",
    "VulnerabilityExtractor",
    "TLSSecurityExtractor",
    "HTTPWebExtractor",
    "SoftwareMaturityExtractor",
    "FeatureExtractorFactory",
    "extract_features",
]
