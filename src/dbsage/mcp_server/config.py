"""Central configuration for dbsage using pydantic-settings."""

import json
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to the optional JSON blacklist file (relative to project root)
_BLACKLIST_JSON = Path(__file__).parents[3] / "config" / "blacklist_tables.json"


class Settings(BaseSettings):
    """All runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DBSAGE_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Database connection
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = ""
    db_user: str = ""
    db_password: SecretStr = SecretStr("")  # never logged, redacted in repr
    db_type: str = "mysql"  # "mysql" or "postgresql"

    # Safety guardrails
    max_query_rows: int = 100
    query_timeout_ms: int = 3000
    slow_query_threshold_ms: int = 2000
    default_sample_limit: int = 10

    # Caching
    cache_ttl_seconds: int = 300

    # Security — merged with config/blacklist_tables.json at startup
    blacklisted_tables: list[str] = []

    # Logging
    dev_mode: bool = False

    @model_validator(mode="after")
    def merge_json_blacklist(self) -> "Settings":
        """Merge tables from config/blacklist_tables.json into blacklisted_tables.

        JSON file entries are combined with DBSAGE_BLACKLISTED_TABLES env var.
        Missing or malformed JSON file is silently ignored.
        """
        if _BLACKLIST_JSON.exists():
            try:
                data = json.loads(_BLACKLIST_JSON.read_text())
                json_tables: list[str] = data.get("blacklisted_tables", [])
                combined = list({*self.blacklisted_tables, *json_tables})
                self.blacklisted_tables = combined
            except (json.JSONDecodeError, KeyError):
                pass  # malformed file — ignore, rely on env var only
        return self


@lru_cache
def get_settings() -> Settings:
    """Return a singleton Settings instance."""
    return Settings()
