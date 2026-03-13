"""Central configuration for dbsage using pydantic-settings."""

import json
import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Path to the optional JSON config files (relative to project root)
_BLACKLIST_JSON = Path(__file__).parents[3] / "config" / "blacklist_tables.json"
_CONNECTIONS_JSON = Path(__file__).parents[3] / "config" / "connections.json"


class ConnectionProfile(BaseModel):
    """Configuration for a single named database connection profile."""

    host: str
    port: int = 3306
    database: str
    user: str
    # Password resolution: inline `password` first, then env var via `password_env`.
    # Use `password_env` to keep secrets out of the file (recommended for prod).
    # Use `password` for convenience in local/dev setups.
    password: str = ""
    password_env: str = ""  # env var name — user defines this
    db_type: str = "mysql"  # "mysql" or "postgresql"
    description: str = ""
    requires_confirmation: bool = False  # True for sensitive connections (e.g. prod)
    max_query_rows: int | None = None  # overrides global setting when set
    query_timeout_ms: int | None = None  # overrides global setting when set


class Settings(BaseSettings):
    """All runtime configuration loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="DBSAGE_",
        env_nested_delimiter="__",
        case_sensitive=False,
    )

    # Database connection (legacy single-DB fields — used when connections is empty)
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = ""
    db_user: str = ""
    db_password: SecretStr = SecretStr("")  # never logged, redacted in repr
    db_type: str = "mysql"  # "mysql" or "postgresql"

    # Safety guardrails
    max_query_rows: int = 100  # default LIMIT injected when query has none
    max_query_rows_hard_cap: int = 500  # ceiling when LLM requests a specific limit
    query_timeout_ms: int = 3000
    slow_query_threshold_ms: int = 2000
    default_sample_limit: int = 10

    # Caching
    cache_ttl_seconds: int = 300

    # Security — merged with config/blacklist_tables.json at startup
    blacklisted_tables: list[str] = []

    # Logging
    dev_mode: bool = False

    # Multi-connection — loaded from config/connections.json
    connections: dict[str, ConnectionProfile] = {}
    connection_groups: dict[str, list[str]] = {}
    default_connection: str = ""

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

    @model_validator(mode="after")
    def load_connections_json(self) -> "Settings":
        """Load named connection profiles from config/connections.json.

        Reads host, port, database, user, db_type, description, and guardrail
        overrides per profile. Passwords can be supplied inline via `password`
        (convenient for dev) or via `password_env` pointing to an env var
        (recommended for prod). Both fields are optional.

        Missing or malformed JSON file is silently ignored (backwards compat).
        """
        if not _CONNECTIONS_JSON.exists():
            return self
        try:
            data = json.loads(_CONNECTIONS_JSON.read_text())
        except json.JSONDecodeError:
            return self  # malformed — ignore

        raw_connections: dict[str, object] = data.get("connections", {})
        parsed: dict[str, ConnectionProfile] = {}
        for name, profile_data in raw_connections.items():
            if not isinstance(profile_data, dict):
                continue
            try:
                # Resolve password from env at load time so it is available
                # immediately but still read from env (not stored in JSON).
                parsed[name] = ConnectionProfile(**profile_data)
            except Exception:  # noqa: BLE001, S110
                pass  # malformed profile — skip silently

        if parsed:
            self.connections = parsed

        raw_groups: dict[str, object] = data.get("groups", {})
        groups: dict[str, list[str]] = {}
        for group_name, members in raw_groups.items():
            if isinstance(members, list):
                groups[group_name] = [str(m) for m in members]
        if groups:
            self.connection_groups = groups

        default: object = data.get("default", "")
        if isinstance(default, str) and default:
            self.default_connection = default

        return self

    def get_password_for(self, profile: ConnectionProfile) -> str:
        """Return the password for a connection profile.

        Resolution order:
        1. Inline `password` field in the profile (convenient for dev/local).
        2. Environment variable named by `password_env` (recommended for prod).
        3. Empty string if neither is set.
        """
        if profile.password:
            return profile.password
        if profile.password_env:
            return os.environ.get(profile.password_env, "")
        return ""


@lru_cache
def get_settings() -> Settings:
    """Return a singleton Settings instance."""
    return Settings()
