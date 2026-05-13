"""Multi-connection engine registry.

Maps named connection profiles to cached AsyncEngine instances.
Engines are created lazily on first use — no pool overhead at startup
for profiles that are never queried.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from dbsage.exceptions import ConnectionPoolError
from dbsage.mcp_server.config import ConnectionProfile, Settings

# Module-level cache: profile name → AsyncEngine
_engines: dict[str, AsyncEngine] = {}


def get_engine_for_profile(
    name: str, profile: ConnectionProfile, password: str
) -> AsyncEngine:
    """Return a cached AsyncEngine for a named profile, creating on first call.

    Args:
        name: The profile name (used as cache key).
        profile: The ConnectionProfile to build the engine from.
        password: The plaintext password (read from env by the caller).
    """
    if name not in _engines:
        _engines[name] = _build_from_profile(profile, password)
    return _engines[name]


def _build_from_profile(profile: ConnectionProfile, password: str) -> AsyncEngine:
    """Build an AsyncEngine from a ConnectionProfile."""
    if profile.db_type == "postgresql":
        url = (
            f"postgresql+asyncpg://{profile.user}:{password}"
            f"@{profile.host}:{profile.port}/{profile.database}"
        )
    elif profile.db_type == "mssql":
        driver = profile.odbc_driver.replace(" ", "+")
        url = (
            f"mssql+aioodbc://{profile.user}:{password}"
            f"@{profile.host}:{profile.port}/{profile.database}"
            f"?driver={driver}&TrustServerCertificate=yes"
        )
    else:
        url = (
            f"mysql+aiomysql://{profile.user}:{password}"
            f"@{profile.host}:{profile.port}/{profile.database}"
        )

    try:
        return create_async_engine(
            url,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=1800,  # required for RDS — avoids stale connections
            echo=False,
        )
    except ModuleNotFoundError as exc:
        if "aioodbc" in str(exc):
            raise ConnectionPoolError(
                "The 'aioodbc' package is required for MSSQL connections. "
                "Install it with: uv sync --extra mssql\n"
                "You also need the Microsoft ODBC Driver installed at the OS level. "
                "On macOS: HOMEBREW_ACCEPT_EULA=Y brew install msodbcsql18"
            ) from exc
        raise


def resolve_connections(names: list[str], settings: Settings) -> list[str]:
    """Expand group names to individual profile names.

    Profiles not found in connections or groups are passed through as-is
    (caller will handle unknown names with an error).

    Preserves order and deduplicates.

    Args:
        names: List of profile names or group names to resolve.
        settings: The current Settings instance.
    """
    resolved: list[str] = []
    seen: set[str] = set()
    for name in names:
        members = settings.connection_groups.get(name, [name])
        for member in members:
            if member not in seen:
                resolved.append(member)
                seen.add(member)
    return resolved


def reset_registry() -> None:
    """Clear the engine cache. Used in tests only."""
    _engines.clear()
