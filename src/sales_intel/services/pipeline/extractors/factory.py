from typing import Any

from sales_intel.services.pipeline.extractors.database_exposure import DatabaseExposureExtractor
from sales_intel.services.pipeline.extractors.http_web import HTTPWebExtractor
from sales_intel.services.pipeline.extractors.iot_ot_exposure import IoTOTExposureExtractor
from sales_intel.services.pipeline.extractors.legacy_protocol_exposure import (
    LegacyProtocolExposureExtractor,
)
from sales_intel.services.pipeline.extractors.software_maturity import SoftwareMaturityExtractor
from sales_intel.services.pipeline.extractors.tls_security import TLSSecurityExtractor
from sales_intel.services.pipeline.extractors.vulnerability import VulnerabilityExtractor
from sales_intel.services.pipeline.schemas import ExtractedFeatures


class FeatureExtractorFactory:
    def __init__(
        self,
        database_extractor: DatabaseExposureExtractor | None = None,
        legacy_protocol_extractor: LegacyProtocolExposureExtractor | None = None,
        iot_ot_extractor: IoTOTExposureExtractor | None = None,
        vuln_extractor: VulnerabilityExtractor | None = None,
        tls_extractor: TLSSecurityExtractor | None = None,
        http_extractor: HTTPWebExtractor | None = None,
        software_maturity_extractor: SoftwareMaturityExtractor | None = None,
    ) -> None:
        self.database_extractor = database_extractor or DatabaseExposureExtractor()
        self.legacy_protocol_extractor = legacy_protocol_extractor or LegacyProtocolExposureExtractor()
        self.iot_ot_extractor = iot_ot_extractor or IoTOTExposureExtractor()
        self.vuln_extractor = vuln_extractor or VulnerabilityExtractor()
        self.tls_extractor = tls_extractor or TLSSecurityExtractor()
        self.http_extractor = http_extractor or HTTPWebExtractor()
        self.software_maturity_extractor = software_maturity_extractor or SoftwareMaturityExtractor()

    def extract(self, record: dict[str, Any]) -> ExtractedFeatures:
        return ExtractedFeatures(
            database=self.database_extractor.extract(record),
            legacy_protocol=self.legacy_protocol_extractor.extract(record),
            iot_ot=self.iot_ot_extractor.extract(record),
            vulnerabilities=self.vuln_extractor.extract(record),
            tls=self.tls_extractor.extract(record),
            http=self.http_extractor.extract(record),
            software_maturity=self.software_maturity_extractor.extract(record),
        )


_default_factory = FeatureExtractorFactory()


def extract_features(record: dict[str, Any]) -> ExtractedFeatures:
    return _default_factory.extract(record)
