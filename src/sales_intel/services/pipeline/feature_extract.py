"""Per-record feature extraction using OOP + SOLID principles.

Domain models encapsulate feature sets.
FeatureExtractor orchestrates specialized extractors for each concern.
"""

from dataclasses import dataclass, field
from typing import Any

# ===== Feature Constants =====
DATABASE_PORTS = {5432, 3306, 33060, 1433, 27017, 6379, 9200, 5984, 9042, 8086, 8123, 7474}
LEGACY_PROTOCOL_PORTS = {21, 23, 3389, 5900, 445, 139}
WEAK_TLS_VERSIONS = {"SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1"}


# ===== Domain Models (type-safe feature sets) =====


@dataclass
class DatabaseExposure:
    """Database service exposure detection."""

    is_exposed: bool = False
    port: int | None = None
    service_type: str | None = None


@dataclass
class LegacyProtocolExposure:
    """Legacy/dangerous protocol exposure (FTP, Telnet, RDP, VNC, SMB)."""

    is_exposed: bool = False
    port: int | None = None
    protocol_type: str | None = None


@dataclass
class IoTOTExposure:
    """IoT/OT device exposure (webcams, routers, HVAC, industrial control)."""

    is_exposed: bool = False
    device_type: str | None = None


@dataclass
class VulnerabilityFeatures:
    """Vulnerability features extracted from CVE data."""

    has_vulns: bool = False
    count: int = 0
    max_cvss: float | None = None
    max_epss: float | None = None
    cve_ids: list[str] = field(default_factory=list)


@dataclass
class TLSFeatures:
    """SSL/TLS security features."""

    has_ssl: bool = False
    is_self_signed: bool = False
    has_weak_version: bool = False
    jarm_fingerprint: str | None = None


@dataclass
class HTTPFeatures:
    """HTTP/web service features."""

    title: str | None = None
    server: str | None = None
    status_code: int | None = None
    has_securitytxt: bool = False


@dataclass
class EOLLegacyFeatures:
    """End-of-life and legacy software detection."""

    is_eol: bool = False
    is_honeypot: bool = False


@dataclass
class ExtractedFeatures:
    """Complete feature set from a single record (domain model)."""

    database: DatabaseExposure
    legacy_protocol: LegacyProtocolExposure
    iot_ot: IoTOTExposure
    vulnerabilities: VulnerabilityFeatures
    tls: TLSFeatures
    http: HTTPFeatures
    eol: EOLLegacyFeatures

    def to_dict(self) -> dict[str, Any]:
        """Convert to flat dict for database insertion."""
        return {
            "is_database_port": self.database.is_exposed,
            "is_legacy_protocol": self.legacy_protocol.is_exposed,
            "is_iot_ot_device": self.iot_ot.is_exposed,
            "has_vulns": self.vulnerabilities.has_vulns,
            "vuln_count": self.vulnerabilities.count,
            "max_cvss": self.vulnerabilities.max_cvss,
            "max_epss": self.vulnerabilities.max_epss,
            "vuln_ids": self.vulnerabilities.cve_ids,
            "has_ssl": self.tls.has_ssl,
            "ssl_self_signed": self.tls.is_self_signed,
            "ssl_version_weak": self.tls.has_weak_version,
            "ssl_jarm": self.tls.jarm_fingerprint,
            "http_title": self.http.title,
            "http_server": self.http.server,
            "http_status": self.http.status_code,
            "has_securitytxt": self.http.has_securitytxt,
            "is_eol_product": self.eol.is_eol,
            "is_honeypot": self.eol.is_honeypot,
        }


# ===== Specialized Extractors (SRP: each handles one concern) =====


class DatabaseExposureExtractor:
    """Extracts database service exposure signals."""

    def extract(self, record: dict[str, Any]) -> DatabaseExposure:
        """Detect database port or service exposure.

        Args:
            record: Raw Shodan record dict.

        Returns:
            DatabaseExposure with is_exposed flag.
        """
        port = record.get("port")
        if port and port in DATABASE_PORTS:
            return DatabaseExposure(is_exposed=True, port=port)

        # Check for database service sub-objects
        db_services = {"mongodb", "redis", "mysql", "mysqlx", "mssql_ssrp"}
        for service in db_services:
            if record.get(service):
                return DatabaseExposure(is_exposed=True, service_type=service)

        return DatabaseExposure()


