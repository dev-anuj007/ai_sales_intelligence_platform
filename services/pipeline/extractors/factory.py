from __future__ import annotations

from typing import Any

from services.pipeline.extractors.database_exposure import DatabaseExposureExtractor
from services.pipeline.extractors.http_web import HTTPWebExtractor
from services.pipeline.extractors.iot_ot_exposure import IoTOTExposureExtractor
from services.pipeline.extractors.legacy_protocol_exposure import (
    LegacyProtocolExposureExtractor,
)
from services.pipeline.extractors.software_maturity import SoftwareMaturityExtractor
from services.pipeline.extractors.tls_security import TLSSecurityExtractor
from services.pipeline.extractors.vulnerability import VulnerabilityExtractor
from services.pipeline.schemas import ExtractedFeatures


class FeatureExtractor:
    def __init__(
        self,
        database_extractor: DatabaseExposureExtractor | None = None,
        legacy_protocol_extractor: LegacyProtocolExposureExtractor | None = None,
        iot_ot_extractor: IoTOTExposureExtractor | None = None,
        vulnerability_extractor: VulnerabilityExtractor | None = None,
        tls_extractor: TLSSecurityExtractor | None = None,
        http_extractor: HTTPWebExtractor | None = None,
        software_maturity_extractor: SoftwareMaturityExtractor | None = None,
    ) -> None:
        self.database = database_extractor or DatabaseExposureExtractor()
        self.legacy_protocol = legacy_protocol_extractor or LegacyProtocolExposureExtractor()
        self.iot_ot = iot_ot_extractor or IoTOTExposureExtractor()
        self.vulnerability = vulnerability_extractor or VulnerabilityExtractor()
        self.tls = tls_extractor or TLSSecurityExtractor()
        self.http = http_extractor or HTTPWebExtractor()
        self.software_maturity = software_maturity_extractor or SoftwareMaturityExtractor()

    def extract(self, record: dict[str, Any]) -> ExtractedFeatures:
        return ExtractedFeatures(
            database=self.database.extract(record),
            legacy_protocol=self.legacy_protocol.extract(record),
            iot_ot=self.iot_ot.extract(record),
            vulnerabilities=self.vulnerability.extract(record),
            tls=self.tls.extract(record),
            http=self.http.extract(record),
            software_maturity=self.software_maturity.extract(record),
        )


_default_extractor = FeatureExtractor()


def extract_features(record: dict[str, Any]) -> ExtractedFeatures:
    return _default_extractor.extract(record)
