from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import urlparse

from legacy_web_mcp.storage import ProjectPaths

NETWORK_DIR = "network"
ASSET_EXTENSIONS = {"css", "js", "png", "jpg", "jpeg", "gif", "svg", "ico"}


@dataclass(slots=True)
class NetworkEvent:
    url: str
    method: str
    status: int | None
    resource_type: str
    request_headers: Dict[str, str] = field(default_factory=dict)
    response_headers: Dict[str, str] = field(default_factory=dict)
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    body_size: int | None = None
    duration_ms: float | None = None


@dataclass(slots=True)
class NetworkTrafficReport:
    page_url: str
    events: List[NetworkEvent] = field(default_factory=list)

    def add_event(self, event: NetworkEvent) -> None:
        self.events.append(event)

    def summary(self) -> Dict[str, Any]:
        totals: Dict[str, int] = {}
        for event in self.events:
            totals[event.resource_type] = totals.get(event.resource_type, 0) + 1
        return {
            "page_url": self.page_url,
            "total_events": len(self.events),
            "by_type": totals,
        }


class NetworkTrafficRecorder:
    def __init__(self, page_url: str) -> None:
        self.report = NetworkTrafficReport(page_url)

    @staticmethod
    def classify(url: str) -> str:
        path = Path(urlparse(url).path)
        suffix = path.suffix.lower()
        if suffix and suffix[1:] in ASSET_EXTENSIONS:
            return "asset"
        if "api" in path.parts:
            return "api"
        return "page"

    def record(
        self,
        *,
        url: str,
        method: str,
        status: int | None,
        request_headers: Dict[str, str] | None = None,
        response_headers: Dict[str, str] | None = None,
        body_size: int | None = None,
        duration_ms: float | None = None,
    ) -> None:
        event = NetworkEvent(
            url=url,
            method=method,
            status=status,
            resource_type=self.classify(url),
            request_headers=request_headers or {},
            response_headers=response_headers or {},
            body_size=body_size,
            duration_ms=duration_ms,
        )
        self.report.add_event(event)

    def export(self) -> NetworkTrafficReport:
        return self.report


def save_network_report(project: ProjectPaths, report: NetworkTrafficReport) -> Path:
    directory = project.analysis_dir / NETWORK_DIR
    directory.mkdir(parents=True, exist_ok=True)
    filename_slug = slugify_url(report.page_url)
    output = directory / f"{filename_slug}-network.json"
    payload = {
        "page_url": report.page_url,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": report.summary(),
        "events": [asdict(event) for event in report.events],
    }
    output.write_text(json.dumps(payload, indent=2))
    return output


def slugify_url(url: str) -> str:
    parsed = urlparse(url)
    parts = [parsed.netloc] + [p for p in parsed.path.split("/") if p]
    slug = "-".join(parts) or parsed.netloc or "page"
    slug = slug.replace(":", "-")
    return slug or "page"
