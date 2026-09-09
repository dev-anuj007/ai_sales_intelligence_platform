from pathlib import Path
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # ===== Paths =====
    project_root: Path = Path(__file__).parent.parent.parent
    data_dir: Path = project_root / "data"
    raw_data_path: Path = data_dir / "raw" / "shodan_scan.jsonl.zst"
    fixtures_dir: Path = data_dir / "fixtures"
    db_dir: Path = project_root / "db"
    duckdb_path: Path = db_dir / "sales_intel.duckdb"
    traces_dir: Path = project_root / "traces"
    traces_jsonl_path: Path = traces_dir / "llm_traces.jsonl"
    prompts_dir: Path = project_root / "prompts"

    # ===== LLM Configuration =====
    llm_client: Literal["mock", "anthropic"] = "mock"
    anthropic_api_key: str = ""
    haiku_model: str = "claude-haiku-4-5-20251001"
    sonnet_model: str = "claude-sonnet-5-20251022"

    # ===== Scoring Configuration =====
    score_version: str = "v1"
    weights_version: str = "v1"

    # ===== Enrichment Configuration =====
    default_top_n: int = 50
    max_accounts_per_enrichment: int = 1000

    # ===== Pipeline Configuration =====
    batch_size: int = 5000
    max_records_to_ingest: int | None = None  # None = all records; set limit for dev iteration

    # ===== Logging Configuration =====
    logfire_enabled: bool = True
    log_level: str = "INFO"

    def __post_init__(self) -> None:
        """Ensure required directories exist."""
        self.db_dir.mkdir(parents=True, exist_ok=True)
        self.traces_dir.mkdir(parents=True, exist_ok=True)
        self.fixtures_dir.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings = Settings()
