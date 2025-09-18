from __future__ import annotations

from pathlib import Path

from legacy_web_mcp.config.loader import load_configuration


def test_load_configuration_with_file_override(tmp_path: Path) -> None:
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """
BROWSER_ENGINE: firefox
MAX_CONCURRENT_PAGES: 7
        """
    )

    settings = load_configuration(config_path=config_file)
    assert settings.BROWSER_ENGINE == "firefox"
    assert settings.MAX_CONCURRENT_PAGES == 7


def test_load_configuration_defaults(tmp_path: Path) -> None:
    settings = load_configuration()
    assert settings.BROWSER_ENGINE == "chromium"
    assert settings.MAX_CONCURRENT_PAGES == 3
