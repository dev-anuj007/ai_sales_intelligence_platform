"""Unit tests for feature extraction (table-driven, high coverage)."""

import pytest

from sales_intel.services.pipeline.feature_extract import (
    DATABASE_PORTS,
    LEGACY_PROTOCOL_PORTS,
    WEAK_TLS_VERSIONS,
    extract_all_features,
    extract_http_features,
    extract_ssl_features,
    extract_vuln_features,
    is_database_port,
    is_eol_product,
    is_honeypot,
    is_iot_ot_device,
    is_legacy_protocol,
)


class TestDatabasePortDetection:
    """Test database port detection."""

    def test_known_database_port(self) -> None:
        """Database port 5432 (PostgreSQL) should be detected."""
        record = {"port": 5432}
        assert is_database_port(record) is True

    def test_known_database_port_mongodb(self) -> None:
        """Database port 27017 (MongoDB) should be detected."""
        record = {"port": 27017}
        assert is_database_port(record) is True

    def test_non_database_port(self) -> None:
        """Port 80 (HTTP) should not be detected as database."""
        record = {"port": 80}
        assert is_database_port(record) is False

    def test_mongodb_subobject_present(self) -> None:
        """mongodb sub-object presence should be detected."""
        record = {"port": 9999, "mongodb": {"version": "4.0"}}
        assert is_database_port(record) is True

    def test_redis_subobject_present(self) -> None:
        """redis sub-object presence should be detected."""
        record = {"port": 6379, "redis": {}}
        assert is_database_port(record) is True

    def test_no_port_or_subobject(self) -> None:
        """No port and no DB sub-object should return False."""
        record = {}
        assert is_database_port(record) is False


class TestLegacyProtocolDetection:
    """Test legacy protocol detection."""

    def test_ftp_port(self) -> None:
        """Port 21 (FTP) should be detected as legacy."""
        record = {"port": 21}
        assert is_legacy_protocol(record) is True

    def test_telnet_port(self) -> None:
        """Port 23 (Telnet) should be detected as legacy."""
        record = {"port": 23}
        assert is_legacy_protocol(record) is True

    def test_rdp_port(self) -> None:
        """Port 3389 (RDP) should be detected as legacy."""
        record = {"port": 3389}
        assert is_legacy_protocol(record) is True

    def test_ftp_subobject(self) -> None:
        """ftp sub-object should be detected."""
        record = {"port": 2121, "ftp": {}}
        assert is_legacy_protocol(record) is True

    def test_modern_port(self) -> None:
        """Port 443 (HTTPS) should not be detected as legacy."""
        record = {"port": 443}
        assert is_legacy_protocol(record) is False


class TestIoTOTDetection:
    """Test IoT/OT device detection."""

    def test_iot_tag(self) -> None:
        """'iot' tag should be detected."""
        record = {"tags": ["iot"]}
        assert is_iot_ot_device(record) is True

    def test_ics_tag(self) -> None:
        """'ics' tag should be detected."""
        record = {"tags": ["ics"]}
        assert is_iot_ot_device(record) is True

    def test_hikvision_subobject(self) -> None:
        """hikvision sub-object should be detected."""
        record = {"hikvision": {}}
        assert is_iot_ot_device(record) is True

    def test_mikrotik_subobject(self) -> None:
        """mikrotik_routeros sub-object should be detected."""
        record = {"mikrotik_routeros": {}}
        assert is_iot_ot_device(record) is True

    def test_no_iot_markers(self) -> None:
        """No IoT markers should return False."""
        record = {}
        assert is_iot_ot_device(record) is False


class TestEOLDetection:
    """Test end-of-life product detection."""

    def test_eol_product_tag(self) -> None:
        """'eol-product' tag should be detected."""
        record = {"tags": ["eol-product"]}
        assert is_eol_product(record) is True

    def test_eol_os_tag(self) -> None:
        """'eol-os' tag should be detected."""
        record = {"tags": ["eol-os"]}
        assert is_eol_product(record) is True

    def test_no_eol_tag(self) -> None:
        """No EOL tags should return False."""
        record = {"tags": ["cdn"]}
        assert is_eol_product(record) is False


class TestHoneypotDetection:
    """Test honeypot detection."""

    def test_honeypot_tag(self) -> None:
        """'honeypot' tag should be detected."""
        record = {"tags": ["honeypot"]}
        assert is_honeypot(record) is True

    def test_no_honeypot_tag(self) -> None:
        """No honeypot tag should return False."""
        record = {"tags": ["cloud"]}
        assert is_honeypot(record) is False


