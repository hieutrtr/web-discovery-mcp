from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

UrlType = Literal["page", "asset"]


@dataclass(slots=True)
class DiscoveredUrl:
    url: str
    source: str
    depth: int
    url_type: UrlType
    title: str | None = None
    description: str | None = None


@dataclass
class DiscoveryReport:
    root_url: str
    pages: list[DiscoveredUrl] = field(default_factory=list)
    assets: list[DiscoveredUrl] = field(default_factory=list)
    progress: list[str] = field(default_factory=list)
    metadata_path: str | None = None
