"""FastMCP server entrypoint for dbsage.

Kept intentionally small — only wires together the MCP instance,
registers tools by importing tool modules, and configures logging.
"""

from fastmcp import FastMCP

from dbsage.logging_.query_logger import configure_logging
from dbsage.mcp_server.config import get_settings

# The shared FastMCP instance — imported by all tool modules
mcp: FastMCP = FastMCP(name="dbsage")

# Register tools by importing their modules (side-effect: @mcp.tool() decorators run)
import dbsage.tools.discovery_tools  # noqa: F401, E402
import dbsage.tools.query_tools  # noqa: F401, E402
import dbsage.tools.sampling_tools  # noqa: F401, E402
import dbsage.tools.schema_tools  # noqa: F401, E402
import dbsage.tools.semantic_tools  # noqa: F401, E402


def main() -> None:
    """Start the MCP server."""
    settings = get_settings()
    configure_logging(dev_mode=settings.dev_mode)
    mcp.run()


if __name__ == "__main__":
    main()
