"""Interactive analysis workflow supporting human-in-the-loop decisions."""

from __future__ import annotations

import asyncio
import time
from collections import deque
from dataclasses import dataclass, replace
from typing import Any, Awaitable, Callable, Deque, Iterable, Mapping, Optional, Protocol, Sequence, TYPE_CHECKING

from legacy_web_mcp.analysis import PageAnalysis
from legacy_web_mcp.interaction.actions import InteractionAction
from legacy_web_mcp.llm.client import LLMClient
from legacy_web_mcp.progress import CheckpointManager, ProgressSnapshot, ProgressTracker
from legacy_web_mcp.storage import ProjectPaths

if TYPE_CHECKING:  # pragma: no cover - avoids circular import at runtime
    from legacy_web_mcp.llm.feature_analysis import FeatureAnalysis
    from legacy_web_mcp.llm.summary import ContentSummary
    from legacy_web_mcp.documentation import DocumentationGenerator


class InteractiveIO(Protocol):
    async def choose(self, prompt: str, options: Sequence[str]) -> int:
        ...

    async def confirm(self, prompt: str) -> bool:
        ...

    async def input_text(self, prompt: str, *, default: str = "") -> str:
        ...

    async def notify(self, message: str) -> None:
        ...


@dataclass(slots=True)
class InteractiveConfig:
    step1_model: str = "step1"
    step2_model: str = "step2"
    timeout_seconds: float = 60.0


@dataclass(slots=True)
class InteractivePageContext:
    page: PageAnalysis
    interactions: Sequence[InteractionAction]
    network_report: Any


@dataclass(slots=True)
class InteractiveAnalysisResult:
    snapshot: ProgressSnapshot
    checkpoint_path: Optional[str]
    completed: list[str]
    skipped: list[str]


PageLoader = Callable[[str], Awaitable[InteractivePageContext]]
SummaryRunner = Callable[[PageAnalysis, LLMClient, str], Awaitable["ContentSummary"]]
FeatureRunner = Callable[
    [PageAnalysis, "ContentSummary", Sequence[InteractionAction], Any, LLMClient, str],
    Awaitable["FeatureAnalysis"],
]


