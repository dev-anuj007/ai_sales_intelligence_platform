from __future__ import annotations

"""Unit tests for OOP-based feature extraction.

Tests specialized extractors and the main FeatureExtractor orchestrator.
"""

import pytest

from services.pipeline.feature_extract import (
    DatabaseExposureExtractor,
    EOLLegacyFeaturesExtractor,
    FeatureExtractor,
    HTTPFeaturesExtractor,
    IoTOTExposureExtractor,
    LegacyProtocolExposureExtractor,
    TLSFeaturesExtractor,
    VulnerabilityFeaturesExtractor,
)


class TestDatabaseExposureExtractor:
    """Test database exposure detection."""

    def setup_method(self) -> None:
        self.extractor = DatabaseExposureExtractor()

    def test_known_database_port_postgres(self) -> None:
        result = self.extractor.extract({"port": 5432})
        assert result.is_exposed is True
        assert result.port == 5432

    def test_known_database_port_mongodb(self) -> None:
        result = self.extractor.extract({"port": 27017})
        assert result.is_exposed is True

    def test_non_database_port(self) -> None:
        result = self.extractor.extract({"port": 80})
        assert result.is_exposed is False

    def test_mongodb_subobject(self) -> None:
        result = self.extractor.extract({"mongodb": {"version": "4.0"}})
        assert result.is_exposed is True
        assert result.service_type == "mongodb"

    def test_redis_subobject(self) -> None:
        result = self.extractor.extract({"redis": {}})
        assert result.is_exposed is True

    def test_no_database_markers(self) -> None:
        result = self.extractor.extract({})
        assert result.is_exposed is False


class TestLegacyProtocolExposureExtractor:
    """Test legacy protocol exposure detection."""

    def setup_method(self) -> None:
        self.extractor = LegacyProtocolExposureExtractor()

    def test_ftp_port(self) -> None:
        result = self.extractor.extract({"port": 21})
        assert result.is_exposed is True
        assert result.port == 21

    def test_telnet_port(self) -> None:
        result = self.extractor.extract({"port": 23})
        assert result.is_exposed is True

    def test_rdp_port(self) -> None:
        result = self.extractor.extract({"port": 3389})
        assert result.is_exposed is True

    def test_ftp_subobject(self) -> None:
        result = self.extractor.extract({"ftp": {}})
        assert result.is_exposed is True
        assert result.protocol_type == "ftp"

    def test_modern_port(self) -> None:
        result = self.extractor.extract({"port": 443})
        assert result.is_exposed is False


class TestIoTOTExposureExtractor:
    """Test IoT/OT device exposure detection."""

    def setup_method(self) -> None:
        self.extractor = IoTOTExposureExtractor()

    def test_iot_tag(self) -> None:
        result = self.extractor.extract({"tags": ["iot"]})
        assert result.is_exposed is True
        assert result.device_type == "iot/ics"

    def test_ics_tag(self) -> None:
        result = self.extractor.extract({"tags": ["ics"]})
        assert result.is_exposed is True

    def test_hikvision_subobject(self) -> None:
        result = self.extractor.extract({"hikvision": {}})
        assert result.is_exposed is True
        assert result.device_type == "hikvision"

    def test_mikrotik_subobject(self) -> None:
        result = self.extractor.extract({"mikrotik_routeros": {}})
        assert result.is_exposed is True

    def test_no_iot_markers(self) -> None:
        result = self.extractor.extract({})
        assert result.is_exposed is False


class TestVulnerabilityFeaturesExtractor:
    """Test vulnerability feature extraction."""

    def setup_method(self) -> None:
        self.extractor = VulnerabilityFeaturesExtractor()

    def test_no_vulns(self) -> None:
        result = self.extractor.extract({})
        assert result.has_vulns is False
        assert result.count == 0

    def test_single_cve(self) -> None:
        record = {"vulns": {"CVE-2021-1234": {"cvss": 7.5, "epss": 0.25}}}
        result = self.extractor.extract(record)
        assert result.has_vulns is True
        assert result.count == 1
        assert result.max_cvss == 7.5
        assert result.max_epss == 0.25

    def test_multiple_cves_max_values(self) -> None:
        record = {
            "vulns": {
                "CVE-2021-1": {"cvss": 5.0, "epss": 0.1},
                "CVE-2021-2": {"cvss": 9.0, "epss": 0.8},
            }
        }
        result = self.extractor.extract(record)
        assert result.count == 2
        assert result.max_cvss == 9.0
        assert result.max_epss == 0.8


