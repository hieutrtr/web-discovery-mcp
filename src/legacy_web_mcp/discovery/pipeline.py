"""Website discovery orchestration."""
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

import structlog
from fastmcp import Context

from legacy_web_mcp.config.settings import MCPSettings
from legacy_web_mcp.discovery.crawler import crawl
from legacy_web_mcp.discovery.http import AiohttpFetcher, Fetcher
from legacy_web_mcp.discovery.models import (
    DiscoveredURL,
    DiscoveryInventory,
    build_summary,
)
from legacy_web_mcp.discovery.robots import analyze_robots
from legacy_web_mcp.discovery.sitemap import fetch_sitemaps
from legacy_web_mcp.discovery.utils import (
    InvalidTargetURL,
    absolute_url,
    estimate_complexity,
    generate_description,
    generate_title,
    is_asset_url,
    is_internal_url,
    normalize_url,
    timestamp_now,
)
from legacy_web_mcp.storage.projects import ProjectStore

_LOGGER = structlog.get_logger(__name__)


@dataclass(slots=True)
class DiscoverySources:
    sitemap: bool
    robots: bool
    crawl: bool

    def to_dict(self) -> dict[str, bool]:
        return {"sitemap": self.sitemap, "robots": self.robots, "crawl": self.crawl}


class WebsiteDiscoveryService:
    """Coordinate website discovery workflow across multiple strategies."""

    def __init__(
        self,
        settings: MCPSettings,
        *,
        project_store: ProjectStore,
        fetcher: Fetcher | None = None,
    ) -> None:
        self._settings = settings
        self._project_store = project_store
        self._fetcher = fetcher or AiohttpFetcher(timeout=settings.DISCOVERY_TIMEOUT)

    async def discover(self, context: Context, target_url: str) -> dict[str, Any]:
        normalized = normalize_url(target_url)
        await context.info(f"Validated target URL: {normalized.url}")

        project = self._project_store.initialize_project(
            normalized.domain,
            configuration_snapshot=self._settings.display_dict(),
            created_at=timestamp_now(),
        )
        await context.info(f"Initialized project {project.paths.project_id}")

        robots = await analyze_robots(self._fetcher, normalized.url)
        await context.info("Analyzed robots.txt directives")

        sitemap_urls, sitemap_errors = await fetch_sitemaps(
            self._fetcher,
            normalized.url,
            additional_candidates=robots.sitemap_urls,
        )
        if sitemap_urls:
            await context.info(f"Parsed sitemap URLs ({len(sitemap_urls)})")
        elif sitemap_errors:
            await context.info("No sitemap URLs discovered; will use crawl fallback")

        records: dict[str, DiscoveredURL] = {}
        self._ingest(records, sitemap_urls, normalized.domain, source="sitemap", depth=0)

        allowed_from_robots = [
            absolute_url(normalized.url, path) for path in robots.allowed_paths
        ]
        self._ingest(
            records, allowed_from_robots, normalized.domain, source="robots_allow", depth=0
        )

        crawl_records: list[tuple[str, int, str]] = []
        used_crawl = False
        if not sitemap_urls:
            crawl_records = await crawl(
                normalized.url,
                fetcher=self._fetcher,
                robots=robots,
                max_depth=self._settings.DISCOVERY_MAX_DEPTH,
                allowed_domains=[normalized.domain],
            )
            if crawl_records:
                used_crawl = True
                await context.info(f"Manual crawl discovered {len(crawl_records)} URLs")
            else:
                await context.info("Manual crawl completed with no additional URLs")

        self._ingest_records(records, crawl_records, normalized.domain)

        url_list = list(records.values())
        summary = build_summary(url_list)
        sources = DiscoverySources(
            sitemap=bool(sitemap_urls),
            robots=bool(robots.allowed_paths),
            crawl=used_crawl,
        )
        inventory = DiscoveryInventory(
            project_id=project.paths.project_id,
            domain=normalized.domain,
            generated_at=timestamp_now(),
            summary=summary,
            urls=tuple(url_list),
            sources=sources.to_dict(),
        )

        project = self._project_store.write_url_inventory(
            project,
            inventory.to_dict(),
            discovered_count=summary.total_urls,
        )
        await context.info("Persisted URL inventory to project storage")
        _LOGGER.info(
            "discovery_completed",
            project_id=project.paths.project_id,
            total_urls=summary.total_urls,
        )
        return {
            "project_id": project.paths.project_id,
            "domain": normalized.domain,
            "summary": summary.to_dict(),
            "sources": sources.to_dict(),
            "inventory": inventory.to_dict(),
            "paths": {
                "root": str(project.paths.root),
                "inventory_json": str(project.paths.inventory_json_path),
                "inventory_yaml": str(project.paths.inventory_yaml_path),
            },
            "errors": {
                "sitemaps": sitemap_errors,
            },
        }

    def _ingest(
        self,
        records: dict[str, DiscoveredURL],
        urls: Iterable[str],
        domain: str,
        *,
        source: str,
        depth: int,
    ) -> None:
        for url in urls:
            self._upsert_record(records, url, source, depth, domain)

    def _ingest_records(
        self,
        records: dict[str, DiscoveredURL],
        discovered: Iterable[tuple[str, int, str]],
        domain: str,
    ) -> None:
        for url, depth, source in discovered:
            self._upsert_record(records, url, source, depth, domain)

    def _upsert_record(
        self,
        records: dict[str, DiscoveredURL],
        url: str,
        source: str,
        depth: int,
        domain: str,
    ) -> None:
        internal = is_internal_url(url, domain)
        asset = is_asset_url(url)
        entry = DiscoveredURL(
            url=url,
            source=source,
            depth=depth,
            internal=internal,
            asset=asset,
            title=generate_title(url, domain),
            description=generate_description(source, depth),
            complexity=estimate_complexity(url),
        )
        existing = records.get(url)
        if existing is None or depth < existing.depth:
            records[url] = entry


__all__ = ["WebsiteDiscoveryService", "InvalidTargetURL"]