class InteractiveAnalysisSession:
    """Coordinates interactive analysis with explicit user decisions."""

    def __init__(
        self,
        *,
        project: ProjectPaths,
        urls: Sequence[str],
        page_loader: PageLoader,
        summary_runner: SummaryRunner,
        feature_runner: FeatureRunner,
        llm_client: LLMClient,
        io: InteractiveIO,
        checkpoints: CheckpointManager,
        progress: ProgressTracker,
        documentation: "DocumentationGenerator",
        config: InteractiveConfig | None = None,
    ) -> None:
        self.project = project
        self.page_loader = page_loader
        self.summary_runner = summary_runner
        self.feature_runner = feature_runner
        self.llm_client = llm_client
        self.io = io
        self.checkpoints = checkpoints
        self.progress = progress
        self.documentation = documentation
        self.config = config or InteractiveConfig()
        self.queue: Deque[str] = deque(urls)
        self.progress.register_urls(urls)
        self.completed: list[str] = []
        self.skipped: list[str] = []
        self._latest_checkpoint: Optional[str] = None

    async def run(self) -> InteractiveAnalysisResult:
        """Execute the interactive analysis session."""

        while self.queue:
            url = self.queue[0]
            choice = await self._page_menu(url)
            if choice == "skip":
                skipped_url = self.queue.popleft()
                self.progress.mark_skipped(skipped_url)
                self.skipped.append(skipped_url)
                await self._checkpoint(current_url=None)
                continue
            if choice == "defer":
                self.queue.rotate(-1)
                await self._checkpoint(current_url=None)
                continue
            if choice == "add":
                await self._add_page()
                continue
            if choice == "config":
                await self._adjust_configuration()
                continue
            if choice == "pause":
                snapshot = self.progress.snapshot()
                await self._checkpoint(current_url=url)
                return InteractiveAnalysisResult(
                    snapshot=snapshot,
                    checkpoint_path=self._latest_checkpoint,
                    completed=list(self.completed),
                    skipped=list(self.skipped),
                )

            # Proceed with analysis
            self.queue.popleft()
            await self._notify_cost_estimate(url)
            confirmed = await self.io.confirm(
                f"Proceed with analysis of {url}?"
            )
            if not confirmed:
                self.queue.append(url)
                await self._checkpoint(current_url=None)
                continue

            await self._checkpoint(current_url=url)
            self.progress.mark_analyzing(url)

            started = time.perf_counter()
            context = await self.page_loader(url)
            summary = await self._interactive_summary(context.page)
            if summary is None:
                self.progress.mark_failed(url, "summary_rejected", retrying=False)
                await self._checkpoint(current_url=None)
                continue

            feature = await self._interactive_feature(context, summary)
            if feature is None:
                self.progress.mark_failed(url, "feature_rejected", retrying=False)
                await self._checkpoint(current_url=None)
                continue

            duration = time.perf_counter() - started
            self.progress.mark_completed(url, duration)
            self.completed.append(url)
            await self._checkpoint(current_url=None)
            self.documentation.update_page(
                page=context.page,
                summary=summary,
                feature=feature,
                progress=self.progress.snapshot(),
            )

        snapshot = self.progress.snapshot()
        return InteractiveAnalysisResult(
            snapshot=snapshot,
            checkpoint_path=self._latest_checkpoint,
            completed=list(self.completed),
            skipped=list(self.skipped),
        )

    async def _page_menu(self, url: str) -> str:
        options = [
            "Analyze now",
            "Skip page",
            "Move to end",
            "Add or prioritize page",
            "Adjust models/timeouts",
            "Pause session",
        ]
        idx = await self.io.choose(
            f"Next page: {url}\nSelect an action:", options
        )
        mapping = {
            0: "proceed",
            1: "skip",
            2: "defer",
            3: "add",
            4: "config",
            5: "pause",
        }
        return mapping.get(idx, "proceed")

    async def _add_page(self) -> None:
        new_url = await self.io.input_text("Enter URL to add/prioritize", default="")
        if not new_url:
            return
        insert_choice = await self.io.choose(
            "Where should the new page go?", ["Process next", "Append to end"]
        )
        if insert_choice == 0:
            self.queue.appendleft(new_url)
        else:
            self.queue.append(new_url)
        self.progress.register_urls([new_url])
        await self._checkpoint(current_url=None)

    async def _adjust_configuration(self) -> None:
        await self.io.notify(
            f"Current configuration: step1={self.config.step1_model}, step2={self.config.step2_model}, timeout={self.config.timeout_seconds}s"
        )
        choice = await self.io.choose(
            "Adjust which parameter?",
            ["Step 1 model", "Step 2 model", "Timeout", "Cancel"],
        )
        if choice == 0:
            new_model = await self.io.input_text("Enter new Step 1 model alias", default=self.config.step1_model)
            if new_model:
                self.config = replace(self.config, step1_model=new_model)
        elif choice == 1:
            new_model = await self.io.input_text("Enter new Step 2 model alias", default=self.config.step2_model)
            if new_model:
                self.config = replace(self.config, step2_model=new_model)
        elif choice == 2:
            new_timeout = await self.io.input_text("Enter timeout seconds", default=str(self.config.timeout_seconds))
            try:
                seconds = float(new_timeout)
            except ValueError:
                seconds = self.config.timeout_seconds
            self.config = replace(self.config, timeout_seconds=max(5.0, seconds))
        await self._checkpoint(current_url=None)

    async def _notify_cost_estimate(self, url: str) -> None:
        step1_cost = self.llm_client.estimate_cost(
            self.config.step1_model,
            prompt_tokens=1200,
            completion_tokens=600,
        )
        step2_cost = self.llm_client.estimate_cost(
            self.config.step2_model,
            prompt_tokens=1500,
            completion_tokens=900,
        )
        await self.io.notify(
            f"Estimated cost for {url}: Step1≈${step1_cost:.4f}, Step2≈${step2_cost:.4f}"
        )

    async def _interactive_summary(self, page: PageAnalysis) -> Optional["ContentSummary"]:
        attempts = 0
        summary: Optional["ContentSummary"] = None
        while True:
            attempts += 1
            if summary is None:
                summary = await self.summary_runner(page, self.llm_client, self.config.step1_model)
            await self.io.notify(
                "Step 1 summary:\n"
                f"Purpose: {summary.purpose}\n"
                f"Target Users: {summary.target_users}\n"
                f"Business Context: {summary.business_context}\n"
                f"User Journey: {summary.user_journey}\n"
                f"Navigation Role: {summary.navigation_role}\n"
                f"Business Logic: {summary.business_logic}\n"
            )
            decision = await self.io.choose(
                "How would you like to proceed with the summary?",
                ["Approve", "Edit", "Retry", "Abort page"],
            )
            if decision == 0:
                return summary
            if decision == 1:
                summary = await self._edit_summary(summary)
                await self._checkpoint(current_url=page.url)
            elif decision == 2:
                summary = await self.summary_runner(page, self.llm_client, self.config.step1_model)
                await self._checkpoint(current_url=page.url)
            else:
                return None

    async def _edit_summary(self, summary: "ContentSummary") -> "ContentSummary":
        purpose = await self.io.input_text("Purpose", default=summary.purpose)
        target_users = await self.io.input_text("Target users", default=summary.target_users)
        business_context = await self.io.input_text("Business context", default=summary.business_context)
        user_journey = await self.io.input_text("User journey", default=summary.user_journey)
        navigation_role = await self.io.input_text("Navigation role", default=summary.navigation_role)
        business_logic = await self.io.input_text("Business logic", default=summary.business_logic)
        from legacy_web_mcp.llm.summary import ContentSummary as _ContentSummary

        return _ContentSummary(
            page_url=summary.page_url,
            purpose=purpose,
            target_users=target_users,
            business_context=business_context,
            user_journey=user_journey,
            navigation_role=navigation_role,
            business_logic=business_logic,
            confidence=summary.confidence,
            processing_seconds=summary.processing_seconds,
            quality_score=summary.quality_score,
            validation_issues=summary.validation_issues,
            context_highlights=summary.context_highlights,
        )

    async def _interactive_feature(
        self,
        context: InteractivePageContext,
        summary: "ContentSummary",
    ) -> Optional["FeatureAnalysis"]:
        analysis: Optional["FeatureAnalysis"] = None
        while True:
            if analysis is None:
                analysis = await self.feature_runner(
                    context.page,
                    summary,
                    context.interactions,
                    context.network_report,
                    self.llm_client,
                    self.config.step2_model,
                )
            await self.io.notify(
                "Step 2 feature overview:\n"
                f"Functional capabilities: {', '.join(analysis.functional_capabilities) or 'None'}\n"
                f"API integrations: {len(analysis.api_integrations)}\n"
                f"Rebuild requirements: {len(analysis.rebuild_requirements)}"
            )
            decision = await self.io.choose(
                "Validate feature analysis:",
                ["Approve", "Retry", "Abort page"],
            )
            if decision == 0:
                return analysis
            if decision == 1:
                analysis = None
                await self._checkpoint(current_url=context.page.url)
                continue
            return None

    async def _checkpoint(self, current_url: Optional[str]) -> None:
        state = dict(self.progress.to_state())
        state.setdefault("interactive", {})
        state["interactive"] = {
            "config": {
                "step1_model": self.config.step1_model,
                "step2_model": self.config.step2_model,
                "timeout_seconds": self.config.timeout_seconds,
            },
            "queue": list(self.queue),
        }
        path = self.checkpoints.write(
            queue=list(self.queue),
            tracker_state=state,
            current_url=current_url,
        )
        self._latest_checkpoint = str(path)


class SimpleConsoleIO:
    """Fallback InteractiveIO implementation using synchronous console prompts."""

    async def choose(self, prompt: str, options: Sequence[str]) -> int:
        while True:
            print(prompt)
            for idx, option in enumerate(options, start=1):
                print(f"[{idx}] {option}")
            raw = input("Select option: ")
            try:
                value = int(raw) - 1
            except ValueError:
                continue
            if 0 <= value < len(options):
                return value

    async def confirm(self, prompt: str) -> bool:
        raw = input(f"{prompt} (y/n): ")
        return raw.strip().lower() in {"y", "yes"}

    async def input_text(self, prompt: str, *, default: str = "") -> str:
        raw = input(f"{prompt} [{default}]: ")
        return raw.strip() or default

    async def notify(self, message: str) -> None:
        print(message)
