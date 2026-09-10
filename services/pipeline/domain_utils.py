from __future__ import annotations

from typing import Any

import tldextract


class DomainExtractor:
    def __init__(self) -> None:
        self._extractor = tldextract.TLDExtract(suffix_list_urls=(), cache_dir=None)

    def extract(self, record: dict[str, Any]) -> str | None:
        candidates = record.get("domains") or []
        if not candidates:
            hostnames = record.get("hostnames") or []
            if hostnames:
                candidates = [hostnames[0]]

        if not candidates:
            return None

        return self._extract_root_domain(candidates[0])

    def _extract_root_domain(self, domain_str: str) -> str | None:
        try:
            result = self._extractor(domain_str)
            if result.domain and result.suffix:
                return f"{result.domain}.{result.suffix}"

            return None

        except Exception:
            return None

    def is_ip_only(self, record: dict[str, Any]) -> bool:
        domains = record.get("domains") or []
        hostnames = record.get("hostnames") or []
        return len(domains) == 0 and len(hostnames) == 0


_default_extractor = DomainExtractor()


def get_root_domain(record: dict[str, Any]) -> str | None:
    return _default_extractor.extract(record)


def is_ip_only(record: dict[str, Any]) -> bool:
    return _default_extractor.is_ip_only(record)
