"""Helper utilities for website discovery."""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse, urlunparse

_ALLOWED_SCHEMES = {"http", "https"}
_ASSET_EXTENSIONS = {
    ".css",
    ".js",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".webp",
    ".woff",
    ".woff2",
    ".ttf",
    ".pdf",
}

_TITLE_CLEAN_PATTERN = re.compile(r"[-_]+")


class InvalidTargetURL(ValueError):
    """Raised when a provided URL cannot be used for discovery."""


@dataclass(frozen=True, slots=True)
class NormalizedURL:
    """Normalized representation of a target URL."""

    url: str
    domain: str


def normalize_url(target: str) -> NormalizedURL:
    parsed = urlparse(target.strip())
    if parsed.scheme.lower() not in _ALLOWED_SCHEMES:
        msg = "Discovery target must use http or https scheme"
        raise InvalidTargetURL(msg)
    if not parsed.netloc:
        msg = "Discovery target must include a hostname"
        raise InvalidTargetURL(msg)

    normalized = parsed._replace(
        scheme=parsed.scheme.lower(),
        netloc=parsed.netloc.lower(),
        fragment="",
    )
    url = urlunparse(normalized)
    domain = normalized.netloc
    return NormalizedURL(url=url, domain=domain)


def is_internal_url(url: str, domain: str) -> bool:
    parsed = urlparse(url)
    return parsed.netloc.lower() == domain.lower()


def is_asset_url(url: str) -> bool:
    path = urlparse(url).path
    extension = PurePosixPath(path).suffix.lower()
    return extension in _ASSET_EXTENSIONS


def absolute_url(base: str, link: str) -> str:
    return urljoin(base, link)


def generate_title(url: str, domain: str) -> str:
    parsed = urlparse(url)
    if parsed.path in {"", "/"}:
        return domain
    slug = PurePosixPath(parsed.path).name or domain
    cleaned = _TITLE_CLEAN_PATTERN.sub(" ", slug).strip()
    return cleaned.title() if cleaned else domain


def generate_description(source: str, depth: int) -> str:
    return f"Discovered via {source} at depth {depth}."


def estimate_complexity(url: str) -> str:
    parsed = urlparse(url)
    path_segments = [segment for segment in parsed.path.split("/") if segment]
    score = len(path_segments) + (1 if parsed.query else 0)
    if score <= 2:
        return "low"
    if score <= 5:
        return "medium"
    return "high"


def dedupe_preserve_order(urls: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def timestamp_now() -> datetime:
    return datetime.now(tz=UTC)


__all__ = [
    "NormalizedURL",
    "InvalidTargetURL",
    "absolute_url",
    "dedupe_preserve_order",
    "estimate_complexity",
    "generate_description",
    "generate_title",
    "is_asset_url",
    "is_internal_url",
    "normalize_url",
    "timestamp_now",
]
