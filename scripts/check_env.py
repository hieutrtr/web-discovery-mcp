#!/usr/bin/env python3
"""CLI utility to ensure required environment variables are present."""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from legacy_web_mcp.config.env_check import (
    check_required_env,
    default_required_keys,
    format_report,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that environment variables needed for the MCP server are available. "
            "You can supply a custom subset via --keys or rely on the default required set."
        )
    )
    parser.add_argument(
        "--keys",
        nargs="*",
        help="Optional list of environment variable names to validate (defaults to required set).",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress success output (warnings still print when keys are missing).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    required_keys = tuple(args.keys) if args.keys else default_required_keys()
    ok, issues = check_required_env(required_keys)

    if ok:
        if not args.quiet:
            print("All required environment variables are configured.")
        return 0

    for line in format_report(issues):
        print(line, file=sys.stderr)
    return 1


if __name__ == "__main__":  # pragma: no cover - exercised via CLI
    raise SystemExit(main())
