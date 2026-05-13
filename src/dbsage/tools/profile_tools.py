"""Profile management tools — add and remove named connection profiles.

Changes are written to config/connections.json and take effect immediately
(settings cache is invalidated after each write).
"""

import json
from pathlib import Path
from typing import Any, cast

from dbsage.db.connection_registry import reset_registry
from dbsage.formatting.table_formatter import section_header
from dbsage.mcp_server.config import get_settings
from dbsage.mcp_server.server import mcp

_CONNECTIONS_JSON = Path(__file__).parents[3] / "config" / "connections.json"

_VALID_DB_TYPES = frozenset({"mysql", "postgresql"})


def _read_connections_file() -> dict[str, Any] | None:
    """Read and parse connections.json. Returns None if file is missing."""
    if not _CONNECTIONS_JSON.exists():
        return None
    try:
        return cast(dict[str, Any], json.loads(_CONNECTIONS_JSON.read_text()))
    except json.JSONDecodeError:
        return {}  # sentinel: file exists but is malformed


def _write_connections_file(data: dict[str, Any]) -> None:
    _CONNECTIONS_JSON.parent.mkdir(parents=True, exist_ok=True)
    _CONNECTIONS_JSON.write_text(json.dumps(data, indent=2) + "\n")


@mcp.tool()
async def add_connection(
    name: str,
    host: str,
    database: str,
    user: str,
    port: int = 3306,
    db_type: str = "mysql",
    password: str = "",
    password_env: str = "",
    description: str = "",
    requires_confirmation: bool = False,
    max_query_rows: int | None = None,
    query_timeout_ms: int | None = None,
) -> str:
    """Add a new named connection profile to config/connections.json.

    The profile is available immediately — no server restart required.
    Use remove_connection() to delete a profile.
    Use list_connections() to verify the result.

    Args:
        name: Unique profile key (used as connection='<name>' in all tools).
        host: Database hostname or IP.
        database: Database/schema name.
        user: Database username (must have SELECT-only privileges).
        port: Database port (default 3306 for MySQL, 5432 for PostgreSQL).
        db_type: "mysql" or "postgresql".
        password: Inline password — convenient for local/dev, avoid in prod.
        password_env: Name of the environment variable holding the password.
        description: Human-readable label shown in list_connections().
        requires_confirmation: Set True for sensitive connections (e.g. prod).
        max_query_rows: Per-profile row limit override (default: global setting).
        query_timeout_ms: Per-profile query timeout override in ms.
    """
    header = section_header("add_connection", name)

    # Input validation
    if not name.strip():
        return f"{header}\n\n  error: name must not be empty"
    if db_type not in _VALID_DB_TYPES:
        return (
            f"{header}\n\n  error: db_type must be 'mysql' or 'postgresql', "
            f"got '{db_type}'"
        )
    if not (1 <= port <= 65535):
        return f"{header}\n\n  error: port must be between 1 and 65535, got {port}"

    raw = _read_connections_file()

    if raw == {}:  # file exists but is malformed
        return (
            f"{header}\n\n"
            "  error: config/connections.json exists but contains invalid JSON.\n"
            "  Fix or delete the file before adding a new profile."
        )

    if raw is None:
        raw = {"connections": {}}

    connections: dict[str, Any] = raw.setdefault("connections", {})

    if name in connections:
        return (
            f"{header}\n\n"
            f"  error: profile '{name}' already exists.\n"
            "  Use remove_connection() first if you want to replace it."
        )

    # Build profile dict — omit falsy optional fields to keep JSON minimal
    profile: dict[str, Any] = {
        "host": host,
        "port": port,
        "database": database,
        "user": user,
        "db_type": db_type,
    }
    if password:
        profile["password"] = password
    if password_env:
        profile["password_env"] = password_env
    if description:
        profile["description"] = description
    if requires_confirmation:
        profile["requires_confirmation"] = True
    if max_query_rows is not None:
        profile["max_query_rows"] = max_query_rows
    if query_timeout_ms is not None:
        profile["query_timeout_ms"] = query_timeout_ms

    connections[name] = profile
    _write_connections_file(raw)

    # Invalidate the settings singleton so the next tool call reloads from disk
    get_settings.cache_clear()

    lines = [
        f"  profile '{name}' added.",
        f"  host:     {host}:{port}",
        f"  database: {database}",
        f"  db_type:  {db_type}",
        f"  user:     {user}",
    ]
    if password_env:
        lines.append(f"  password: via env var ${password_env}")
    elif password:
        lines.append("  password: inline (consider using password_env in prod)")
    else:
        lines.append("  password: not set — set password or password_env before use")
    if requires_confirmation:
        lines.append("  sensitive: YES")

    return f"{header}\n\n" + "\n".join(lines)


@mcp.tool()
async def remove_connection(name: str) -> str:
    """Remove a named connection profile from config/connections.json.

    Also clears the profile from the default connection and any groups it belongs to.
    The change takes effect immediately — no server restart required.

    Args:
        name: The profile key to remove (as shown in list_connections()).
    """
    header = section_header("remove_connection", name)

    raw = _read_connections_file()

    if raw is None:
        return f"{header}\n\n  error: config/connections.json not found"

    if raw == {}:
        return (
            f"{header}\n\n"
            "  error: config/connections.json exists but contains invalid JSON"
        )

    connections: dict[str, Any] = raw.get("connections", {})
    if name not in connections:
        available = ", ".join(connections.keys()) if connections else "(none)"
        return (
            f"{header}\n\n"
            f"  error: profile '{name}' not found.\n"
            f"  available profiles: {available}"
        )

    del connections[name]
    notes: list[str] = []

    # Clear default if it pointed to this profile
    if raw.get("default") == name:
        raw["default"] = ""
        notes.append("cleared default (was pointing to this profile)")

    # Remove from groups; drop any group that becomes empty
    groups: dict[str, Any] = raw.get("groups", {})
    emptied: list[str] = []
    for group_name, members in list(groups.items()):
        if name in members:
            members.remove(name)
            if not members:
                emptied.append(group_name)
    for g in emptied:
        del groups[g]
        notes.append(f"removed empty group '{g}'")

    _write_connections_file(raw)

    # Invalidate settings cache and evict all cached engines
    get_settings.cache_clear()
    reset_registry()

    lines = [f"  profile '{name}' removed."]
    for note in notes:
        lines.append(f"  note: {note}")

    return f"{header}\n\n" + "\n".join(lines)
