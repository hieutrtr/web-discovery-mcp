"""Automated YOLO analysis workflow."""

from __future__ import annotations

import asyncio
import json
import time
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Awaitable, Callable, Deque, Dict, Mapping, Optional, Sequence

try:  # pragma: no cover
    import structlog

    logger = structlog.get_logger(__name__)
except ModuleNotFoundError:  # pragma: no cover
    import logging

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

from legacy_web_mcp.analysis import collect_page_analysis
from legacy_web_mcp.config import Settings, load_settings
from legacy_web_mcp.documentation import DocumentationGenerator
from legacy_web_mcp.errors import LegacyWebMCPError
from legacy_web_mcp.interaction import discover_interactions
from legacy_web_mcp.llm.client import LLMClient, build_default_client
from legacy_web_mcp.llm.feature_analysis import analyse_features
from legacy_web_mcp.llm.summary import summarize_content
from legacy_web_mcp.navigation import navigate_to_page
from legacy_web_mcp.network import NetworkTrafficRecorder, save_network_report
from legacy_web_mcp.progress import CheckpointManager, ProgressSnapshot, ProgressTracker
from legacy_web_mcp.storage import ProjectPaths

FetchHtml = Callable[[str], Awaitable[str]]


@dataclass(slots=True)
class QueueItem:
    url: str
    attempt: int = 1


@dataclass(slots=True)
class YoloAnalysisConfig:
    step1_model: str = "step1"
    step2_model: str = "step2"
    max_concurrency: int = 1
    max_attempts: int = 3
    status_interval: float = 20.0

    @classmethod
    def from_settings(
        cls,
        settings: Settings,
        *,
        overrides: Mapping[str, Any] | None = None,
    ) -> "YoloAnalysisConfig":
        data: Dict[str, Any] = {
            "step1_model": "step1",
            "step2_model": "step2",
            "max_concurrency": max(1, settings.max_concurrent_browsers),
            "max_attempts": 3,
            "status_interval": 20.0,
        }
        if overrides:
            data.update({key: value for key, value in overrides.items() if key in data})
        return cls(**data)


@dataclass(slots=True)
class YoloAnalysisResult:
    project_id: str
    snapshot: ProgressSnapshot
    completed: list[str]
    failed: list[str]
    errors: Dict[str, str]
    duration_seconds: float
    checkpoint_path: Optional[str]
    artifacts: Dict[str, str]
    budget: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "project_id": self.project_id,
            "status": "completed"
            if self.snapshot.completed + self.snapshot.skipped >= self.snapshot.total_pages
            else "running",
            "duration_seconds": self.duration_seconds,
            "completed": list(self.completed),
            "failed": list(self.failed),
            "pending": self.snapshot.pending,
            "percentage": self.snapshot.percentage,
            "eta_seconds": self.snapshot.eta_seconds,
            "checkpoint_path": self.checkpoint_path,
            "errors": dict(self.errors),
            "artifacts": dict(self.artifacts),
            "budget": dict(self.budget),
        }


