"""Infrastructure noise detection and filtering.

Records tagged with infra-related tags (CDN, cloud, proxy, honeypot, VPN, Tor)
are marked as noise. This is a rule-level filter applied to all records at
ingest time; a separate LLM re-classification later re-checks only top-scored
accounts for ambiguous cases.

Design: tag-based (not org/isp/asn-based) because those fields describe
hosting infrastructure providers, not the target business.
"""

# Tags indicating infrastructure/non-target assets
_INFRA_NOISE_TAGS = {
    "cdn",       # Content Delivery Network (Incapsula, CloudFlare, Akamai, etc.)
    "cloud",     # Cloud provider (AWS, Google, Azure edge nodes)
    "proxy",     # HTTP/SOCKS proxy
    "vpn",       # VPN endpoint
    "honeypot",  # Deception asset
    "tor",       # Tor exit node
}


def is_infra_noise_tags(tags: list[str] | None) -> bool:
    """Check if a record should be filtered as infrastructure noise.

    Args:
        tags: List of tags from the Shodan record.

    Returns:
        True if any tag indicates infrastructure/non-target asset.
    """
    if not tags:
        return False

    return bool(_INFRA_NOISE_TAGS.intersection(tags))


def should_include_record(record: dict) -> bool:
    """Determine if a record should be included in accounts aggregation.

    A record is excluded (noise) if it's tagged as infra.

    Args:
        record: Raw Shodan record dict (after domain extraction).

    Returns:
        True if record should be included in analysis.
    """
    tags = record.get("tags") or []
    return not is_infra_noise_tags(tags)
