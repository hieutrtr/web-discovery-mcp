import asyncio
import json
from pathlib import Path

from legacy_web_mcp.config import Settings
from legacy_web_mcp.llm.client import BaseProvider, LLMClient, LLMRequest
from legacy_web_mcp.storage import initialize_project
from legacy_web_mcp.workflows.yolo import YoloAnalysisRunner


async def _summary_transport(_: LLMRequest) -> str:
    return json.dumps(
        {
            "purpose": "Summarize",
            "target_users": "Users",
            "business_context": "Context",
            "user_journey": "Journey",
            "navigation_role": "Role",
            "business_logic": "Logic",
            "confidence": 0.9,
        }
    )


async def _feature_transport(_: LLMRequest) -> str:
    return json.dumps(
        {
            "interactive_elements": [
                {"selector": "#cta", "purpose": "click", "details": "Primary action"}
            ],
            "functional_capabilities": ["browse"],
            "api_integrations": [
                {"url": "https://api.example.com", "method": "GET", "description": "Fetch data"}
            ],
            "business_rules": ["rule"],
            "rebuild_requirements": [
                {"priority": "high", "requirement": "Implement API", "dependencies": []}
            ],
            "integration_points": [],
        }
    )


async def _fallback_transport(_: LLMRequest) -> str:
    return json.dumps(
        {
            "interactive_elements": [],
            "functional_capabilities": [],
            "api_integrations": [],
            "business_rules": [],
            "rebuild_requirements": [],
            "integration_points": [],
        }
    )


def _build_client(settings: Settings) -> LLMClient:
    client = LLMClient(settings=settings)
    client.register_provider(
        "openai",
        BaseProvider(
            name="openai",
            api_key=settings.openai_api_key,
            default_model=settings.step1_model,
            transport=_summary_transport,
        ),
    )
    client.register_provider(
        "anthropic",
        BaseProvider(
            name="anthropic",
            api_key=settings.anthropic_api_key,
            default_model=settings.step2_model,
            transport=_feature_transport,
        ),
    )
    client.register_provider(
        "gemini",
        BaseProvider(
            name="gemini",
            api_key=settings.gemini_api_key,
            default_model=settings.fallback_model,
            transport=_fallback_transport,
        ),
    )
    client.set_order(["openai", "anthropic", "gemini"])
    client.set_model_aliases(
        {
            "step1": ("openai", settings.step1_model),
            "step2": ("anthropic", settings.step2_model),
            "fallback": ("gemini", settings.fallback_model),
        }
    )
    return client


def test_yolo_runner_processes_pages(tmp_path: Path) -> None:
    settings = Settings(
        analysis_output_root=str(tmp_path),
        openai_api_key="key",
        anthropic_api_key="key",
        gemini_api_key="key",
        step1_model="gpt-test",
        step2_model="claude-test",
        fallback_model="gemini-test",
    )
    project = initialize_project("https://example.com", base_path=tmp_path, settings=settings)
    urls = ["https://example.com/", "https://example.com/about"]
    html_map = {
        "https://example.com/": "<html><head><title>Home</title></head><body><button id='cta'>Go</button></body></html>",
        "https://example.com/about": "<html><head><title>About</title></head><body><form id='profile'><input name='name'/></form></body></html>",
    }

    async def fetch_html(url: str) -> str:
        return html_map[url]

    client = _build_client(settings)
    runner = YoloAnalysisRunner(
        project=project,
        urls=urls,
        settings=settings,
        llm_client=client,
        fetch_html=fetch_html,
    )

    result = asyncio.run(runner.run())

    assert result.completed == urls
    assert not result.failed
    snapshot = result.snapshot
    assert snapshot.completed == len(urls)
    assert Path(result.artifacts["master_report"]).exists()
    page_file = project.docs_pages_dir / "page-example.com.md"
    assert page_file.exists()
    assert "Legacy Web Analysis Report" in Path(result.artifacts["master_report"]).read_text(encoding="utf-8")


def test_yolo_runner_retries_failures(tmp_path: Path) -> None:
    settings = Settings(
        analysis_output_root=str(tmp_path),
        openai_api_key="key",
        anthropic_api_key="key",
        gemini_api_key="key",
        step1_model="gpt-test",
        step2_model="claude-test",
        fallback_model="gemini-test",
    )
    project = initialize_project("https://example.org", base_path=tmp_path, settings=settings)
    urls = ["https://example.org/page"]
    html_map = {
        urls[0]: "<html><head><title>Page</title></head><body><button id='cta'>Go</button></body></html>",
    }

    async def fetch_html(url: str) -> str:
        return html_map[url]

    summary_attempts = {"count": 0}

    async def failing_summary_transport(_: LLMRequest) -> str:
        summary_attempts["count"] += 1
        if summary_attempts["count"] == 1:
            raise RuntimeError("summary failure")
        return await _summary_transport(_)

    client = LLMClient(settings=settings)
    client.register_provider(
        "openai",
        BaseProvider(
            name="openai",
            api_key=settings.openai_api_key,
            default_model=settings.step1_model,
            transport=failing_summary_transport,
        ),
    )
    client.register_provider(
        "anthropic",
        BaseProvider(
            name="anthropic",
            api_key=settings.anthropic_api_key,
            default_model=settings.step2_model,
            transport=_feature_transport,
        ),
    )
    client.register_provider(
        "gemini",
        BaseProvider(
            name="gemini",
            api_key=settings.gemini_api_key,
            default_model=settings.fallback_model,
            transport=_fallback_transport,
        ),
    )
    client.set_order(["openai", "anthropic", "gemini"])
    client.set_model_aliases(
        {
            "step1": ("openai", settings.step1_model),
            "step2": ("anthropic", settings.step2_model),
            "fallback": ("gemini", settings.fallback_model),
        }
    )

    runner = YoloAnalysisRunner(
        project=project,
        urls=urls,
        settings=settings,
        llm_client=client,
        fetch_html=fetch_html,
    )

    result = asyncio.run(runner.run())

    assert result.completed == urls
    assert not result.failed
    assert summary_attempts["count"] == 2
    assert urls[0] not in result.errors
