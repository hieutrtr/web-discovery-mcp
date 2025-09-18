from __future__ import annotations

import asyncio
import json
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Awaitable, Callable, Deque, Dict, List, Mapping, Optional

from legacy_web_mcp.analysis import collect_page_analysis
from legacy_web_mcp.config import Settings, load_settings
from legacy_web_mcp.network import NetworkTrafficRecorder
from legacy_web_mcp.navigation import navigate_to_page
from legacy_web_mcp.storage import ProjectPaths

NavigateCallable = Callable[[str, ProjectPaths], Awaitable[Mapping[str, Path | str | float | List[str]]]]
FetchHtml = Callable[[str], Awaitable[str]]


@dataclass
class WorkflowProgress:
    completed: List[str] = field(default_factory=list)
    failed: List[Dict[str, str]] = field(default_factory=list)
    skipped: List[str] = field(default_factory=list)
    current: Optional[str] = None
    checkpoint_path: Optional[Path] = None


class SequentialNavigationWorkflow:
    def __init__(
        self,
        project: ProjectPaths,
        urls: List[str],
        *,
        settings: Settings | None = None,
        fetch_html: FetchHtml | None = None,
    ) -> None:
        self.project = project
        self.settings = settings or load_settings()
        self._queue: Deque[str] = deque(urls)
        self._initial_urls = list(urls)
        self._paused = asyncio.Event()
        self._paused.set()
        self._progress = WorkflowProgress()
        self._checkpoint_file = project.root_path / "progress.json"
        self._fetch_html = fetch_html

    def pause(self) -> None:
        self._paused.clear()

    def resume(self) -> None:
        self._paused.set()

    def skip(self, url: str) -> None:
        try:
            self._queue.remove(url)
            self._progress.skipped.append(url)
            self._write_checkpoint()
        except ValueError:
            pass

    async def run(self) -> WorkflowProgress:
        while self._queue:
            await self._paused.wait()
            url = self._queue.popleft()
            self._progress.current = url
            self._write_checkpoint()
            try:
                await self._process_url(url)
                self._progress.completed.append(url)
            except Exception as exc:  # pragma: no cover - defensive logging
                self._progress.failed.append({"url": url, "error": str(exc)})
            finally:
                self._progress.current = None
                self._write_checkpoint()
        return self._progress

    async def _process_url(self, url: str) -> None:
        recorder = NetworkTrafficRecorder(url)

        async def fetch_with_record(target_url: str) -> str:
            if self._fetch_html is None:
                raise RuntimeError("fetch_html not provided in offline mode")
            html = await self._fetch_html(target_url)
            recorder.record(url=target_url, method="GET", status=200)
            return html

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

    def _write_checkpoint(self) -> None:
        data = {
            "queue": list(self._queue),
            "completed": self._progress.completed,
            "failed": self._progress.failed,
            "skipped": self._progress.skipped,
            "current": self._progress.current,
            "initial_urls": self._initial_urls,
        }
        self._checkpoint_file.write_text(json.dumps(data, indent=2))
        self._progress.checkpoint_path = self._checkpoint_file

    def load_checkpoint(self) -> None:
        if not self._checkpoint_file.exists():
            return
        data = json.loads(self._checkpoint_file.read_text())
        self._queue = deque(data.get("queue", []))
        self._progress.completed = data.get("completed", [])
        self._progress.failed = data.get("failed", [])
        self._progress.skipped = data.get("skipped", [])
        self._progress.current = data.get("current")
        self._progress.checkpoint_path = self._checkpoint_file