class TestSSLFeatureExtraction:
    """Test SSL/TLS feature extraction."""

    def test_no_ssl(self) -> None:
        """Record with no SSL should return has_ssl=False."""
        record = {}
        has_ssl, self_signed, weak_version, jarm = extract_ssl_features(record)
        assert has_ssl is False
        assert self_signed is False
        assert weak_version is False
        assert jarm is None

    def test_self_signed_cert_by_issuer_subject(self) -> None:
        """Cert with matching issuer and subject should be detected as self-signed."""
        record = {
            "ssl": {
                "cert": {
                    "issuer": {"CN": "test.com"},
                    "subject": {"CN": "test.com"},
                }
            }
        }
        has_ssl, self_signed, weak_version, jarm = extract_ssl_features(record)
        assert has_ssl is True
        assert self_signed is True

    def test_self_signed_cert_by_tag(self) -> None:
        """'self-signed' tag should be detected."""
        record = {"ssl": {}, "tags": ["self-signed"]}
        has_ssl, self_signed, weak_version, jarm = extract_ssl_features(record)
        assert has_ssl is True
        assert self_signed is True

    def test_weak_tls_version(self) -> None:
        """SSLv3 in versions should be detected as weak."""
        record = {"ssl": {"versions": ["SSLv3", "TLSv1.2"]}}
        has_ssl, self_signed, weak_version, jarm = extract_ssl_features(record)
        assert has_ssl is True
        assert weak_version is True

    def test_strong_tls_version(self) -> None:
        """TLSv1.3 should not be detected as weak."""
        record = {"ssl": {"versions": ["TLSv1.3"]}}
        has_ssl, self_signed, weak_version, jarm = extract_ssl_features(record)
        assert weak_version is False


class TestVulnFeatureExtraction:
    """Test vulnerability feature extraction."""

    def test_no_vulns(self) -> None:
        """Record with no vulns should return has_vulns=False."""
        record = {}
        has_vulns, count, max_cvss, max_epss, ids = extract_vuln_features(record)
        assert has_vulns is False
        assert count == 0
        assert max_cvss is None
        assert max_epss is None

    def test_single_cve(self) -> None:
        """Single CVE should be extracted correctly."""
        record = {
            "vulns": {
                "CVE-2021-1234": {
                    "cvss": 7.5,
                    "epss": 0.25,
                }
            }
        }
        has_vulns, count, max_cvss, max_epss, ids = extract_vuln_features(record)
        assert has_vulns is True
        assert count == 1
        assert max_cvss == 7.5
        assert max_epss == 0.25
        assert "CVE-2021-1234" in ids

    def test_multiple_cves_max_values(self) -> None:
        """Multiple CVEs should report max CVSS/EPSS."""
        record = {
            "vulns": {
                "CVE-2021-1": {"cvss": 5.0, "epss": 0.1},
                "CVE-2021-2": {"cvss": 9.0, "epss": 0.8},
            }
        }
        has_vulns, count, max_cvss, max_epss, ids = extract_vuln_features(record)
        assert count == 2
        assert max_cvss == 9.0
        assert max_epss == 0.8


class TestHTTPFeatureExtraction:
    """Test HTTP feature extraction."""

    def test_no_http(self) -> None:
        """Record with no HTTP should return None values."""
        record = {}
        title, server, status, has_sec = extract_http_features(record)
        assert title is None
        assert server is None
        assert status is None
        assert has_sec is False

    def test_http_fields(self) -> None:
        """HTTP fields should be extracted."""
        record = {
            "http": {
                "title": "Apache Server",
                "server": "Apache/2.4.41",
                "status": 200,
            }
        }
        title, server, status, has_sec = extract_http_features(record)
        assert title == "Apache Server"
        assert server == "Apache/2.4.41"
        assert status == 200

    def test_securitytxt_present(self) -> None:
        """securitytxt field should be detected."""
        record = {"http": {"securitytxt": "Contact: security@example.com"}}
        title, server, status, has_sec = extract_http_features(record)
        assert has_sec is True


class TestExtractAllFeatures:
    """Test comprehensive feature extraction."""

    def test_full_record(self) -> None:
        """All features should be extracted from a complete record."""
        record = {
            "port": 5432,
            "tags": ["eol-product"],
            "ssl": {"versions": ["TLSv1.2"]},
            "vulns": {"CVE-2021-1": {"cvss": 8.0, "epss": 0.5}},
            "http": {"title": "Login", "status": 200},
        }
        features = extract_all_features(record)

        assert features["is_database_port"] is True
        assert features["is_eol_product"] is True
        assert features["has_ssl"] is True
        assert features["ssl_version_weak"] is False
        assert features["has_vulns"] is True
        assert features["vuln_count"] == 1
        assert features["http_title"] == "Login"

    def test_minimal_record(self) -> None:
        """Minimal record should have safe defaults."""
        record = {"port": 80}
        features = extract_all_features(record)

        assert features["is_database_port"] is False
        assert features["is_legacy_protocol"] is False
        assert features["has_vulns"] is False
        assert features["http_title"] is None
