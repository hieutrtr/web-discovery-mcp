"""Progress tracking for page analysis workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from statistics import mean
from typing import Dict, Iterable, Mapping, MutableMapping, Optional

try:  # pragma: no cover
    import structlog

    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:  # pragma: no cover
    import logging
    from typing import Any

    logging.basicConfig(level=logging.INFO)

    class _Shim:
        def __init__(self, base: logging.Logger) -> None:
            self._base = base

        def info(self, event: str, **kwargs: Any) -> None:
            self._base.info("%s %s", event, kwargs)

        def warning(self, event: str, **kwargs: Any) -> None:
            self._base.warning("%s %s", event, kwargs)

        def error(self, event: str, **kwargs: Any) -> None:
            self._base.error("%s %s", event, kwargs)

        def debug(self, event: str, **kwargs: Any) -> None:
            self._base.debug("%s %s", event, kwargs)

    logger = _Shim(logging.getLogger(__name__))

from legacy_web_mcp.storage import ProjectPaths


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class PageStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass(slots=True)
class PageProgress:
    url: str
    status: PageStatus = PageStatus.PENDING
    started_at: str | None = None
    completed_at: str | None = None
    duration_seconds: float | None = None
    attempts: int = 0
    retries: int = 0
    last_error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return {
            "url": self.url,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "attempts": self.attempts,
            "retries": self.retries,
            "last_error": self.last_error,
        }


@dataclass(slots=True, frozen=True)
class ProgressSnapshot:
    project_id: str
    total_pages: int
    pending: int
    analyzing: int
    completed: int
    failed: int
    skipped: int
    percentage: float
    average_seconds: float | None
    eta_seconds: float | None
    current_url: str | None
    started_at: str
    updated_at: str
    pages: Mapping[str, dict[str, object]]

    def to_dict(self) -> dict[str, object]:
        return {
            "project_id": self.project_id,
            "total_pages": self.total_pages,
            "pending": self.pending,
            "analyzing": self.analyzing,
            "completed": self.completed,
            "failed": self.failed,
            "skipped": self.skipped,
            "percentage": self.percentage,
            "average_seconds": self.average_seconds,
            "eta_seconds": self.eta_seconds,
            "current_url": self.current_url,
            "started_at": self.started_at,
            "updated_at": self.updated_at,
            "pages": dict(self.pages),
        }


class ProgressTracker:
    """Manage progress state for page analysis workflows."""

    SNAPSHOT_FILE = "analysis-progress.json"
    EVENT_LOG_FILE = "progress-events.log"

    def __init__(self, project: ProjectPaths) -> None:
        self.project = project
        self._pages: Dict[str, PageProgress] = {}
        self._current_url: str | None = None
        self._started_at = _utcnow()
        self._durations: list[float] = []
        self._snapshot_path = project.docs_progress_dir / self.SNAPSHOT_FILE
        self._event_log_path = project.docs_progress_dir / self.EVENT_LOG_FILE
        self._snapshot_path.parent.mkdir(parents=True, exist_ok=True)
        self._event_log_path.touch(exist_ok=True)
        self._load_existing_snapshot()

    # ------------------------------------------------------------------
    # Registration & restoration
    # ------------------------------------------------------------------
    def register_urls(self, urls: Iterable[str]) -> None:
        for url in urls:
            self._pages.setdefault(url, PageProgress(url=url))
        if self._snapshot_path.exists():
            # Ensure snapshot reflects any newly registered URLs.
            self.write_snapshot()

    def restore(self, state: Mapping[str, object]) -> None:
        pages = state.get("pages", {})
        restored: Dict[str, PageProgress] = {}
        for url, payload in pages.items():
            payload_map = dict(payload)
            status_value = payload_map.get("status", PageStatus.PENDING.value)
            try:
                status = PageStatus(str(status_value))
            except ValueError:
                status = PageStatus.PENDING
            duration_value = payload_map.get("duration_seconds")
            try:
                duration = float(duration_value) if duration_value is not None else None
            except (TypeError, ValueError):
                duration = None
            restored[url] = PageProgress(
                url=url,
                status=status,
                started_at=payload_map.get("started_at"),
                completed_at=payload_map.get("completed_at"),
                duration_seconds=duration,
                attempts=int(payload_map.get("attempts", 0) or 0),
                retries=int(payload_map.get("retries", 0) or 0),
                last_error=payload_map.get("last_error"),
            )
            if restored[url].duration_seconds and restored[url].status == PageStatus.COMPLETED:
                self._durations.append(restored[url].duration_seconds)
        self._pages.update(restored)
        self._current_url = state.get("current_url")  # type: ignore[assignment]
        started_at = state.get("started_at")
        if isinstance(started_at, str):
            try:
                candidate = started_at.replace("Z", "+00:00")
                self._started_at = datetime.fromisoformat(candidate)
            except ValueError:
                self._started_at = _utcnow()

    def to_state(self) -> dict[str, object]:
        snapshot = self.snapshot()
        return {
            "current_url": self._current_url,
            "started_at": snapshot.started_at,
            "pages": snapshot.pages,
        }

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------
    def mark_analyzing(self, url: str) -> None:
        record = self._ensure_page(url)
        record.status = PageStatus.ANALYZING
        record.attempts += 1
        record.started_at = _utcnow().isoformat()
        self._current_url = url
        self._log_event("page_analyzing", url=url, attempts=record.attempts)
        self.write_snapshot()

    def mark_completed(self, url: str, duration_seconds: float) -> None:
        record = self._ensure_page(url)
        record.status = PageStatus.COMPLETED
        record.completed_at = _utcnow().isoformat()
        record.duration_seconds = round(duration_seconds, 3)
        record.last_error = None
        self._current_url = None
        if duration_seconds > 0:
            self._durations.append(duration_seconds)
        self._log_event(
            "page_completed",
            url=url,
            duration=round(duration_seconds, 3),
            attempts=record.attempts,
        )
        self.write_snapshot()

    def mark_failed(self, url: str, error: str, *, retrying: bool = False) -> None:
        record = self._ensure_page(url)
        record.status = PageStatus.ANALYZING if retrying else PageStatus.FAILED
        record.last_error = error
        if retrying:
            record.retries += 1
        else:
            self._current_url = None
        self._log_event(
            "page_failed",
            url=url,
            error=error,
            retrying=retrying,
            retries=record.retries,
        )
        self.write_snapshot()

    def mark_skipped(self, url: str) -> None:
        record = self._ensure_page(url)
        record.status = PageStatus.SKIPPED
        record.completed_at = _utcnow().isoformat()
        self._current_url = None
        self._log_event("page_skipped", url=url)
        self.write_snapshot()

    # ------------------------------------------------------------------
    # Snapshot & persistence
    # ------------------------------------------------------------------
    def snapshot(self) -> ProgressSnapshot:
        pending = sum(1 for r in self._pages.values() if r.status == PageStatus.PENDING)
        analyzing = sum(1 for r in self._pages.values() if r.status == PageStatus.ANALYZING)
        completed = sum(1 for r in self._pages.values() if r.status == PageStatus.COMPLETED)
        failed = sum(1 for r in self._pages.values() if r.status == PageStatus.FAILED)
        skipped = sum(1 for r in self._pages.values() if r.status == PageStatus.SKIPPED)
        total = max(len(self._pages), 1)
        percentage = round((completed + skipped) / total * 100, 2)
        average = round(mean(self._durations), 3) if self._durations else None
        remaining = pending + analyzing
        eta = None
        if average is not None and remaining > 0:
            eta = round(average * remaining, 3)
        started_at = self._started_at.isoformat()
        updated_at = _utcnow().isoformat()
        page_payload = {url: record.to_dict() for url, record in self._pages.items()}
        return ProgressSnapshot(
            project_id=self.project.project_id,
            total_pages=len(self._pages),
            pending=pending,
            analyzing=analyzing,
            completed=completed,
            failed=failed,
            skipped=skipped,
            percentage=percentage,
            average_seconds=average,
            eta_seconds=eta,
            current_url=self._current_url,
            started_at=started_at,
            updated_at=updated_at,
            pages=page_payload,
        )

    def write_snapshot(self) -> None:
        snapshot = self.snapshot()
        self._snapshot_path.write_text(
            json.dumps(snapshot.to_dict(), indent=2),
            encoding="utf-8",
        )
        self._update_metadata(snapshot)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_page(self, url: str) -> PageProgress:
        if url not in self._pages:
            self._pages[url] = PageProgress(url=url)
        return self._pages[url]

    def _log_event(self, event: str, **data: object) -> None:
        payload = {"event": event, "timestamp": _utcnow().isoformat(), **data}
        with self._event_log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload) + "\n")
        logger.info(event, project_id=self.project.project_id, **data)

    def _load_existing_snapshot(self) -> None:
        if not self._snapshot_path.exists():
            return
        try:
            data = json.loads(self._snapshot_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(
                "progress_snapshot_corrupted",
                project_id=self.project.project_id,
                path=str(self._snapshot_path),
            )
            return
        self.restore(data)

    def _update_metadata(self, snapshot: ProgressSnapshot) -> None:
        metadata_path = self.project.docs_metadata_file
        metadata: MutableMapping[str, object] = {}
        if metadata_path.exists():
            try:
                metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                metadata = {}
        metadata.update(
            {
                "project_id": snapshot.project_id,
                "updated_at": snapshot.updated_at,
                "completed_pages": snapshot.completed,
                "failed_pages": snapshot.failed,
                "skipped_pages": snapshot.skipped,
                "total_pages": snapshot.total_pages,
                "status": "completed"
                if snapshot.completed + snapshot.skipped >= snapshot.total_pages
                else "running",
                "percentage": snapshot.percentage,
                "eta_seconds": snapshot.eta_seconds,
            }
        )
        metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")


__all__ = [
    "PageStatus",
    "PageProgress",
    "ProgressSnapshot",
    "ProgressTracker",
]
