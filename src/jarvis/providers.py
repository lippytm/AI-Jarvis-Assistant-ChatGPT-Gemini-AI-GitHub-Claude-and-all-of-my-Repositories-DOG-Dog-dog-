from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from .models import ProviderResponse, Task


class ProviderError(RuntimeError):
    pass


class Provider(ABC):
    name: str

    @abstractmethod
    def configured(self) -> bool: ...

    @abstractmethod
    def complete(self, task: Task, timeout: int) -> ProviderResponse: ...


def _post(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
    try:
        with urlopen(request, timeout=timeout) as response:  # noqa: S310
            return json.loads(response.read().decode())
    except HTTPError as exc:
        detail = exc.read().decode(errors="replace")[:500]
        raise ProviderError(f"Provider returned HTTP {exc.code}: {detail}") from exc
    except (URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise ProviderError(f"Provider request failed: {type(exc).__name__}") from exc


@dataclass
class MockProvider(Provider):
    name: str = "mock"

    def configured(self) -> bool:
        return True

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        del timeout
        return ProviderResponse(task.id, self.name, "mock-v1",
                                f"[Mock Jarvis] Task received and recorded: {task.prompt}")


@dataclass
class OpenAIProvider(Provider):
    name: str = "openai"

    def configured(self) -> bool:
        return bool(os.getenv("OPENAI_API_KEY"))

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        key = os.getenv("OPENAI_API_KEY")
        if not key:
            raise ProviderError("OPENAI_API_KEY is not configured")
        model = os.getenv("OPENAI_MODEL", "gpt-5")
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        data = _post(f"{base}/responses",
                     {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                     {"model": model, "instructions": task.system, "input": task.prompt}, timeout)
        content = data.get("output_text") or "".join(
            part.get("text", "") for item in data.get("output", [])
            for part in item.get("content", []) if part.get("type") == "output_text")
        return ProviderResponse(task.id, self.name, model, content, usage=data.get("usage", {}))


@dataclass
class ChatGPTProvider(OpenAIProvider):
    """Named OpenAI API profile for ChatGPT-oriented workflow steps."""

    name: str = "chatgpt"


@dataclass
class AnthropicProvider(Provider):
    name: str = "anthropic"

    def configured(self) -> bool:
        return bool(os.getenv("ANTHROPIC_API_KEY"))

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        key = os.getenv("ANTHROPIC_API_KEY")
        if not key:
            raise ProviderError("ANTHROPIC_API_KEY is not configured")
        model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")
        base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1").rstrip("/")
        data = _post(f"{base}/messages",
                     {"x-api-key": key, "anthropic-version": "2023-06-01",
                      "Content-Type": "application/json"},
                     {"model": model, "max_tokens": 2048, "system": task.system,
                      "messages": [{"role": "user", "content": task.prompt}]}, timeout)
        content = "".join(x.get("text", "") for x in data.get("content", [])
                          if x.get("type") == "text")
        return ProviderResponse(task.id, self.name, model, content, usage=data.get("usage", {}))


@dataclass
class GeminiProvider(Provider):
    name: str = "gemini"

    def configured(self) -> bool:
        return bool(os.getenv("GEMINI_API_KEY"))

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise ProviderError("GEMINI_API_KEY is not configured")
        model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        data = _post(f"{base}/models/{quote(model)}:generateContent?key={quote(key)}",
                     {"Content-Type": "application/json"},
                     {"systemInstruction": {"parts": [{"text": task.system}]},
                      "contents": [{"role": "user", "parts": [{"text": task.prompt}]}]}, timeout)
        candidates = data.get("candidates", [])
        parts = candidates[0].get("content", {}).get("parts", []) if candidates else []
        return ProviderResponse(task.id, self.name, model,
                                "".join(x.get("text", "") for x in parts),
                                usage=data.get("usageMetadata", {}))


@dataclass
class GeminiJarvisProvider(GeminiProvider):
    """Gemini transport with a dedicated Jarvis workflow identity."""

    name: str = "gemini-jarvis"


@dataclass
class PerplexityProvider(Provider):
    name: str = "perplexity"

    def configured(self) -> bool:
        return bool(os.getenv("PERPLEXITY_API_KEY"))

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        key = os.getenv("PERPLEXITY_API_KEY")
        if not key:
            raise ProviderError("PERPLEXITY_API_KEY is not configured")
        model = os.getenv("PERPLEXITY_MODEL", "sonar-pro")
        base = os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai").rstrip("/")
        data = _post(f"{base}/chat/completions",
                     {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                     {"model": model, "messages": [
                         {"role": "system", "content": task.system},
                         {"role": "user", "content": task.prompt}]}, timeout)
        choices = data.get("choices", [])
        content = choices[0].get("message", {}).get("content", "") if choices else ""
        usage = data.get("usage", {})
        if data.get("citations"):
            usage = {**usage, "citations": data["citations"]}
        return ProviderResponse(task.id, self.name, model, content, usage=usage)


def providers() -> dict[str, Provider]:
    items: list[Provider] = [MockProvider(), OpenAIProvider(), ChatGPTProvider(),
                             AnthropicProvider(), GeminiProvider(), GeminiJarvisProvider(),
                             PerplexityProvider()]
    return {item.name: item for item in items}
