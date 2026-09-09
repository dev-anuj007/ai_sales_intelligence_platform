"""Base protocol for all feature extractors (Interface Segregation)."""

from typing import Any, Protocol

from sales_intel.services.pipeline.features import (
    DatabaseExposure,
    HTTPWebData,
    IoTOTExposure,
    LegacyProtocolExposure,
    SoftwareMaturityData,
    TLSSecurityData,
    VulnerabilityData,
)


class DatabaseExposureExtractorProtocol(Protocol):
    """Interface for database exposure extractors."""

    def extract(self, record: dict[str, Any]) -> DatabaseExposure:
        """Extract database exposure features."""
        ...


class LegacyProtocolExposureExtractorProtocol(Protocol):
    """Interface for legacy protocol extractors."""

    def extract(self, record: dict[str, Any]) -> LegacyProtocolExposure:
        """Extract legacy protocol exposure features."""
        ...


class IoTOTExposureExtractorProtocol(Protocol):
    """Interface for IoT/OT extractors."""

    def extract(self, record: dict[str, Any]) -> IoTOTExposure:
        """Extract IoT/OT exposure features."""
        ...


class VulnerabilityExtractorProtocol(Protocol):
    """Interface for vulnerability extractors."""

    def extract(self, record: dict[str, Any]) -> VulnerabilityData:
        """Extract vulnerability features."""
        ...


class TLSSecurityExtractorProtocol(Protocol):
    """Interface for TLS security extractors."""

    def extract(self, record: dict[str, Any]) -> TLSSecurityData:
        """Extract TLS security features."""
        ...


class HTTPWebExtractorProtocol(Protocol):
    """Interface for HTTP web extractors."""

    def extract(self, record: dict[str, Any]) -> HTTPWebData:
        """Extract HTTP web features."""
        ...


class SoftwareMaturityExtractorProtocol(Protocol):
    """Interface for software maturity extractors."""

    def extract(self, record: dict[str, Any]) -> SoftwareMaturityData:
        """Extract software maturity features."""
        ...
