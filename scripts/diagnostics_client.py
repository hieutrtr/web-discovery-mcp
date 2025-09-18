#!/usr/bin/env python3
"""Utility client for manually exercising MCP diagnostics tools."""
from __future__ import annotations

import argparse
import asyncio
import json
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from typing import Any

from fastmcp import Client

DEFAULT_COMMAND: Sequence[str] = ("uv", "run", "legacy-web-mcp")
RESOURCE_URI_TEMPLATE = "/system/status/{scope}"


def _build_config(command: Sequence[str]) -> dict[str, Any]:
    if not command:
        raise ValueError("Command cannot be empty")
    return {
        "mcpServers": {
            "diagnostics": {
                "transport": "stdio",
                "command": command[0],
                "args": list(command[1:]),
            }
        }
    }


def _jsonify(obj: Any) -> Any:
    if hasattr(obj, "model_dump"):
        return _jsonify(obj.model_dump())
    if is_dataclass(obj):
        return _jsonify(asdict(obj))
    if isinstance(obj, dict):
        return {key: _jsonify(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_jsonify(item) for item in obj]
    return obj


async def _call_tool(client: Client, name: str) -> Any:
    return await client.call_tool(name, {})


async def _read_system_status(client: Client, scope: str) -> Any:
    uri = RESOURCE_URI_TEMPLATE.format(scope=scope)
    return await client.read_resource(uri)


async def _list_capabilities(client: Client) -> dict[str, Any]:
    tools = await client.list_tools()
    resources = await client.list_resource_templates()
    return {
        "tools": [tool.name for tool in tools],
        "resources": [_jsonify(template) for template in resources],
    }


async def main() -> None:
    parser = argparse.ArgumentParser(description="Run diagnostics tools via FastMCP client")
    parser.add_argument(
        "action",
        choices=["health", "deps", "llm", "status", "list"],
        help="Which diagnostics interaction to perform",
    )
    parser.add_argument(
        "--command",
        nargs="+",
        default=list(DEFAULT_COMMAND),
        help="Command used to start the MCP server (default: uv run legacy-web-mcp)",
    )
    parser.add_argument(
        "--scope",
        default="global",
        help="Scope parameter for system_status resource (only used with action=status)",
    )
    args = parser.parse_args()

    config = _build_config(args.command)

    async with Client(config) as client:
        if args.action == "health":
            result = await _call_tool(client, "health_check")
        elif args.action == "deps":
            result = await _call_tool(client, "validate_dependencies")
        elif args.action == "llm":
            result = await _call_tool(client, "test_llm_connectivity")
        elif args.action == "status":
            result = await _read_system_status(client, args.scope)
        else:  # list
            result = await _list_capabilities(client)

    print(json.dumps(_jsonify(result), indent=2, sort_keys=True))


if __name__ == "__main__":
    asyncio.run(main())
