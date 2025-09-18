import asyncio

import pytest

from legacy_web_mcp.config import Settings
from legacy_web_mcp.llm.client import LLMClient, LLMRequest, build_default_client


class StubProvider:
    def __init__(self, name: str, response: str, api_key: str = "key", fail_times: int = 0) -> None:
        self.name = name
        self._response = response
        self.api_key = api_key
        self.default_model = "model"
        self.fail_times = fail_times
        self.calls = 0

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError("missing key")

    async def complete(self, request: LLMRequest):
        if self.calls < self.fail_times:
            self.calls += 1
            raise RuntimeError("temporary failure")
        self.calls += 1
        return type("Resp", (), {
            "provider": self.name,
            "model": request.model or self.default_model,
            "content": self._response,
            "tokens_used": 10,
            "cost_usd": 0.001,
        })


def test_generate_with_retry_and_fallback(monkeypatch):
    settings = Settings(
        openai_api_key="ok",
        anthropic_api_key="ok",
        gemini_api_key="ok",
    )
    client = LLMClient(settings=settings, max_retries=1, backoff_base=0)
    client.register_provider("openai", StubProvider("openai", "hello", fail_times=1))
    client.register_provider("anthropic", StubProvider("anthropic", "fallback"))
    client.set_order(["openai", "anthropic"])

    response = asyncio.run(client.generate(LLMRequest(model="gpt", prompt="Hi")))
    assert response.content in {"hello", "fallback"}
    assert client.token_usage[response.provider] == 10
    health = client.provider_health()
    assert health["openai"].total_requests >= 1


def test_build_default_client_validates(monkeypatch):
    settings = Settings(
        openai_api_key="a",
        anthropic_api_key="b",
        gemini_api_key="c",
    )
    monkeypatch.setattr("legacy_web_mcp.llm.client.load_settings", lambda: settings)
    client = build_default_client()
    results = client.validate_providers()
    assert all(error is None for error in results.values())