class LegacyProtocolExposureExtractor:
    """Extracts legacy/dangerous protocol exposure signals."""

    def extract(self, record: dict[str, Any]) -> LegacyProtocolExposure:
        """Detect legacy protocol exposure (FTP, Telnet, RDP, VNC, SMB).

        Args:
            record: Raw Shodan record dict.

        Returns:
            LegacyProtocolExposure with is_exposed flag.
        """
        port = record.get("port")
        if port and port in LEGACY_PROTOCOL_PORTS:
            return LegacyProtocolExposure(is_exposed=True, port=port)

        # Check for legacy protocol sub-objects
        legacy_services = {"ftp", "telnet", "rdp_encryption", "vnc"}
        for service in legacy_services:
            if record.get(service):
                return LegacyProtocolExposure(is_exposed=True, protocol_type=service)

        return LegacyProtocolExposure()


class IoTOTExposureExtractor:
    """Extracts IoT/OT device exposure signals."""

    def extract(self, record: dict[str, Any]) -> IoTOTExposure:
        """Detect IoT/OT device exposure.

        Args:
            record: Raw Shodan record dict.

        Returns:
            IoTOTExposure with is_exposed flag.
        """
        tags = record.get("tags") or []
        if "iot" in tags or "ics" in tags:
            return IoTOTExposure(is_exposed=True, device_type="iot/ics")

        # Check for known IoT/OT device types
        iot_services = {
            "hikvision",
            "dahua",
            "dahua_dvr_web",
            "draytek_vigor",
            "mikrotik_routeros",
            "mikrotik_winbox",
            "hp_ilo",
            "ipmi",
            "qnap",
            "synology_dsm",
        }
        for service in iot_services:
            if record.get(service):
                return IoTOTExposure(is_exposed=True, device_type=service)

        return IoTOTExposure()


class VulnerabilityFeaturesExtractor:
    """Extracts vulnerability features from CVE data."""

    def extract(self, record: dict[str, Any]) -> VulnerabilityFeatures:
        """Extract vulnerability features.

        Args:
            record: Raw Shodan record dict.

        Returns:
            VulnerabilityFeatures with counts and max scores.
        """
        vulns_dict = record.get("vulns")
        if not vulns_dict:
            return VulnerabilityFeatures()

        cve_ids = list(vulns_dict.keys())
        max_cvss: float | None = None
        max_epss: float | None = None

        for cve_id, vuln_data in vulns_dict.items():
            cvss = vuln_data.get("cvss")
            if cvss is not None:
                if max_cvss is None or cvss > max_cvss:
                    max_cvss = float(cvss)

            epss = vuln_data.get("epss")
            if epss is not None:
                if max_epss is None or epss > max_epss:
                    max_epss = float(epss)

        return VulnerabilityFeatures(
            has_vulns=True,
            count=len(cve_ids),
            max_cvss=max_cvss,
            max_epss=max_epss,
            cve_ids=cve_ids,
        )


class TLSFeaturesExtractor:
    """Extracts SSL/TLS security features."""

    def extract(self, record: dict[str, Any]) -> TLSFeatures:
        """Extract TLS features.

        Args:
            record: Raw Shodan record dict.

        Returns:
            TLSFeatures with SSL details.
        """
        ssl_data = record.get("ssl")
        if not ssl_data:
            return TLSFeatures()

        # Detect self-signed cert
        cert = ssl_data.get("cert") or {}
        issuer = cert.get("issuer", {})
        subject = cert.get("subject", {})
        is_self_signed = issuer == subject if issuer and subject else False

        # Or check tags
        tags = record.get("tags") or []
        if "self-signed" in tags:
            is_self_signed = True

        # Detect weak TLS version
        has_weak_version = False
        versions = ssl_data.get("versions") or []
        if any(v in WEAK_TLS_VERSIONS for v in versions):
            has_weak_version = True

        # Extract JARM fingerprint
        jarm = ssl_data.get("jarm")

        return TLSFeatures(
            has_ssl=True,
            is_self_signed=is_self_signed,
            has_weak_version=has_weak_version,
            jarm_fingerprint=jarm,
        )


