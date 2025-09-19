"""Storage utilities for Legacy Web MCP."""

from legacy_web_mcp.storage.projects import (
    ProjectMetadata,
    ProjectPaths,
    ProjectRecord,
    ProjectStore,
    create_project_store,
)

__all__ = [
    "ProjectMetadata",
    "ProjectPaths",
    "ProjectRecord",
    "ProjectStore",
    "create_project_store",
]
