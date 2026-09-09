from pydantic import BaseModel, Field


class DatabasePortsConfig(BaseModel):
    postgres: int = 5432
    mysql: int = 3306
    mysql_x: int = 33060
    sqlserver: int = 1433
    mongodb: int = 27017
    redis: int = 6379
    elasticsearch: int = 9200
    couchdb: int = 5984
    cassandra: int = 9042
    influxdb: int = 8086
    clickhouse: int = 8123
    neo4j: int = 7474

    def as_set(self) -> frozenset[int]:
        return frozenset([
            self.postgres, self.mysql, self.mysql_x, self.sqlserver,
            self.mongodb, self.redis, self.elasticsearch, self.couchdb,
            self.cassandra, self.influxdb, self.clickhouse, self.neo4j,
        ])


class LegacyProtocolPortsConfig(BaseModel):
    ftp: int = 21
    telnet: int = 23
    rdp: int = 3389
    vnc: int = 5900
    smb: int = 445
    netbios: int = 139

    def as_set(self) -> frozenset[int]:
        return frozenset([self.ftp, self.telnet, self.rdp, self.vnc, self.smb, self.netbios])


class WeakTLSVersionsConfig(BaseModel):
    versions: list[str] = Field(default_factory=lambda: ["SSLv2", "SSLv3", "TLSv1.0", "TLSv1.1"])

    def as_set(self) -> frozenset[str]:
        return frozenset(self.versions)


class DatabaseServiceTypesConfig(BaseModel):
    service_types: list[str] = Field(default_factory=lambda: [
        "mongodb", "redis", "mysql", "mysqlx", "mssql_ssrp"
    ])

    def as_set(self) -> frozenset[str]:
        return frozenset(self.service_types)


class LegacyProtocolTypesConfig(BaseModel):
    service_types: list[str] = Field(default_factory=lambda: [
        "ftp", "telnet", "rdp_encryption", "vnc"
    ])

    def as_set(self) -> frozenset[str]:
        return frozenset(self.service_types)


class IoTOTDeviceTypesConfig(BaseModel):
    device_types: list[str] = Field(default_factory=lambda: [
        "hikvision", "dahua", "dahua_dvr_web", "draytek_vigor",
        "mikrotik_routeros", "mikrotik_winbox", "hp_ilo", "ipmi",
        "qnap", "synology_dsm",
    ])

    def as_set(self) -> frozenset[str]:
        return frozenset(self.device_types)


class InfrastructureNoiseTagsConfig(BaseModel):
    tags: list[str] = Field(default_factory=lambda: ["cdn", "cloud", "proxy", "vpn", "honeypot", "tor"])

    def as_set(self) -> frozenset[str]:
        return frozenset(self.tags)


class CVECriticalityThresholds(BaseModel):
    critical_cvss_min: float = 9.0
    high_cvss_min: float = 7.0
    high_epss_min: float = 0.5


class PipelineConfig(BaseModel):
    database_ports: DatabasePortsConfig = Field(default_factory=DatabasePortsConfig)
    legacy_protocol_ports: LegacyProtocolPortsConfig = Field(default_factory=LegacyProtocolPortsConfig)
    weak_tls_versions: WeakTLSVersionsConfig = Field(default_factory=WeakTLSVersionsConfig)
    database_service_types: DatabaseServiceTypesConfig = Field(default_factory=DatabaseServiceTypesConfig)
    legacy_protocol_types: LegacyProtocolTypesConfig = Field(default_factory=LegacyProtocolTypesConfig)
    iot_ot_device_types: IoTOTDeviceTypesConfig = Field(default_factory=IoTOTDeviceTypesConfig)
    infra_noise_tags: InfrastructureNoiseTagsConfig = Field(default_factory=InfrastructureNoiseTagsConfig)
    cve_thresholds: CVECriticalityThresholds = Field(default_factory=CVECriticalityThresholds)

    banner_text_max_length: int = 2048
    top_records_per_account: int = 20
    batch_size: int = 5000


_pipeline_config = PipelineConfig()


def get_pipeline_config() -> PipelineConfig:
    return _pipeline_config
