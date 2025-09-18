from __future__ import annotations

import asyncio
import random
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional, Protocol

from legacy_web_mcp.config import Settings, load_settings

TransportCallable = Callable[["LLMRequest"], Awaitable[str]]


@dataclass(slots=True)
class LLMRequest:
    model: str
    prompt: str
    temperature: float = 0.2
    max_tokens: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class LLMResponse:
    provider: str
    model: str
    content: str
    tokens_used: int
    cost_usd: float


@dataclass(slots=True)
class ProviderHealth:
    available: bool = True
    last_error: Optional[str] = None
    total_requests: int = 0
    failed_requests: int = 0

    @property
    def failure_rate(self) -> float:
        if self.total_requests == 0:
            return 0.0
        return self.failed_requests / self.total_requests


class Provider(Protocol):
    name: str

    async def complete(self, request: LLMRequest) -> LLMResponse:
        ...

    def validate(self) -> None:
        ...


class BaseProvider:
    def __init__(self, name: str, api_key: Optional[str], default_model: str, transport: TransportCallable | None = None) -> None:
        self.name = name
        self.api_key = api_key
        self.default_model = default_model
        self._transport = transport

    def validate(self) -> None:
        if not self.api_key:
            raise ValueError(f"Missing API key for provider {self.name}")

    async def complete(self, request: LLMRequest) -> LLMResponse:
        self.validate()
        model = request.model or self.default_model
        text = await self._call_transport(request)
        tokens = self._estimate_tokens(request.prompt, text)
        cost = self._estimate_cost(tokens)
        return LLMResponse(provider=self.name, model=model, content=text, tokens_used=tokens, cost_usd=cost)

    async def _call_transport(self, request: LLMRequest) -> str:
        if self._transport is None:
            await asyncio.sleep(0.05)
            return f"[{self.name}] response for: {request.prompt}"
        return await self._transport(request)

    @staticmethod
    def _estimate_tokens(*parts: str) -> int:
        return sum(len(part.split()) for part in parts) + 5

    def _estimate_cost(self, tokens: int) -> float:
        return round(tokens * 0.00002, 6)


class LLMClient:
    def __init__(self, settings: Settings | None = None, *, max_retries: int = 2, backoff_base: float = 0.2) -> None:
        self.settings = settings or load_settings()
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self.providers: Dict[str, Provider] = {}
        self.order: List[str] = []
        self.health: Dict[str, ProviderHealth] = {}
        self.token_usage: Dict[str, int] = {}

    def register_provider(self, name: str, provider: Provider) -> None:
        self.providers[name] = provider
        if name not in self.order:
            self.order.append(name)
        self.health.setdefault(name, ProviderHealth())
        self.token_usage.setdefault(name, 0)

    def set_order(self, provider_names: Iterable[str]) -> None:
        self.order = [name for name in provider_names if name in self.providers]

    async def generate(self, request: LLMRequest, *, preferred: Iterable[str] | None = None) -> LLMResponse:
        provider_sequence = list(preferred or self.order or self.providers.keys())
        if not provider_sequence:
            raise RuntimeError("No providers registered")

        last_error: Optional[Exception] = None
        for provider_name in provider_sequence:
            provider = self.providers.get(provider_name)
            if provider is None:
                continue
            response = await self._attempt(provider, request)
            if response is not None:
                return response
            last_error = self.health[provider_name].last_error
        raise RuntimeError(f"All providers failed: {last_error}")

    async def _attempt(self, provider: Provider, request: LLMRequest) -> Optional[LLMResponse]:
        health = self.health[provider.name]
        for attempt in range(self.max_retries + 1):
            try:
                health.total_requests += 1
                response = await provider.complete(request)
                self.token_usage[provider.name] += response.tokens_used
                health.available = True
                health.last_error = None
                return response
            except Exception as exc:  # pragma: no cover - defensive but tested via stubs
                health.failed_requests += 1
                health.available = False
                health.last_error = str(exc)
                if attempt < self.max_retries:
                    await asyncio.sleep(self.backoff_base * (2 ** attempt))
                else:
                    return None
        return None

    def validate_providers(self) -> Dict[str, str | None]:
        results: Dict[str, str | None] = {}
        for name, provider in self.providers.items():
            try:
                provider.validate()
                results[name] = None
            except Exception as exc:  # pragma: no cover
                results[name] = str(exc)
        return results

    def provider_health(self) -> Dict[str, ProviderHealth]:
        return self.health


def build_default_client(transport_factory: Dict[str, TransportCallable] | None = None) -> LLMClient:
    settings = load_settings()
    client = LLMClient(settings=settings)
    transports = transport_factory or {}
    client.register_provider(
        "openai",
        BaseProvider(
            name="openai",
            api_key=settings.openai_api_key,
            default_model=settings.step1_model,
            transport=transports.get("openai"),
        ),
    )
    client.register_provider(
        "anthropic",
        BaseProvider(
            name="anthropic",
            api_key=settings.anthropic_api_key,
            default_model=settings.step2_model,
            transport=transports.get("anthropic"),
        ),
    )
    client.register_provider(
        "gemini",
        BaseProvider(
            name="gemini",
            api_key=settings.gemini_api_key,
            default_model=settings.fallback_model,
            transport=transports.get("gemini"),
        ),
    )
    client.set_order(["openai", "anthropic", "gemini"])
    return client
