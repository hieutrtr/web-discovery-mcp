"""Checkpoint management for analysis workflows."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping, Optional

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

    logger = _Shim(logging.getLogger(__name__))

from legacy_web_mcp.storage import ProjectPaths


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")


@dataclass(slots=True)
class CheckpointState:
    project_id: str
    created_at: str
    queue: list[str]
    current_url: str | None
    tracker_state: Mapping[str, object]


class CheckpointManager:
    """Persist and restore workflow checkpoints."""

    def __init__(self, project: ProjectPaths, *, max_history: int = 5) -> None:
        self.project = project
        self.max_history = max_history
        self._directory = project.checkpoints_dir
        self._directory.mkdir(parents=True, exist_ok=True)
        self._latest_path: Path | None = None

    @property
    def latest_path(self) -> Path | None:
        return self._latest_path

    def write(
        self,
        queue: Iterable[str],
        tracker_state: Mapping[str, object],
        current_url: str | None,
    ) -> Path:
        data = {
            "project_id": self.project.project_id,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "queue": list(queue),
            "current_url": current_url,
            "tracker": dict(tracker_state),
        }
        filename = self._directory / f"checkpoint-{_timestamp()}.json"
        filename.write_text(json.dumps(data, indent=2), encoding="utf-8")
        self._latest_path = filename
        logger.info(
            "checkpoint_written",
            project_id=self.project.project_id,
            path=str(filename),
            queue_size=len(data["queue"]),
        )
        self._cleanup_history()
        return filename

    def load_latest(self) -> Optional[CheckpointState]:
        candidates = sorted(self._directory.glob("checkpoint-*.json"))
        if not candidates:
            return None
        latest = candidates[-1]
        try:
            payload = json.loads(latest.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.warning(
                "checkpoint_corrupted",
                project_id=self.project.project_id,
                path=str(latest),
            )
            return None
        self._latest_path = latest
        state = CheckpointState(
            project_id=payload.get("project_id", self.project.project_id),
            created_at=payload.get("created_at", datetime.now(timezone.utc).isoformat()),
            queue=list(payload.get("queue", [])),
            current_url=payload.get("current_url"),
            tracker_state=payload.get("tracker", {}),
        )
        logger.info(
            "checkpoint_loaded",
            project_id=state.project_id,
            path=str(latest),
            queue_size=len(state.queue),
        )
        return state

    def clear_history(self) -> None:
        for path in self._directory.glob("checkpoint-*.json"):
            path.unlink(missing_ok=True)
        self._latest_path = None

    def prune(self, retain: int | None = None) -> None:
        limit = self.max_history if retain is None else max(1, retain)
        checkpoints = sorted(self._directory.glob("checkpoint-*.json"))
        if len(checkpoints) <= limit:
            return
        for path in checkpoints[:-limit]:
            path.unlink(missing_ok=True)
            logger.info(
                "checkpoint_pruned",
                project_id=self.project.project_id,
                path=str(path),
            )

    def _cleanup_history(self) -> None:
        self.prune(self.max_history)


__all__ = ["CheckpointManager", "CheckpointState"]
