"""Per-record feature extraction.

Computes boolean and numeric flags for each Shodan record that become
input to the scoring engine. All constants centralized here for easy tuning.
"""

from typing import Any

# ===== Port Constants =====
DATABASE_PORTS = {5432, 3306, 33060, 1433, 27017, 6379, 9200, 5984, 9042, 8086, 8123, 7474}
LEGACY_PROTOCOL_PORTS = {21, 23, 3389, 5900, 445, 139}

# ===== TLS/SSL Constants =====
WEAK_TLS_VERSIONS = {"SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1"}


def is_database_port(record: dict) -> bool:
    """Detect if record exposes a database service.

    Checks for known database ports or protocol-specific sub-objects.

    Args:
        record: Raw Shodan record dict.

    Returns:
        True if database exposure detected.
    """
    port = record.get("port")
    if port and port in DATABASE_PORTS:
        return True

    # Check for protocol-specific sub-objects indicating DB service
    db_services = {"mongodb", "redis", "mysql", "mysqlx", "mssql_ssrp"}
    for service in db_services:
        if record.get(service):
            return True

    return False


def is_legacy_protocol(record: dict) -> bool:
    """Detect legacy/dangerous protocol exposure (FTP, Telnet, RDP, VNC, SMB).

    Args:
        record: Raw Shodan record dict.

    Returns:
        True if legacy protocol detected.
    """
    port = record.get("port")
    if port and port in LEGACY_PROTOCOL_PORTS:
        return True

    # Check for protocol-specific sub-objects
    legacy_services = {"ftp", "telnet", "rdp_encryption", "vnc"}
    for service in legacy_services:
        if record.get(service):
            return True

    return False


def is_iot_ot_device(record: dict) -> bool:
    """Detect IoT/OT device exposure (webcams, routers, HVAC, etc.).

    Args:
        record: Raw Shodan record dict.

    Returns:
        True if IoT/OT device detected.
    """
    tags = record.get("tags") or []
    if "iot" in tags or "ics" in tags:
        return True

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
            return True

    return False


def is_eol_product(record: dict) -> bool:
    """Detect end-of-life or end-of-support software.

    Indicates neglected, unpatched assets.

    Args:
        record: Raw Shodan record dict.

    Returns:
        True if EOL/EOS product detected.
    """
    tags = record.get("tags") or []
    return "eol-product" in tags or "eol-os" in tags


def is_honeypot(record: dict) -> bool:
    """Detect honeypot deception asset.

    Args:
        record: Raw Shodan record dict.

    Returns:
        True if record is tagged as honeypot.
    """
    tags = record.get("tags") or []
    return "honeypot" in tags


def extract_ssl_features(record: dict) -> tuple[bool, bool, bool, str | None]:
    """Extract SSL/TLS features from record.

    Args:
        record: Raw Shodan record dict.

    Returns:
        Tuple of (has_ssl, ssl_self_signed, ssl_version_weak, ssl_jarm).
    """
    ssl_data = record.get("ssl")
    if not ssl_data:
        return False, False, False, None

    has_ssl = True

    # Detect self-signed cert
    cert = ssl_data.get("cert") or {}
    issuer = cert.get("issuer", {})
    subject = cert.get("subject", {})
    ssl_self_signed = issuer == subject if issuer and subject else False

    # Or check tags
    tags = record.get("tags") or []
    if "self-signed" in tags:
        ssl_self_signed = True

    # Detect weak TLS version
    ssl_version_weak = False
    versions = ssl_data.get("versions") or []
    if any(v in WEAK_TLS_VERSIONS for v in versions):
        ssl_version_weak = True

    # Extract JARM fingerprint (optional, for fingerprinting)
    ssl_jarm = ssl_data.get("jarm")

    return has_ssl, ssl_self_signed, ssl_version_weak, ssl_jarm


def extract_vuln_features(record: dict) -> tuple[bool, int, float | None, float | None, list[str]]:
    """Extract vulnerability features from record.

    Args:
        record: Raw Shodan record dict.

    Returns:
        Tuple of (has_vulns, vuln_count, max_cvss, max_epss, vuln_ids).
    """
    vulns_dict = record.get("vulns")
    if not vulns_dict:
        return False, 0, None, None, []

    has_vulns = True
    cve_ids = list(vulns_dict.keys())
    vuln_count = len(cve_ids)

    # Extract max CVSS and EPSS across all CVEs
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

    return has_vulns, vuln_count, max_cvss, max_epss, cve_ids


def extract_http_features(record: dict) -> tuple[str | None, str | None, int | None, bool]:
    """Extract HTTP/web features from record.

    Args:
        record: Raw Shodan record dict.

    Returns:
        Tuple of (http_title, http_server, http_status, has_securitytxt).
    """
    http_data = record.get("http") or {}

    http_title = http_data.get("title")
    http_server = http_data.get("server")
    http_status = http_data.get("status")
    has_securitytxt = bool(http_data.get("securitytxt"))

    return http_title, http_server, http_status, has_securitytxt


def extract_all_features(record: dict) -> dict[str, Any]:
    """Extract all features from a raw Shodan record.

    Returns a dict of feature flags and values suitable for insertion
    into the staging_records table.

    Args:
        record: Raw Shodan record dict.

    Returns:
        Dict with all extracted feature flags.
    """
    # SSL features
    has_ssl, ssl_self_signed, ssl_version_weak, ssl_jarm = extract_ssl_features(record)

    # Vulnerability features
    has_vulns, vuln_count, max_cvss, max_epss, vuln_ids = extract_vuln_features(record)

    # HTTP features
    http_title, http_server, http_status, has_securitytxt = extract_http_features(record)

    return {
        "is_database_port": is_database_port(record),
        "is_legacy_protocol": is_legacy_protocol(record),
        "is_iot_ot_device": is_iot_ot_device(record),
        "is_eol_product": is_eol_product(record),
        "is_honeypot": is_honeypot(record),
        "has_ssl": has_ssl,
        "ssl_self_signed": ssl_self_signed,
        "ssl_version_weak": ssl_version_weak,
        "ssl_jarm": ssl_jarm,
        "has_vulns": has_vulns,
        "vuln_count": vuln_count,
        "max_cvss": max_cvss,
        "max_epss": max_epss,
        "vuln_ids": vuln_ids,
        "http_title": http_title,
        "http_server": http_server,
        "http_status": http_status,
        "has_securitytxt": has_securitytxt,
    }
