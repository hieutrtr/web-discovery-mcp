from __future__ import annotations

import tomllib
from collections.abc import Iterator
from importlib import metadata
from pathlib import Path
from typing import Any

import pytest
import yaml  # type: ignore[import-untyped]

ROOT = Path(__file__).resolve().parents[2]


def test_package_version() -> None:
    import legacy_web_mcp

    expected = metadata.version("legacy-web-mcp")
    assert legacy_web_mcp.__version__ == expected


def test_source_tree_structure() -> None:
    src_root = ROOT / "src" / "legacy_web_mcp"
    expected_dirs = {
        "config",
        "llm",
        "browser",
        "progress",
        "documentation",
        "storage",
        "mcp",
        "shared",
    }

    missing = {name for name in expected_dirs if not (src_root / name).is_dir()}
    assert not missing, f"Missing expected module directories: {sorted(missing)}"


def test_cli_invokes_server_run(monkeypatch: pytest.MonkeyPatch) -> None:
    from legacy_web_mcp import cli

    called = False

    def fake_run() -> None:
        nonlocal called
        called = True

    monkeypatch.setattr("legacy_web_mcp.mcp.server.run", fake_run)
    monkeypatch.setattr("legacy_web_mcp.cli.run", fake_run)
    cli.main()
    assert called


def test_pyproject_tooling_configuration() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())

    tools = pyproject.get("tool", {})
    assert "ruff" in tools, "Ruff configuration missing from pyproject.toml"
    assert "mypy" in tools, "Mypy configuration missing from pyproject.toml"
    pytest_cfg = tools.get("pytest", {}).get("ini_options")
    assert pytest_cfg is not None, "Pytest configuration missing under [tool.pytest.ini_options]"

    dev_deps = pyproject.get("project", {}).get("optional-dependencies", {}).get("dev", [])
    required = {"ruff==0.13.0", "mypy==1.18.1", "pytest==8.4.2"}
    assert required.issubset(set(dev_deps)), "Required dev dependencies not present"


def test_gitignore_covers_python_artifacts() -> None:
    patterns = {
        "__pycache__/",
        "*.py[cod]",
        "*.egg-info/",
        "playwright-report/",
    }
    gitignore = (ROOT / ".gitignore").read_text().splitlines()
    missing = patterns.difference(gitignore)
    assert not missing, f"Missing gitignore patterns: {sorted(missing)}"


def _read_env_template() -> dict[str, str]:
    env_path = ROOT / ".env.template"
    pairs: dict[str, str] = {}
    for line in env_path.read_text().splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        key, _, value = stripped.partition("=")
        pairs[key] = value
    return pairs


def test_env_template_keys_present() -> None:
    env_keys = _read_env_template()
    required = {
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "STEP1_MODEL",
        "STEP2_MODEL",
        "FALLBACK_MODEL",
        "PLAYWRIGHT_HEADLESS",
        "MAX_CONCURRENT_PAGES",
        "OUTPUT_ROOT",
    }
    missing = required.difference(env_keys)
    assert not missing, f"Missing keys in .env.template: {sorted(missing)}"


def test_ci_workflow_runs_tooling() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"
    workflow = yaml.safe_load(workflow_path.read_text())
    steps: Iterator[dict[str, Any]] = iter(workflow["jobs"]["lint-test"]["steps"])

    commands: dict[str, str] = {}
    for step in steps:
        name = step.get("name")
        if name and "run" in step:
            commands[name] = step["run"]

    assert commands.get("Ruff lint") == "uv run ruff check"
    assert commands.get("Ruff format check") == "uv run ruff format --check"
    assert commands.get("Mypy type check") == "uv run mypy src tests"
    assert commands.get("Pytest") == "uv run pytest"


def test_readme_documents_setup_sections() -> None:
    readme = (ROOT / "README.md").read_text()
    required_headers = [
        "Getting Started",
        "Installation",
        "Running the Server",
        "Development Tooling",
        "Configuration",
        "Continuous Integration",
    ]
    for header in required_headers:
        assert f"## {header}" in readme, f"README missing section: {header}"
