from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter
from typing import Awaitable, Callable, Deque, Dict, List, Mapping, Optional

from legacy_web_mcp.analysis import PageAnalysis, collect_page_analysis
from legacy_web_mcp.config import Settings, load_settings
from legacy_web_mcp.documentation import DocumentationGenerator
from legacy_web_mcp.network import NetworkTrafficRecorder
from legacy_web_mcp.navigation import navigate_to_page
from legacy_web_mcp.progress import (
    CheckpointManager,
    ProgressSnapshot,
    ProgressTracker,
)
from legacy_web_mcp.storage import ProjectPaths

NavigateCallable = Callable[[str, ProjectPaths], Awaitable[Mapping[str, Path | str | float | List[str]]]]
FetchHtml = Callable[[str], Awaitable[str]]


@dataclass(slots=True)
class WorkflowProgress:
    snapshot: ProgressSnapshot
    checkpoint_path: Optional[Path]


class SequentialNavigationWorkflow:
    def __init__(
        self,
        project: ProjectPaths,
        urls: List[str],
        *,
        settings: Settings | None = None,
        fetch_html: FetchHtml | None = None,
        resume: bool = True,
        tracker: ProgressTracker | None = None,
        checkpoints: CheckpointManager | None = None,
        documentation: DocumentationGenerator | None = None,
    ) -> None:
        self.project = project
        self.settings = settings or load_settings()
        self.progress_tracker = tracker or ProgressTracker(project)
        self.checkpoint_manager = checkpoints or CheckpointManager(project)
        self.documentation_generator = documentation or DocumentationGenerator(project)
        self._initial_urls = list(urls)
        self.progress_tracker.register_urls(urls)
        self._queue: Deque[str] = deque(urls)
        self._paused = asyncio.Event()
        self._paused.set()
        self._fetch_html = fetch_html
        if resume:
            self._attempt_resume()
        else:
            self._persist_state(current_url=None)

    def pause(self) -> None:
        self._paused.clear()
        current = self.progress_tracker.snapshot().current_url
        self._persist_state(current_url=current)

    def resume(self) -> None:
        self._paused.set()

    def manual_checkpoint(self) -> Path:
        snapshot = self.progress_tracker.snapshot()
        return self._persist_state(current_url=snapshot.current_url)

    def cleanup_checkpoints(self, retain: int | None = None) -> None:
        self.checkpoint_manager.prune(retain)

    def skip(self, url: str) -> None:
        try:
            self._queue.remove(url)
            self.progress_tracker.mark_skipped(url)
            self._persist_state(current_url=None)
        except ValueError:
            pass

    async def run(self) -> WorkflowProgress:
        checkpoint_path: Path | None = None
        while self._queue:
            await self._paused.wait()
            url = self._queue.popleft()
            self.progress_tracker.mark_analyzing(url)
            checkpoint_path = self._persist_state(current_url=url)
            try:
                duration, analysis = await self._process_url(url)
                self.progress_tracker.mark_completed(url, duration)
                self.documentation_generator.update_page(
                    page=analysis,
                    summary=None,
                    feature=None,
                    progress=self.progress_tracker.snapshot(),
                )
            except Exception as exc:  # pragma: no cover - defensive logging
                self.progress_tracker.mark_failed(url, str(exc))
                checkpoint_path = self._persist_state(current_url=None)
            finally:
                checkpoint_path = self._persist_state(current_url=None)
        snapshot = self.progress_tracker.snapshot()
        return WorkflowProgress(snapshot=snapshot, checkpoint_path=checkpoint_path)

    async def _process_url(self, url: str) -> tuple[float, PageAnalysis]:
        recorder = NetworkTrafficRecorder(url)

        async def fetch_with_record(target_url: str) -> str:
            if self._fetch_html is None:
                raise RuntimeError("fetch_html not provided in offline mode")
            html = await self._fetch_html(target_url)
            recorder.record(url=target_url, method="GET", status=200)
            return html

        started = perf_counter()
        capture = await navigate_to_page(
            url,
            self.project,
            fetch=fetch_with_record if self._fetch_html else None,
            headless=self.settings.headless,
        )

        analysis = collect_page_analysis(
            project=self.project,
            page_url=url,
            html=capture.html_path.read_text(encoding="utf-8"),
            text_content=capture.text_path.read_text(encoding="utf-8"),
            navigation_metadata={
                "title": capture.metadata.get("title", url),
                "load_seconds": capture.metadata.get("load_seconds"),
            },
            network_report=recorder.export(),
        )
        self._progress_log_entry(url, analysis.analysis_path)
        duration = perf_counter() - started
        return duration, analysis

    def _progress_log_entry(self, url: str, analysis_path: Path) -> None:
        log_dir = self.project.root_path / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / "workflow.log"
        entry = {
            "url": url,
            "analysis": str(analysis_path),
        }
        with log_file.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry) + "\n")

    def _persist_state(self, current_url: str | None) -> Path:
        checkpoint = self.checkpoint_manager.write(
            queue=list(self._queue),
            tracker_state=self.progress_tracker.to_state(),
            current_url=current_url,
        )
        return checkpoint

    def _attempt_resume(self) -> None:
        state = self.checkpoint_manager.load_latest()
        if state is None:
            return
        self.progress_tracker.restore(state.tracker_state)
        rebuilt_queue: List[str] = []
        if state.current_url:
            rebuilt_queue.append(state.current_url)
        rebuilt_queue.extend(state.queue)
        if rebuilt_queue:
            self._queue = deque(rebuilt_queue)
        self.progress_tracker.write_snapshot()
