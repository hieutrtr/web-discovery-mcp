import asyncio

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
        monthly_budget_usd=0.001,
    )
    client = LLMClient(settings=settings, max_retries=1, backoff_base=0)
    client.register_provider("openai", StubProvider("openai", "hello", fail_times=1))
    client.register_provider("anthropic", StubProvider("anthropic", "fallback"))
    client.set_order(["openai", "anthropic"])
    client.set_model_aliases({"step1": ("openai", "model"), "fallback": ("anthropic", "model")})

    response = asyncio.run(client.generate(LLMRequest(model="step1", prompt="Hi")))
    assert response.content in {"hello", "fallback"}
    assert client.token_usage[response.provider] == 10
    status = client.budget_status()
    assert "total_cost" in status


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


def test_budget_status_exceeded():
    settings = Settings(openai_api_key="ok", anthropic_api_key="ok", gemini_api_key="ok", monthly_budget_usd=0.0001)
    client = LLMClient(settings=settings)
    provider = StubProvider("openai", "resp")
    client.register_provider("openai", provider)
    client.set_model_aliases({"step1": ("openai", "model")})
    asyncio.run(client.generate(LLMRequest(model="step1", prompt="hello")))
    status = client.budget_status()
    assert status["total_cost"] > 0
    assert status["limit"] == 0.0001
    assert status["exceeded"] == (status["total_cost"] > status["limit"])
