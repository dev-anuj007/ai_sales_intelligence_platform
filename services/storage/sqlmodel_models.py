from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from sqlalchemy import JSON, TIMESTAMP, VARCHAR, BigInteger, Boolean, Column, Float, Integer
from sqlmodel import Field, SQLModel


class StagingRecordSQL(SQLModel, table=True):
    """SQLModel ORM version of raw Shodan scan record."""

    __tablename__ = "staging_records"

    record_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    ip: Optional[str] = None
    port: Optional[int] = None
    transport: Optional[str] = None
    root_domain: Optional[str] = None
    hostnames: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    domains: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    org: Optional[str] = None
    isp: Optional[str] = None
    asn: Optional[str] = None
    country_code: Optional[str] = None
    region: Optional[str] = None
    city: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    ts: Optional[datetime] = Field(None, sa_column=Column(TIMESTAMP))
    product: Optional[str] = None
    version: Optional[str] = None
    os: Optional[str] = None
    device: Optional[str] = None
    devicetype: Optional[str] = None
    cpe: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    is_infra_noise: bool = False
    has_vulns: bool = False
    vuln_count: int = 0
    max_cvss: Optional[float] = None
    max_epss: Optional[float] = None
    vuln_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    has_ssl: bool = False
    ssl_self_signed: bool = False
    ssl_version_weak: bool = False
    ssl_jarm: Optional[str] = None
    http_title: Optional[str] = None
    http_server: Optional[str] = None
    http_status: Optional[int] = None
    has_securitytxt: bool = False
    is_database_port: bool = False
    is_legacy_protocol: bool = False
    is_iot_ot_device: bool = False
    is_eol_product: bool = False
    is_honeypot: bool = False
    data_snippet: Optional[str] = None
    shodan_module: Optional[str] = None
    ingested_at: datetime = Field(default_factory=datetime.utcnow, sa_column=Column(TIMESTAMP))


class AccountSQL(SQLModel, table=True):
    """SQLModel ORM version of aggregated domain account."""

    __tablename__ = "accounts"

    root_domain: str = Field(primary_key=True)
    record_count: int
    asset_count: int
    distinct_ips: int
    distinct_ports: int
    port_list: list[int] = Field(default_factory=list, sa_column=Column(JSON))
    countries: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    primary_country_code: Optional[str] = None
    primary_org: Optional[str] = None
    cloud_or_cdn_fronted: bool = False
    vuln_count_total: int = 0
    vuln_count_critical: int = 0
    max_cvss: Optional[float] = None
    max_epss: Optional[float] = None
    top_cve_ids: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    exposed_database_count: int = 0
    legacy_protocol_count: int = 0
    weak_tls_count: int = 0
    self_signed_cert_count: int = 0
    eol_product_count: int = 0
    iot_ot_device_count: int = 0
    honeypot_flagged: bool = False
    excluded_as_honeypot: bool = Field(default=False)
    sample_http_titles: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    sample_products: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    first_seen: Optional[datetime] = Field(None, sa_column=Column(TIMESTAMP))
    last_seen: Optional[datetime] = Field(None, sa_column=Column(TIMESTAMP))
    snapshot_date: Optional[str] = None
    risk_score: Optional[float] = None
    score_version: Optional[str] = None
    signal_tags: list[str] = Field(default_factory=list, sa_column=Column(JSON))
    score_explanation: Optional[str] = None
    scored_at: Optional[datetime] = Field(None, sa_column=Column(TIMESTAMP))
    inferred_company_name: Optional[str] = None
    inferred_industry: Optional[str] = None
    narrative: Optional[str] = None
    outreach_draft: Optional[str] = None
    enriched_at: Optional[datetime] = Field(None, sa_column=Column(TIMESTAMP))


class TraceRecordSQL(SQLModel, table=True):
    """SQLModel ORM version of LLM call trace."""

    __tablename__ = "trace_logs"

    trace_id: str = Field(primary_key=True)
    timestamp: datetime = Field(sa_column=Column(TIMESTAMP))
    task: str
    root_domain: Optional[str] = None
    model: str
    prompt_name: str
    prompt_version: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float
    decision: Optional[dict[str, Any]] = Field(None, sa_column=Column(JSON))
    success: bool = True
    error: Optional[str] = None
    request_hash: Optional[str] = None
    llm_client_type: str


class AccountTopRecordSQL(SQLModel, table=True):
    """SQLModel ORM version of top N records per account."""

    __tablename__ = "account_top_records"

    root_domain: str = Field(primary_key=True)
    record_id: int = Field(sa_column=Column(BigInteger, primary_key=True))
    rank: int
