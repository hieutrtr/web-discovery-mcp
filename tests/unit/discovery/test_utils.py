from __future__ import annotations

import pytest

from legacy_web_mcp.discovery.utils import (
    InvalidTargetURL,
    estimate_complexity,
    generate_description,
    generate_title,
    is_asset_url,
    is_internal_url,
    normalize_url,
)


def test_normalize_url_validates_scheme_and_hostname() -> None:
    normalized = normalize_url("HTTPS://Example.com/path")
    assert normalized.url == "https://example.com/path"
    assert normalized.domain == "example.com"

    with pytest.raises(InvalidTargetURL):
        normalize_url("ftp://example.com")
    with pytest.raises(InvalidTargetURL):
        normalize_url("https:///no-host")


def test_is_internal_and_asset_detection() -> None:
    assert is_internal_url("https://example.com/page", "example.com")
    assert not is_internal_url("https://other.com", "example.com")
    assert is_asset_url("https://example.com/assets/app.css")
    assert not is_asset_url("https://example.com/about")


def test_metadata_heuristics() -> None:
    title = generate_title("https://example.com/path/my-page", "example.com")
    assert title == "My Page"
    description = generate_description("sitemap", 1)
    assert "sitemap" in description
    assert "depth 1" in description
    assert estimate_complexity("https://example.com/a/b/c") == "medium"
    assert estimate_complexity("https://example.com/one") == "low"
