"""MCP tooling for website discovery."""
from __future__ import annotations

from fastmcp import Context, FastMCP

from legacy_web_mcp.config.loader import load_configuration
from legacy_web_mcp.discovery.pipeline import InvalidTargetURL, WebsiteDiscoveryService
from legacy_web_mcp.storage import create_project_store


def register(mcp: FastMCP) -> None:
    """Register discovery tool with the MCP instance."""

    @mcp.tool(
        name="discover_website",
        description="Discover site structure via sitemap/crawl tooling."
    )
    async def discover_website(context: Context, url: str) -> dict[str, object]:
        settings = load_configuration()
        project_store = create_project_store(settings)
        service = WebsiteDiscoveryService(settings, project_store=project_store)
        try:
            return await service.discover(context, url)
        except InvalidTargetURL as exc:
            message = str(exc)
            await context.error(message)
            raise ValueError(message) from exc


__all__ = ["register"]
