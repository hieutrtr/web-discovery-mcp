"""Data models for discovery pipeline outputs."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class DiscoveredURL:
    """Represents an individual URL detected during discovery."""

    url: str
    source: str
    depth: int
    internal: bool
    asset: bool
    title: str | None
    description: str | None
    complexity: str

    def category(self) -> str:
        if self.asset:
            return "asset"
        if self.internal:
            return "internal_page"
        return "external_page"

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "source": self.source,
            "depth": self.depth,
            "category": self.category(),
            "internal": self.internal,
            "asset": self.asset,
            "title": self.title,
            "description": self.description,
            "complexity": self.complexity,
        }


@dataclass(frozen=True, slots=True)
class DiscoverySummary:
    """Aggregate summary describing discovery execution."""

    total_urls: int
    internal_pages: int
    external_pages: int
    assets: int

    def to_dict(self) -> dict[str, int]:
        return {
            "total": self.total_urls,
            "internal_pages": self.internal_pages,
            "external_pages": self.external_pages,
            "assets": self.assets,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryInventory:
    """Final structure persisted to project storage."""

    project_id: str
    domain: str
    generated_at: datetime
    summary: DiscoverySummary
    urls: tuple[DiscoveredURL, ...]
    sources: dict[str, bool]

    def to_dict(self) -> dict[str, Any]:
        return {
            "project": {
                "id": self.project_id,
                "domain": self.domain,
            },
            "generated_at": self.generated_at.astimezone(UTC).isoformat(),
            "summary": self.summary.to_dict(),
            "sources": self.sources,
            "urls": self._group_urls(),
        }

    def _group_urls(self) -> dict[str, list[dict[str, Any]]]:
        buckets: dict[str, list[dict[str, Any]]] = {
            "internal_pages": [],
            "external_pages": [],
            "assets": [],
        }
        for entry in self.urls:
            category = entry.category()
            bucket_key = category + "s" if category != "asset" else "assets"
            buckets[bucket_key].append(entry.to_dict())
        for bucket in buckets.values():
            bucket.sort(key=lambda item: (item["depth"], item["url"]))
        return buckets

    def total(self) -> int:
        return self.summary.total_urls


def build_summary(urls: list[DiscoveredURL]) -> DiscoverySummary:
    internal = sum(1 for item in urls if item.category() == "internal_page")
    external = sum(1 for item in urls if item.category() == "external_page")
    assets = sum(1 for item in urls if item.category() == "asset")
    return DiscoverySummary(
        total_urls=len(urls),
        internal_pages=internal,
        external_pages=external,
        assets=assets,
    )


__all__ = [
    "DiscoveredURL",
    "DiscoveryInventory",
    "DiscoverySummary",
    "build_summary",
]
