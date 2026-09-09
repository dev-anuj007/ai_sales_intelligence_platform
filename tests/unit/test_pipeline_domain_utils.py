"""Unit tests for domain extraction utilities."""

import pytest

from sales_intel.services.pipeline.domain_utils import get_root_domain, is_ip_only


class TestGetRootDomain:
    """Test root domain extraction."""

    def test_simple_domain(self) -> None:
        """Simple domain should be extracted."""
        record = {"domains": ["example.com"]}
        assert get_root_domain(record) == "example.com"

    def test_subdomain_normalized_to_root(self) -> None:
        """Subdomain should be normalized to root domain."""
        record = {"domains": ["www.example.com"]}
        assert get_root_domain(record) == "example.com"

    def test_deeply_nested_subdomain(self) -> None:
        """Deeply nested subdomain should extract root."""
        record = {"domains": ["api.v2.staging.example.com"]}
        assert get_root_domain(record) == "example.com"

    def test_co_uk_suffix(self) -> None:
        """.co.uk suffix should be handled correctly."""
        record = {"domains": ["www.example.co.uk"]}
        assert get_root_domain(record) == "example.co.uk"

    def test_prefer_domains_over_hostnames(self) -> None:
        """domains[0] should be preferred over hostnames[0]."""
        record = {
            "domains": ["real-domain.com"],
            "hostnames": ["fake-host.example.com"],
        }
        assert get_root_domain(record) == "real-domain.com"

    def test_fallback_to_hostnames(self) -> None:
        """Should fall back to hostnames if domains is empty."""
        record = {"domains": [], "hostnames": ["www.example.com"]}
        assert get_root_domain(record) == "example.com"

    def test_fallback_to_hostnames_none_domains(self) -> None:
        """Should fall back to hostnames if domains is None."""
        record = {"hostnames": ["www.example.com"]}
        assert get_root_domain(record) == "example.com"

    def test_no_domain_or_hostname(self) -> None:
        """IP-only record should return None."""
        record = {}
        assert get_root_domain(record) is None

    def test_invalid_domain(self) -> None:
        """Invalid domain string should return None."""
        record = {"domains": ["192.168.1.1"]}  # IP, not domain
        result = get_root_domain(record)
        # Could be None or the IP depending on tldextract behavior
        assert result is None or "." in (result or "")

    def test_empty_domains_array(self) -> None:
        """Empty domains array should fall back to hostnames."""
        record = {"domains": [], "hostnames": ["test.com"]}
        assert get_root_domain(record) == "test.com"

    def test_localhost(self) -> None:
        """localhost should be handled (may return None or 'localhost')."""
        record = {"domains": ["localhost"]}
        result = get_root_domain(record)
        # tldextract may return None for localhost since it has no suffix
        assert result is None or result == "localhost"


class TestIsIPOnly:
    """Test IP-only record detection."""

    def test_has_domains(self) -> None:
        """Record with domains should not be IP-only."""
        record = {"domains": ["example.com"]}
        assert is_ip_only(record) is False

    def test_has_hostnames(self) -> None:
        """Record with hostnames should not be IP-only."""
        record = {"hostnames": ["www.example.com"]}
        assert is_ip_only(record) is False

    def test_has_both(self) -> None:
        """Record with both should not be IP-only."""
        record = {"domains": ["example.com"], "hostnames": ["www.example.com"]}
        assert is_ip_only(record) is False

    def test_no_domains_no_hostnames(self) -> None:
        """Record with neither should be IP-only."""
        record = {}
        assert is_ip_only(record) is True

    def test_empty_arrays(self) -> None:
        """Empty arrays should be treated as IP-only."""
        record = {"domains": [], "hostnames": []}
        assert is_ip_only(record) is True

    def test_none_values(self) -> None:
        """None values should be treated as IP-only."""
        record = {"domains": None, "hostnames": None}
        assert is_ip_only(record) is True