class TestTLSFeaturesExtractor:
    """Test SSL/TLS feature extraction."""

    def setup_method(self) -> None:
        self.extractor = TLSFeaturesExtractor()

    def test_no_ssl(self) -> None:
        result = self.extractor.extract({})
        assert result.has_ssl is False

    def test_self_signed_cert(self) -> None:
        record = {
            "ssl": {
                "cert": {
                    "issuer": {"CN": "test.com"},
                    "subject": {"CN": "test.com"},
                }
            }
        }
        result = self.extractor.extract(record)
        assert result.has_ssl is True
        assert result.is_self_signed is True

    def test_self_signed_tag(self) -> None:
        record = {"ssl": {}, "tags": ["self-signed"]}
        result = self.extractor.extract(record)
        assert result.is_self_signed is True

    def test_weak_tls_version(self) -> None:
        record = {"ssl": {"versions": ["SSLv3", "TLSv1.2"]}}
        result = self.extractor.extract(record)
        assert result.has_weak_version is True

    def test_strong_tls_version(self) -> None:
        record = {"ssl": {"versions": ["TLSv1.3"]}}
        result = self.extractor.extract(record)
        assert result.has_weak_version is False


class TestHTTPFeaturesExtractor:
    """Test HTTP feature extraction."""

    def setup_method(self) -> None:
        self.extractor = HTTPFeaturesExtractor()

    def test_no_http(self) -> None:
        result = self.extractor.extract({})
        assert result.title is None
        assert result.server is None

    def test_http_fields(self) -> None:
        record = {
            "http": {
                "title": "Apache Server",
                "server": "Apache/2.4.41",
                "status": 200,
            }
        }
        result = self.extractor.extract(record)
        assert result.title == "Apache Server"
        assert result.server == "Apache/2.4.41"
        assert result.status_code == 200

    def test_securitytxt(self) -> None:
        record = {"http": {"securitytxt": "Contact: security@example.com"}}
        result = self.extractor.extract(record)
        assert result.has_securitytxt is True


class TestEOLLegacyFeaturesExtractor:
    """Test EOL and legacy software detection."""

    def setup_method(self) -> None:
        self.extractor = EOLLegacyFeaturesExtractor()

    def test_eol_product_tag(self) -> None:
        result = self.extractor.extract({"tags": ["eol-product"]})
        assert result.is_eol is True

    def test_eol_os_tag(self) -> None:
        result = self.extractor.extract({"tags": ["eol-os"]})
        assert result.is_eol is True

    def test_honeypot_tag(self) -> None:
        result = self.extractor.extract({"tags": ["honeypot"]})
        assert result.is_honeypot is True

    def test_no_flags(self) -> None:
        result = self.extractor.extract({"tags": ["cloud"]})
        assert result.is_eol is False
        assert result.is_honeypot is False


class TestFeatureExtractorFacade:
    """Test the main FeatureExtractor orchestrator (facade pattern)."""

    def setup_method(self) -> None:
        self.extractor = FeatureExtractor()

    def test_minimal_record(self) -> None:
        """Minimal record should extract all features with safe defaults."""
        record = {"port": 80}
        features = self.extractor.extract(record)

        assert features.database.is_exposed is False
        assert features.legacy_protocol.is_exposed is False
        assert features.iot_ot.is_exposed is False
        assert features.vulnerabilities.has_vulns is False
        assert features.tls.has_ssl is False
        assert features.http.title is None
        assert features.software_maturity.is_eol is False
        assert features.software_maturity.is_honeypot is False

    def test_complete_record(self) -> None:
        """Complete record with all features should extract correctly."""
        record = {
            "port": 5432,
            "tags": ["eol-product"],
            "ssl": {"versions": ["TLSv1.2"]},
            "vulns": {"CVE-2021-1": {"cvss": 8.0, "epss": 0.5}},
            "http": {"title": "Login", "status": 200},
        }
        features = self.extractor.extract(record)

        assert features.database.is_exposed is True
        assert features.software_maturity.is_eol is True
        assert features.tls.has_ssl is True
        assert features.vulnerabilities.has_vulns is True
        assert features.http.title == "Login"

    def test_to_dict_conversion(self) -> None:
        """ExtractedFeatures should convert to flat dict for DB insertion."""
        record = {"port": 5432, "tags": ["eol-product"]}
        features = self.extractor.extract(record)
        flat_dict = features.to_db_dict()

        assert flat_dict["is_database_port"] is True
        assert flat_dict["is_eol_product"] is True
        assert "http_title" in flat_dict

    def test_dependency_injection(self) -> None:
        """Custom extractors should be injectable for testing."""
        custom_db_extractor = DatabaseExposureExtractor()

        # Override just the database extractor
        extractor = FeatureExtractor(database_extractor=custom_db_extractor)
        record = {"port": 5432}
        features = extractor.extract(record)

        assert features.database.is_exposed is True

    def test_iot_device_with_multiple_tags(self) -> None:
        """Record with IoT tag should be detected."""
        record = {"tags": ["iot", "eol-product"]}
        features = self.extractor.extract(record)

        assert features.iot_ot.is_exposed is True
        assert features.software_maturity.is_eol is True
