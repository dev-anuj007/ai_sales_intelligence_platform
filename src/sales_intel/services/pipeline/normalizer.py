"""Normalization: raw Shodan record → staging_records row.

Maps raw Shodan JSON fields to the staging_records table schema,
with feature extraction and truncation to control storage.
"""

from datetime import datetime
from typing import Any

from sales_intel.services.pipeline.domain_utils import get_root_domain
from sales_intel.services.pipeline.feature_extract import extract_all_features
from sales_intel.services.pipeline.noise_filter import is_infra_noise_tags


def normalize_record(raw_record: dict[str, Any], record_id: int) -> dict[str, Any]:
    """Normalize a raw Shodan record for insertion into staging_records.

    Performs:
    - Domain extraction and root domain identification
    - Infra noise tagging
    - Feature extraction (CVE, SSL, HTTP, protocol exposure, etc.)
    - Banner text truncation (data_snippet, first 2KB to control storage)
    - Type normalization (arrays, timestamps)

    Args:
        raw_record: Raw Shodan JSON record.
        record_id: Sequence ID assigned during batch processing.

    Returns:
        Dict ready for insertion into staging_records table.
    """
    # Extract root domain (or None if IP-only)
    root_domain = get_root_domain(raw_record)

    # Extract location
    location = raw_record.get("location") or {}

    # Extract Shodan metadata
    shodan = raw_record.get("_shodan") or {}

    # Extract all features
    features = extract_all_features(raw_record)

    # Truncate banner text (data field)
    data_snippet = raw_record.get("data")
    if data_snippet:
        if isinstance(data_snippet, str) and len(data_snippet) > 2048:
            data_snippet = data_snippet[:2048]
        elif not isinstance(data_snippet, str):
            data_snippet = None

    # Parse timestamp
    ts_str = raw_record.get("timestamp")
    ts = None
    if ts_str:
        try:
            ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
        except (ValueError, AttributeError):
            ts = None

    # Determine noise status
    is_noise = is_infra_noise_tags(raw_record.get("tags"))

    # Build normalized record dict
    normalized = {
        "record_id": record_id,
        "ip": raw_record.get("ip_str") or raw_record.get("ip"),
        "port": raw_record.get("port"),
        "transport": raw_record.get("transport"),
        "root_domain": root_domain,
        "hostnames": raw_record.get("hostnames", []),
        "domains": raw_record.get("domains", []),
        "org": raw_record.get("org"),
        "isp": raw_record.get("isp"),
        "asn": raw_record.get("asn"),
        "country_code": location.get("country_code"),
        "region": location.get("region_code"),
        "city": location.get("city"),
        "latitude": location.get("latitude"),
        "longitude": location.get("longitude"),
        "ts": ts,
        "product": raw_record.get("product"),
        "version": raw_record.get("version"),
        "os": raw_record.get("os"),
        "device": raw_record.get("device"),
        "devicetype": raw_record.get("devicetype"),
        "cpe": raw_record.get("cpe", []),
        "tags": raw_record.get("tags", []),
        "is_infra_noise": is_noise,
        "has_vulns": features["has_vulns"],
        "vuln_count": features["vuln_count"],
        "max_cvss": features["max_cvss"],
        "max_epss": features["max_epss"],
        "vuln_ids": features["vuln_ids"],
        "has_ssl": features["has_ssl"],
        "ssl_self_signed": features["ssl_self_signed"],
        "ssl_version_weak": features["ssl_version_weak"],
        "ssl_jarm": features["ssl_jarm"],
        "http_title": features["http_title"],
        "http_server": features["http_server"],
        "http_status": features["http_status"],
        "has_securitytxt": features["has_securitytxt"],
        "is_database_port": features["is_database_port"],
        "is_legacy_protocol": features["is_legacy_protocol"],
        "is_iot_ot_device": features["is_iot_ot_device"],
        "is_eol_product": features["is_eol_product"],
        "is_honeypot": features["is_honeypot"],
        "data_snippet": data_snippet,
        "shodan_module": shodan.get("module"),
    }

    return normalized
