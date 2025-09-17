"""Legacy Web Application Analysis MCP Server package."""

from importlib import metadata

__all__ = ["__version__"]


def __getattr__(name: str) -> str:
    if name == "__version__":
        try:
            return metadata.version("legacy-web-mcp")
        except metadata.PackageNotFoundError:  # pragma: no cover - during local development
            return "0.0.0"
    raise AttributeError(name)
