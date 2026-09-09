from __future__ import annotations

from pydantic import BaseModel, Field


class DatabaseExposure(BaseModel):
    is_exposed: bool = False
    port: int | None = None
    service_type: str | None = None

    class Config:
        frozen = True


class LegacyProtocolExposure(BaseModel):
    is_exposed: bool = False
    port: int | None = None
    protocol_type: str | None = None

    class Config:
        frozen = True


class IoTOTExposure(BaseModel):
    is_exposed: bool = False
    device_type: str | None = None

    class Config:
        frozen = True


class VulnerabilityData(BaseModel):
    has_vulns: bool = False
    count: int = 0
    max_cvss: float | None = None
    max_epss: float | None = None
    cve_ids: list[str] = Field(default_factory=list)
    count_critical: int = 0

    class Config:
        frozen = True


class TLSSecurityData(BaseModel):
    has_ssl: bool = False
    is_self_signed: bool = False
    has_weak_version: bool = False
    jarm_fingerprint: str | None = None

    class Config:
        frozen = True


class HTTPWebData(BaseModel):
    title: str | None = None
    server: str | None = None
    status_code: int | None = None
    has_securitytxt: bool = False

    class Config:
        frozen = True


class SoftwareMaturityData(BaseModel):
    is_eol: bool = False
    is_honeypot: bool = False

    class Config:
        frozen = True


class ExtractedFeatures(BaseModel):
    database: DatabaseExposure
    legacy_protocol: LegacyProtocolExposure
    iot_ot: IoTOTExposure
    vulnerabilities: VulnerabilityData
    tls: TLSSecurityData
    http: HTTPWebData
    software_maturity: SoftwareMaturityData

    class Config:
        frozen = True

    def to_db_dict(self) -> dict[str, object]:
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
            "is_eol_product": self.software_maturity.is_eol,
            "is_honeypot": self.software_maturity.is_honeypot,
        }