class YoloAnalysisRunner:
    """Coordinates automated YOLO-mode analysis without human intervention."""

    def __init__(
        self,
        project: ProjectPaths,
        urls: Sequence[str],
        *,
        settings: Settings | None = None,
        llm_client: LLMClient | None = None,
        config: YoloAnalysisConfig | None = None,
        progress: ProgressTracker | None = None,
        checkpoints: CheckpointManager | None = None,
        documentation: DocumentationGenerator | None = None,
        fetch_html: FetchHtml | None = None,
    ) -> None:
        if not urls:
            raise ValueError("YOLO analysis requires at least one URL to process")
        self.project = project
        self.settings = settings or load_settings()
        self.llm_client = llm_client or build_default_client()
        self.config = config or YoloAnalysisConfig.from_settings(self.settings)
        self.progress = progress or ProgressTracker(project)
        self.checkpoints = checkpoints or CheckpointManager(project)
        self.documentation = documentation or DocumentationGenerator(project)
        self.fetch_html = fetch_html

        normalized_urls = [url for url in urls if url]
        self.progress.register_urls(normalized_urls)

        self._queue: asyncio.Queue[Optional[QueueItem]] = asyncio.Queue()
        self._pending_snapshot: Deque[QueueItem] = deque()
        for url in normalized_urls:
            self._enqueue(QueueItem(url=url, attempt=1))

        self._progress_lock = asyncio.Lock()
        self._checkpoint_lock = asyncio.Lock()
        self._inflight: set[str] = set()
        self._latest_checkpoint: Optional[Path] = None
        self._completed: list[str] = []
        self._failed: list[str] = []
        self._errors: Dict[str, str] = {}
        self._last_status = 0.0

    async def run(self) -> YoloAnalysisResult:
        start = time.perf_counter()
        worker_count = max(1, min(self.config.max_concurrency, len(self._pending_snapshot)))
        workers = [asyncio.create_task(self._worker(i)) for i in range(worker_count)]
        await self._queue.join()
        for _ in workers:
            self._queue.put_nowait(None)
        await asyncio.gather(*workers)
        duration = round(time.perf_counter() - start, 3)
        snapshot = await self._snapshot()
        artifacts = {
            "master_report": str(self.project.docs_master_report),
            "progress_snapshot": str(self.project.docs_progress_dir / ProgressTracker.SNAPSHOT_FILE),
            "documentation_data": str(self.project.docs_web_dir / DocumentationGenerator.DATA_FILE),
        }
        return YoloAnalysisResult(
            project_id=self.project.project_id,
            snapshot=snapshot,
            completed=list(self._completed),
            failed=list(self._failed),
            errors=dict(self._errors),
            duration_seconds=duration,
            checkpoint_path=str(self._latest_checkpoint) if self._latest_checkpoint else None,
            artifacts=artifacts,
            budget=self.llm_client.budget_status(),
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _enqueue(self, item: QueueItem) -> None:
        self._queue.put_nowait(item)
        self._pending_snapshot.append(item)

    async def _worker(self, worker_id: int) -> None:
        while True:
            item = await self._queue.get()
            if item is None:
                self._queue.task_done()
                break
            if self._pending_snapshot:
                self._pending_snapshot.popleft()
            self._inflight.add(item.url)
            try:
                success, message = await self._process_item(item)
            finally:
                self._inflight.discard(item.url)
                self._queue.task_done()

            if success:
                await self._emit_status("page_completed", item.url)
            else:
                if item.attempt < self.config.max_attempts:
                    self._enqueue(QueueItem(url=item.url, attempt=item.attempt + 1))
                    await self._emit_status("page_retry", item.url, extra={"attempt": item.attempt + 1})
                else:
                    self._failed.append(item.url)
                    await self._emit_status("page_failed", item.url, extra={"error": message})
            await self._checkpoint(None)

    async def _process_item(self, item: QueueItem) -> tuple[bool, Optional[str]]:
        url = item.url
        recorder = NetworkTrafficRecorder(url)

        async def fetch_with_record(target_url: str) -> str:
            if self.fetch_html is None:
                raise RuntimeError("fetch_html callback not provided for offline processing")
            html = await self.fetch_html(target_url)
            recorder.record(url=target_url, method="GET", status=200)
            return html

        async with self._progress_lock:
            self.progress.mark_analyzing(url)
        await self._checkpoint(url)

        started = time.perf_counter()
        try:
            capture = await navigate_to_page(
                url,
                self.project,
                fetch=fetch_with_record if self.fetch_html else None,
                headless=self.settings.headless,
            )
            html = capture.html_path.read_text(encoding="utf-8")
            interactions = discover_interactions(html)
            report = recorder.export()
            save_network_report(self.project, report)
            analysis = collect_page_analysis(
                project=self.project,
                page_url=url,
                html=html,
                text_content=capture.text_path.read_text(encoding="utf-8"),
                navigation_metadata={
                    "title": capture.metadata.get("title", url),
                    "load_seconds": capture.metadata.get("load_seconds"),
                },
                network_report=report,
            )

            summary = await summarize_content(
                analysis,
                llm_client=self.llm_client,
                model_alias=self.config.step1_model,
            )

            feature = await analyse_features(
                analysis,
                summary,
                interactions,
                report,
                llm_client=self.llm_client,
                model_alias=self.config.step2_model,
                max_interactions=self.settings.max_interactions_for_analysis,
                max_api_events=self.settings.max_api_events_for_analysis,
            )

            duration = time.perf_counter() - started
            async with self._progress_lock:
                self.progress.mark_completed(url, duration)
                snapshot = self.progress.snapshot()
            self._completed.append(url)
            self.documentation.update_page(
                page=analysis,
                summary=summary,
                feature=feature,
                progress=snapshot,
            )
            self._errors.pop(url, None)
            return True, None
        except Exception as exc:
            message = _render_error(exc)
            self._errors[url] = message
            retrying = item.attempt < self.config.max_attempts
            async with self._progress_lock:
                self.progress.mark_failed(url, message, retrying=retrying)
            logger.warning(
                "yolo_page_error",
                project_id=self.project.project_id,
                url=url,
                attempt=item.attempt,
                retrying=retrying,
                error=message,
            )
            return False, message

    async def _snapshot(self) -> ProgressSnapshot:
        async with self._progress_lock:
            return self.progress.snapshot()

    async def _checkpoint(self, current_url: Optional[str]) -> None:
        state = await self._snapshot_state()
        queue_urls = [entry.url for entry in list(self._pending_snapshot)]

        async with self._checkpoint_lock:
            path = await asyncio.to_thread(
                self.checkpoints.write,
                queue_urls,
                state,
                current_url,
            )
            self._latest_checkpoint = path

    async def _snapshot_state(self) -> Dict[str, Any]:
        async with self._progress_lock:
            tracker_state = self.progress.to_state()
        tracker_state.setdefault("yolo", {})
        tracker_state["yolo"] = {
            "config": asdict(self.config),
            "pending": [asdict(item) for item in list(self._pending_snapshot)],
            "inflight": list(self._inflight),
            "completed": list(self._completed),
            "failed": list(self._failed),
        }
        return tracker_state

    async def _emit_status(self, event: str, url: str, *, extra: Mapping[str, Any] | None = None) -> None:
        now = time.perf_counter()
        if now - self._last_status < self.config.status_interval and event == "page_completed":
            return
        snapshot = await self._snapshot()
        payload = {
            "project_id": self.project.project_id,
            "status_event": event,
            "url": url,
            "completed": snapshot.completed,
            "pending": snapshot.pending,
            "failed": snapshot.failed,
            "percentage": snapshot.percentage,
        }
        if extra:
            payload.update(extra)
        logger.info("yolo_status", **payload)
        if event == "page_completed":
            self._last_status = now


def _render_error(exc: Exception) -> str:
    if isinstance(exc, LegacyWebMCPError):
        return f"{exc.code}:{exc.message}"
    return f"{exc.__class__.__name__}:{exc}"


def load_discovered_urls(project: ProjectPaths) -> list[str]:
    inventory = project.discovery_dir / "urls.json"
    if not inventory.exists():
        raise FileNotFoundError(inventory)
    data = json.loads(inventory.read_text(encoding="utf-8"))
    pages = data.get("pages", [])
    urls: list[str] = []
    seen: set[str] = set()
    for entry in pages:
        if not isinstance(entry, Mapping):
            continue
        url = entry.get("url")
        url_type = entry.get("url_type", "page")
        if not url or url_type != "page":
            continue
        if url in seen:
            continue
        seen.add(url)
        urls.append(url)
    return urls


async def run_yolo_analysis(
    project: ProjectPaths,
    *,
    urls: Sequence[str],
    settings: Settings | None = None,
    llm_client: LLMClient | None = None,
    config_overrides: Mapping[str, Any] | None = None,
    fetch_html: FetchHtml | None = None,
    progress: ProgressTracker | None = None,
    checkpoints: CheckpointManager | None = None,
    documentation: DocumentationGenerator | None = None,
) -> YoloAnalysisResult:
    settings = settings or load_settings()
    config = YoloAnalysisConfig.from_settings(settings, overrides=config_overrides)
    runner = YoloAnalysisRunner(
        project,
        urls,
        settings=settings,
        llm_client=llm_client,
        config=config,
        fetch_html=fetch_html,
        progress=progress,
        checkpoints=checkpoints,
        documentation=documentation,
    )
    return await runner.run()


__all__ = [
    "YoloAnalysisConfig",
    "YoloAnalysisResult",
    "YoloAnalysisRunner",
    "load_discovered_urls",
    "run_yolo_analysis",
]
