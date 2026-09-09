"""Domain utilities for root domain extraction.

Uses tldextract with offline public suffix list to identify company domains
from Shodan records. No network fetches at runtime.
"""

import tldextract

# Initialize tldextract with offline mode (no network fetch at runtime)
# Uses bundled public suffix list snapshot
_EXTRACTOR = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)


def get_root_domain(record: dict) -> str | None:
    """Extract the root (registrable) domain from a Shodan record.

    Prefers 'domains' field (Shodan's primary domain), falls back to 'hostnames',
    then returns None if neither is available.

    Args:
        record: Raw Shodan record dict.

    Returns:
        Root domain (e.g., 'example.com'), or None if no domain found.
    """
    # Prefer domains[0] (Shodan's primary domain)
    candidates = record.get("domains") or []

    # Fall back to hostnames[0]
    if not candidates:
        hostnames = record.get("hostnames") or []
        if hostnames:
            candidates = [hostnames[0]]

    if not candidates:
        return None

    # Extract root domain using tldextract
    domain_str = candidates[0]
    try:
        result = _EXTRACTOR(domain_str)

        # Need both domain and suffix to form a valid root domain
        if result.domain and result.suffix:
            return f"{result.domain}.{result.suffix}"

        return None

    except Exception:
        # If extraction fails, return None (invalid domain)
        return None


def is_ip_only(record: dict) -> bool:
    """Check if record has no domain/hostname (IP-only asset).

    Args:
        record: Raw Shodan record dict.

    Returns:
        True if record has neither domains nor hostnames.
    """
    domains = record.get("domains") or []
    hostnames = record.get("hostnames") or []
    return len(domains) == 0 and len(hostnames) == 0
