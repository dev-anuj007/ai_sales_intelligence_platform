from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class StagingRecord(BaseModel):
    """Raw Shodan scan record after normalization, before aggregation."""

    record_id: int
    ip: str
    port: int
    transport: str | None = None
    root_domain: str | None = None
    hostnames: list[str] = Field(default_factory=list)
    domains: list[str] = Field(default_factory=list)
    org: str | None = None
    isp: str | None = None
    asn: str | None = None
    country_code: str | None = None
    region: str | None = None
    city: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    ts: datetime | None = None
    product: str | None = None
    version: str | None = None
    os: str | None = None
    device: str | None = None
    devicetype: str | None = None
    cpe: list[str] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    is_infra_noise: bool = False
    has_vulns: bool = False
    vuln_count: int = 0
    max_cvss: float | None = None
    max_epss: float | None = None
    vuln_ids: list[str] = Field(default_factory=list)
    has_ssl: bool = False
    ssl_self_signed: bool = False
    ssl_version_weak: bool = False
    ssl_jarm: str | None = None
    http_title: str | None = None
    http_server: str | None = None
    http_status: int | None = None
    has_securitytxt: bool = False
    is_database_port: bool = False
    is_legacy_protocol: bool = False
    is_iot_ot_device: bool = False
    is_eol_product: bool = False
    is_honeypot: bool = False
    data_snippet: str | None = None
    shodan_module: str | None = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        """Pydantic config for ORM mode compatibility."""

        from_attributes = True


class Account(BaseModel):
    """Aggregated domain account with computed signals and scores."""

    root_domain: str
    record_count: int
    asset_count: int
    distinct_ips: int
    distinct_ports: int
    port_list: list[int] = Field(default_factory=list)
    countries: list[str] = Field(default_factory=list)
    primary_country_code: str | None = None
    primary_org: str | None = None
    cloud_or_cdn_fronted: bool = False
    vuln_count_total: int = 0
    vuln_count_critical: int = 0
    max_cvss: float | None = None
    max_epss: float | None = None
    top_cve_ids: list[str] = Field(default_factory=list)
    exposed_database_count: int = 0
    legacy_protocol_count: int = 0
    weak_tls_count: int = 0
    self_signed_cert_count: int = 0
    eol_product_count: int = 0
    iot_ot_device_count: int = 0
    honeypot_flagged: bool = False
    excluded_as_honeypot: bool = False
    sample_http_titles: list[str] = Field(default_factory=list)
    sample_products: list[str] = Field(default_factory=list)
    first_seen: datetime | None = None
    last_seen: datetime | None = None
    snapshot_date: str | None = None
    risk_score: float | None = None
    score_version: str | None = None
    signal_tags: list[str] = Field(default_factory=list)
    score_explanation: str | None = None  # JSON string
    scored_at: datetime | None = None
    inferred_company_name: str | None = None
    inferred_industry: str | None = None
    narrative: str | None = None
    outreach_draft: str | None = None
    enriched_at: datetime | None = None

    class Config:
        """Pydantic config for ORM mode compatibility."""

        from_attributes = True


class TraceRecord(BaseModel):
    """LLM call trace for observability and cost tracking."""

    trace_id: str
    timestamp: datetime
    task: str
    root_domain: str | None = None
    model: str
    prompt_name: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    decision: dict[str, Any] | None = None
    success: bool = True
    error: str | None = None
    request_hash: str | None = None
    llm_client_type: str

    class Config:
        """Pydantic config for ORM mode compatibility."""

        from_attributes = True


class AccountTopRecord(BaseModel):
    """Top N most-interesting records per account (for LLM grounding)."""

    root_domain: str
    record_id: int
    rank: int

    class Config:
        """Pydantic config for ORM mode compatibility."""

        from_attributes = True
