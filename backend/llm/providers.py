"""Real HTTP clients for the LLM providers. The only module that talks to a
provider over the network - api keys are read once at import and never leave
this module (logs mention provider names, never keys or raw responses).
"""

import logging

import httpx

from backend.config import LLM_MAX_TOKENS, LLM_TIMEOUT_SECONDS, PROVIDER_SPECS

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=5.0, read=LLM_TIMEOUT_SECONDS, write=10.0, pool=5.0)
_http = httpx.Client(timeout=_TIMEOUT)


class Provider:
    name: str
    model: str

    def available(self) -> bool:
        raise NotImplementedError

    def complete(self, system: str, user: str, temperature: float) -> str:
        raise NotImplementedError


class OpenAICompatProvider(Provider):
    """Covers Grok, OpenAI, and Groq - all speak the same chat/completions shape."""

    def __init__(
        self,
        name: str,
        base_url: str,
        model: str,
        api_key: str | None,
        reasoning_effort: str | None = None,
    ):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key
        self.reasoning_effort = reasoning_effort

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system: str, user: str, temperature: float) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": LLM_MAX_TOKENS,
            "temperature": temperature,
        }
        # Reasoning models (e.g. Groq's GPT-OSS) spend part of max_tokens on
        # an internal reasoning trace before the real answer; capping effort
        # to "low" leaves enough budget for the actual JSON response.
        if self.reasoning_effort:
            payload["reasoning_effort"] = self.reasoning_effort

        resp = _http.post(
            f"{self.base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"]


class AnthropicProvider(Provider):
    def __init__(self, name: str, base_url: str, model: str, api_key: str | None):
        self.name = name
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key

    def available(self) -> bool:
        return bool(self.api_key)

    def complete(self, system: str, user: str, temperature: float) -> str:
        resp = _http.post(
            f"{self.base_url}/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": self.model,
                "max_tokens": LLM_MAX_TOKENS,
                "temperature": temperature,
                "system": system,
                "messages": [{"role": "user", "content": user}],
            },
        )
        resp.raise_for_status()
        data = resp.json()
        # `content` can include non-text (e.g. thinking) blocks, so never
        # assume content[0] is the text block.
        return "".join(
            block.get("text", "") for block in data.get("content", []) if block.get("type") == "text"
        )


class MockProvider(Provider):
    name = "mock"
    model = "mock"

    def available(self) -> bool:
        return True

    def complete(self, system: str, user: str, temperature: float) -> str:
        raise NotImplementedError("MockProvider.complete should never be called directly")


def _build_provider(name: str, spec: dict) -> Provider:
    if spec["kind"] == "anthropic":
        return AnthropicProvider(name, spec["base_url"], spec["model"], spec["api_key"])
    return OpenAICompatProvider(
        name, spec["base_url"], spec["model"], spec["api_key"], spec.get("reasoning_effort")
    )


PROVIDERS: dict[str, Provider] = {name: _build_provider(name, spec) for name, spec in PROVIDER_SPECS.items()}
PROVIDERS["mock"] = MockProvider()


def get_provider(name: str) -> Provider:
    return PROVIDERS[name]


def provider_status() -> list[dict]:
    return [
        {"name": name, "model": provider.model, "configured": provider.available()}
        for name, provider in PROVIDERS.items()
        if name != "mock"
    ]
