"""Connection management tools — list and health-check named connection profiles."""

import time

from dbsage.db.connection_registry import resolve_connections
from dbsage.db.query_executor import execute_query
from dbsage.formatting.table_formatter import section_header
from dbsage.mcp_server.dependencies import get_app_settings, get_engine_for
from dbsage.mcp_server.server import mcp


@mcp.tool()
async def list_connections() -> str:
    """List all configured database connection profiles.

    Shows name, description, host, database, db_type, and whether the connection
    is marked sensitive. Passwords are never shown.

    Use connection='<name>' on any tool to target a specific database.
    Call ping_connections() to verify connectivity before running queries.
    """
    settings = get_app_settings()
    header = section_header("list_connections")

    if not settings.connections:
        return (
            f"{header}\n\n"
            "  (no named connection profiles configured)\n\n"
            "  To add connections, populate config/connections.json.\n"
            "  See .env.example for password env var conventions."
        )

    # Build table rows
    col_name = max(len(n) for n in settings.connections) + 2
    col_name = max(col_name, 8)

    lines: list[str] = []
    header_row = (
        f"  {'name':<{col_name}} {'db_type':<10} {'host':<35} {'database':<20} "
        f"{'description':<25} sensitive?"
    )
    sep = "  " + "-" * (len(header_row) - 2)
    lines.append(header_row)
    lines.append(sep)

    for name, profile in settings.connections.items():
        sensitive = "YES" if profile.requires_confirmation else "no"
        default_marker = " (default)" if name == settings.default_connection else ""
        lines.append(
            f"  {name + default_marker:<{col_name}} {profile.db_type:<10} "
            f"{profile.host:<35} {profile.database:<20} "
            f"{profile.description:<25} {sensitive}"
        )

    count = len(settings.connections)
    profile_word = "profile" if count == 1 else "profiles"
    lines.append("")
    lines.append(f"  {count} {profile_word}")

    if settings.connection_groups:
        lines.append("")
        lines.append("  Groups:")
        for group_name, members in settings.connection_groups.items():
            lines.append(f"    {group_name}: {', '.join(members)}")

    body = "\n".join(lines)
    return f"{header}\n\n{body}"


@mcp.tool()
async def ping_connections(connections: list[str] | None = None) -> str:
    """Check connectivity and latency for named connection profiles.

    Runs SELECT 1 against each connection to verify reachability.
    If connections is omitted, pings all configured profiles.

    Args:
        connections: Optional list of profile names or group names to check.
                     Defaults to all configured profiles.
    """
    import asyncio

    settings = get_app_settings()
    header = section_header("ping_connections")

    if not settings.connections:
        return (
            f"{header}\n\n  (no named connection profiles configured — nothing to ping)"
        )

    # Resolve which profiles to ping
    if connections:
        targets = resolve_connections(connections, settings)
    else:
        targets = list(settings.connections.keys())

    if not targets:
        return f"{header}\n\n  (no connections to ping)"

    timeout_ms = settings.query_timeout_ms

    async def _ping(name: str) -> tuple[str, float | None, str]:
        """Returns (name, elapsed_ms or None, error_message)."""
        if name not in settings.connections:
            return name, None, "unknown profile"
        try:
            engine = get_engine_for(name)
            start = time.monotonic()
            await execute_query("SELECT 1", engine, timeout_ms=timeout_ms)
            elapsed = (time.monotonic() - start) * 1000
            return name, elapsed, ""
        except Exception as exc:  # noqa: BLE001
            return name, None, str(exc)

    # Run all pings concurrently
    results: list[tuple[str, float | None, str]] = []
    async with asyncio.TaskGroup() as tg:
        tasks = [tg.create_task(_ping(name)) for name in targets]
    results = [t.result() for t in tasks]

    col_name = max(len(r[0]) for r in results) + 2
    col_name = max(col_name, 8)

    lines: list[str] = []
    for name, elapsed, error in results:
        if elapsed is not None:
            lines.append(f"  {name:<{col_name}} OK      {elapsed:.0f}ms")
        else:
            lines.append(f"  {name:<{col_name}} FAILED  {error}")

    body = "\n".join(lines)
    return f"{header}\n\n{body}"
