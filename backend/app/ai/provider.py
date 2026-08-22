"""AI provider abstraction.

The rest of the codebase depends only on this interface. Supported
providers: OpenAI (OpenAI-compatible APIs), Anthropic (optional), Mock
(deterministic fallback — never invents findings).

Every provider returns raw text; callers validate/parse with Pydantic.
"""

import json
import logging
from abc import ABC, abstractmethod

import httpx

from app.config.settings import settings

logger = logging.getLogger("wisewebai.ai")


class AIError(Exception):
    pass


class AIProvider(ABC):
    name: str = "base"

    @abstractmethod
    async def complete(self, system: str, user: str) -> str:
        """Return the model's text completion for the given messages."""

    def available(self) -> bool:
        return True


class OpenAIProvider(AIProvider):
    """OpenAI-compatible chat completions (works with OpenAI and compatible
    endpoints such as local models via OpenAI base URLs)."""

    name = "openai"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or settings.ai_api_key
        self.model = model or settings.ai_model
        self.base_url = (base_url or settings.ai_openai_base_url).rstrip("/")
        self.timeout = timeout or settings.ai_timeout_seconds

    def available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, system: str, user: str) -> str:
        if not self.available():
            raise AIError("OpenAI provider has no API key configured.")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
            )
            if response.status_code != 200:
                raise AIError(f"AI provider returned HTTP {response.status_code}")
            data = response.json()
            try:
                return data["choices"][0]["message"]["content"]
            except (KeyError, IndexError) as exc:
                raise AIError("Unexpected AI response shape") from exc


class AnthropicProvider(AIProvider):
    """Optional Anthropic provider (Messages API)."""

    name = "anthropic"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        timeout: int | None = None,
    ):
        self.api_key = api_key or settings.ai_api_key
        self.model = model or settings.ai_model
        self.timeout = timeout or settings.ai_timeout_seconds

    def available(self) -> bool:
        return bool(self.api_key)

    async def complete(self, system: str, user: str) -> str:
        if not self.available():
            raise AIError("Anthropic provider has no API key configured.")
        payload = {
            "model": self.model,
            "system": system,
            "messages": [{"role": "user", "content": user}],
            "max_tokens": 4096,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                },
                json=payload,
            )
            if response.status_code != 200:
                raise AIError(f"Anthropic provider returned HTTP {response.status_code}")
            data = response.json()
            try:
                return "".join(
                    block.get("text", "")
                    for block in data.get("content", [])
                    if block.get("type") == "text"
                )
            except (KeyError, TypeError) as exc:
                raise AIError("Unexpected Anthropic response shape") from exc


class MockAIProvider(AIProvider):
    """Deterministic fallback provider.

    Generates structured JSON from the evidence it is given. It never
    invents findings: recommendations are derived from actual findings
    via the recommendation engine, and summaries are template-based on
    real scores.
    """

    name = "mock"

    async def complete(self, system: str, user: str) -> str:
        # The caller is expected to parse JSON; for the mock provider we
        # route through the deterministic generators instead, so this
        # method returns an empty object for unsupported prompts.
        return json.dumps({"root_causes": [], "recommendations": []})


def get_provider(provider_name: str | None = None) -> AIProvider:
    name = (provider_name or settings.ai_provider).lower()
    if name == "openai":
        provider: AIProvider = OpenAIProvider()
        if not provider.available():
            logger.warning("OpenAI provider requested but no API key; using mock provider")
            return MockAIProvider()
        return provider
    if name == "anthropic":
        provider = AnthropicProvider()
        if not provider.available():
            logger.warning("Anthropic provider requested but no API key; using mock provider")
            return MockAIProvider()
        return provider
    return MockAIProvider()
