"""Unit tests for infrastructure noise filtering."""

import pytest

from sales_intel.services.pipeline.noise_filter import (
    is_infra_noise_tags,
    should_include_record,
)


class TestIsInfraNoiseTags:
    """Test infra noise tag detection."""

    def test_cdn_tag(self) -> None:
        """'cdn' tag should be detected as noise."""
        assert is_infra_noise_tags(["cdn"]) is True

    def test_cloud_tag(self) -> None:
        """'cloud' tag should be detected as noise."""
        assert is_infra_noise_tags(["cloud"]) is True

    def test_proxy_tag(self) -> None:
        """'proxy' tag should be detected as noise."""
        assert is_infra_noise_tags(["proxy"]) is True

    def test_vpn_tag(self) -> None:
        """'vpn' tag should be detected as noise."""
        assert is_infra_noise_tags(["vpn"]) is True

    def test_honeypot_tag(self) -> None:
        """'honeypot' tag should be detected as noise."""
        assert is_infra_noise_tags(["honeypot"]) is True

    def test_tor_tag(self) -> None:
        """'tor' tag should be detected as noise."""
        assert is_infra_noise_tags(["tor"]) is True

    def test_multiple_infra_tags(self) -> None:
        """Multiple infra tags should be detected."""
        assert is_infra_noise_tags(["cdn", "cloud"]) is True

    def test_mixed_tags_with_noise(self) -> None:
        """Mixed tags including noise should be detected."""
        assert is_infra_noise_tags(["database", "cdn"]) is True

    def test_non_noise_tags(self) -> None:
        """Non-infra tags should not be detected as noise."""
        assert is_infra_noise_tags(["eol-product", "database"]) is False

    def test_empty_tags(self) -> None:
        """Empty tag list should not be noise."""
        assert is_infra_noise_tags([]) is False

    def test_none_tags(self) -> None:
        """None should not be detected as noise."""
        assert is_infra_noise_tags(None) is False

    def test_case_sensitivity(self) -> None:
        """Tag matching should be case-sensitive (lowercase expected)."""
        # Tags should be lowercase in Shodan data, but test defensively
        assert is_infra_noise_tags(["CDN"]) is False  # uppercase not matched
        assert is_infra_noise_tags(["cdn"]) is True  # lowercase matched


class TestShouldIncludeRecord:
    """Test record inclusion decision."""

    def test_include_non_noise_record(self) -> None:
        """Non-noise record should be included."""
        record = {"tags": ["eol-product", "database"]}
        assert should_include_record(record) is True

    def test_exclude_cdn_record(self) -> None:
        """CDN record should be excluded."""
        record = {"tags": ["cdn"]}
        assert should_include_record(record) is False

    def test_exclude_cloud_record(self) -> None:
        """Cloud record should be excluded."""
        record = {"tags": ["cloud"]}
        assert should_include_record(record) is False

    def test_exclude_proxy_record(self) -> None:
        """Proxy record should be excluded."""
        record = {"tags": ["proxy"]}
        assert should_include_record(record) is False

    def test_exclude_honeypot_record(self) -> None:
        """Honeypot record should be excluded."""
        record = {"tags": ["honeypot"]}
        assert should_include_record(record) is False

    def test_mixed_tags_exclude_if_any_noise(self) -> None:
        """Mixed tags with any noise should exclude."""
        record = {"tags": ["database", "cdn", "eol-product"]}
        assert should_include_record(record) is False

    def test_no_tags_include(self) -> None:
        """Record with no tags should be included."""
        record = {"tags": []}
        assert should_include_record(record) is True

    def test_none_tags_include(self) -> None:
        """Record with None tags should be included."""
        record = {}
        assert should_include_record(record) is True

    def test_real_world_example_business_web_server(self) -> None:
        """Real business web server (non-noise) should be included."""
        record = {
            "tags": ["eol-product"],
            "port": 80,
            "product": "Apache httpd",
        }
        assert should_include_record(record) is True

    def test_real_world_example_cdn_fronted(self) -> None:
        """CDN-fronted record should be excluded (noise)."""
        record = {
            "tags": ["cdn", "http"],
            "org": "Cloudflare, Inc.",
        }
        assert should_include_record(record) is False