class HTTPFeaturesExtractor:
    """Extracts HTTP/web service features."""

    def extract(self, record: dict[str, Any]) -> HTTPFeatures:
        """Extract HTTP features.

        Args:
            record: Raw Shodan record dict.

        Returns:
            HTTPFeatures with title, server, status.
        """
        http_data = record.get("http") or {}

        return HTTPFeatures(
            title=http_data.get("title"),
            server=http_data.get("server"),
            status_code=http_data.get("status"),
            has_securitytxt=bool(http_data.get("securitytxt")),
        )


class EOLLegacyFeaturesExtractor:
    """Extracts end-of-life and legacy software flags."""

    def extract(self, record: dict[str, Any]) -> EOLLegacyFeatures:
        """Extract EOL/legacy flags.

        Args:
            record: Raw Shodan record dict.

        Returns:
            EOLLegacyFeatures with is_eol and is_honeypot.
        """
        tags = record.get("tags") or []

        is_eol = "eol-product" in tags or "eol-os" in tags
        is_honeypot = "honeypot" in tags

        return EOLLegacyFeatures(is_eol=is_eol, is_honeypot=is_honeypot)


# ===== Main Orchestrator (Facade) =====


class FeatureExtractor:
    """Orchestrates all feature extractors (Facade pattern).

    Dependency-injectable for testing. Each specialized extractor is injected,
    allowing easy mocking or swapping implementations.
    """

    def __init__(
        self,
        database_extractor: DatabaseExposureExtractor | None = None,
        legacy_protocol_extractor: LegacyProtocolExposureExtractor | None = None,
        iot_ot_extractor: IoTOTExposureExtractor | None = None,
        vuln_extractor: VulnerabilityFeaturesExtractor | None = None,
        tls_extractor: TLSFeaturesExtractor | None = None,
        http_extractor: HTTPFeaturesExtractor | None = None,
        eol_extractor: EOLLegacyFeaturesExtractor | None = None,
    ) -> None:
        """Initialize with optional injected extractors (defaults to standard implementations).

        Args:
            database_extractor: Injected database exposure extractor.
            legacy_protocol_extractor: Injected legacy protocol extractor.
            iot_ot_extractor: Injected IoT/OT extractor.
            vuln_extractor: Injected vulnerability extractor.
            tls_extractor: Injected TLS extractor.
            http_extractor: Injected HTTP extractor.
            eol_extractor: Injected EOL/legacy extractor.
        """
        self.database_extractor = database_extractor or DatabaseExposureExtractor()
        self.legacy_protocol_extractor = legacy_protocol_extractor or LegacyProtocolExposureExtractor()
        self.iot_ot_extractor = iot_ot_extractor or IoTOTExposureExtractor()
        self.vuln_extractor = vuln_extractor or VulnerabilityFeaturesExtractor()
        self.tls_extractor = tls_extractor or TLSFeaturesExtractor()
        self.http_extractor = http_extractor or HTTPFeaturesExtractor()
        self.eol_extractor = eol_extractor or EOLLegacyFeaturesExtractor()

    def extract(self, record: dict[str, Any]) -> ExtractedFeatures:
        """Extract all features from a record by delegating to specialized extractors.

        Args:
            record: Raw Shodan record dict.

        Returns:
            ExtractedFeatures domain model with all feature categories.
        """
        return ExtractedFeatures(
            database=self.database_extractor.extract(record),
            legacy_protocol=self.legacy_protocol_extractor.extract(record),
            iot_ot=self.iot_ot_extractor.extract(record),
            vulnerabilities=self.vuln_extractor.extract(record),
            tls=self.tls_extractor.extract(record),
            http=self.http_extractor.extract(record),
            eol=self.eol_extractor.extract(record),
        )


# ===== Backward-compatibility convenience functions (for existing code) =====


_default_extractor = FeatureExtractor()


def extract_all_features(record: dict[str, Any]) -> dict[str, Any]:
    """Convenience function: extract all features and return flat dict.

    Deprecated: use FeatureExtractor directly for better OOP design.
    This exists only for backward compatibility with existing code.

    Args:
        record: Raw Shodan record dict.

    Returns:
        Flat dict suitable for database insertion.
    """
    features = _default_extractor.extract(record)
    return features.to_dict()
