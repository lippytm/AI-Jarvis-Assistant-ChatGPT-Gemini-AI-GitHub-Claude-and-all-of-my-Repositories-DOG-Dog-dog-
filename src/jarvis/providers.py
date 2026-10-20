from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from http.client import HTTPException
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

from .models import ProviderResponse, Task


class ProviderError(RuntimeError):
    pass


MAX_RESPONSE_BYTES = 1024 * 1024
MAX_OUTPUT_TOKENS = 2000


def _model(variable: str) -> str:
    value = os.getenv(variable, "")
    if (not value or len(value) > 256
            or any(character.isspace() or ord(character) < 32 or ord(character) == 127
                   for character in value)):
        raise ProviderError(f"{variable} must name a model supported by the configured account and endpoint")
    return value


def _api_key(variable: str) -> str:
    value = os.getenv(variable, "")
    if not value or any(ord(character) < 33 or ord(character) > 126 for character in value):
        raise ProviderError(f"{variable} is missing or invalid")
    return value


def _configured(key_variable: str, model_variable: str) -> bool:
    try:
        _api_key(key_variable)
        _model(model_variable)
    except ProviderError:
        return False
    return True


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


class Provider(ABC):
    name: str

    @abstractmethod
    def configured(self) -> bool: ...

    @abstractmethod
    def complete(self, task: Task, timeout: int) -> ProviderResponse: ...


def _post(url: str, headers: dict[str, str], payload: dict[str, Any], timeout: int) -> dict[str, Any]:
    try:
        request = Request(url, data=json.dumps(payload).encode(), headers=headers, method="POST")
        with build_opener(_RejectRedirects()).open(request, timeout=timeout) as response:  # noqa: S310
            raw = response.read(MAX_RESPONSE_BYTES + 1)
        if len(raw) > MAX_RESPONSE_BYTES:
            raise ProviderError("Provider response exceeded the local pilot limit")
        data = json.loads(raw.decode())
        if not isinstance(data, dict):
            raise ProviderError("Provider response must be a JSON object")
        return data
    except HTTPError as exc:
        exc.close()
        raise ProviderError(f"Provider returned HTTP {exc.code}") from exc
    except (URLError, TimeoutError, HTTPException, OSError, ValueError, TypeError, UnicodeError) as exc:
        raise ProviderError(f"Provider request failed: {type(exc).__name__}") from exc


def _response_text(data: dict[str, Any], family: str) -> str:
    """Require a completed native text result before a workflow may continue."""
    try:
        if data.get("error") or data.get("refusal"):
            raise ProviderError("Provider reported an unsuccessful result")
        if family == "openai":
            if data.get("status") != "completed":
                raise ProviderError("Provider did not return a completed text result")
            for item in data.get("output", []):
                if (item.get("type") == "refusal" or item.get("refusal")
                        or any(part.get("type") == "refusal" or part.get("refusal")
                               for part in item.get("content", []))):
                    raise ProviderError("Provider did not return a completed text result")
            if "output_text" in data:
                content = data["output_text"]
            else:
                content = "".join(
                    part["text"] for item in data["output"] if item.get("type") == "message"
                    for part in item["content"] if part.get("type") == "output_text")
        elif family == "anthropic":
            if (data.get("stop_reason") not in ("end_turn", "stop_sequence")
                    or (data.get("stop_details") or {}).get("type") == "refusal"):
                raise ProviderError("Provider did not return a completed text result")
            content = "".join(part["text"] for part in data["content"]
                              if part.get("type") == "text")
        elif family == "gemini":
            feedback = data.get("promptFeedback") or {}
            candidate = data["candidates"][0]
            if (feedback.get("blockReason") not in (None, "", "BLOCK_REASON_UNSPECIFIED")
                    or candidate.get("finishReason") != "STOP"
                    or any(rating.get("blocked") is True
                           for rating in candidate.get("safetyRatings", [])
                           + feedback.get("safetyRatings", []))):
                raise ProviderError("Provider did not return a completed text result")
            content = "".join(part["text"] for part in candidate["content"]["parts"]
                              if "text" in part and part.get("thought") is not True)
        elif family == "perplexity":
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop" or choice["message"].get("refusal"):
                raise ProviderError("Provider did not return a completed text result")
            content = choice["message"]["content"]
        else:
            raise ProviderError("Unsupported provider response family")
    except (AttributeError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise ProviderError("Provider returned a malformed text result") from exc
    if not isinstance(content, str) or not content.strip():
        raise ProviderError("Provider returned no usable text result")
    return content


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
        return _configured("OPENAI_API_KEY", "OPENAI_MODEL")

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        key = _api_key("OPENAI_API_KEY")
        model = _model("OPENAI_MODEL")
        base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").rstrip("/")
        data = _post(f"{base}/responses",
                     {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                     {"model": model, "instructions": task.system, "input": task.prompt,
                      "max_output_tokens": MAX_OUTPUT_TOKENS}, timeout)
        content = _response_text(data, "openai")
        return ProviderResponse(task.id, self.name, model, content, usage=data.get("usage", {}))


@dataclass
class ChatGPTProvider(OpenAIProvider):
    """Named OpenAI API profile for ChatGPT-oriented workflow steps."""

    name: str = "chatgpt"


@dataclass
class AnthropicProvider(Provider):
    name: str = "anthropic"

    def configured(self) -> bool:
        return _configured("ANTHROPIC_API_KEY", "ANTHROPIC_MODEL")

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        key = _api_key("ANTHROPIC_API_KEY")
        model = _model("ANTHROPIC_MODEL")
        base = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com/v1").rstrip("/")
        data = _post(f"{base}/messages",
                     {"x-api-key": key, "anthropic-version": "2023-06-01",
                      "Content-Type": "application/json"},
                     {"model": model, "max_tokens": MAX_OUTPUT_TOKENS, "system": task.system,
                      "messages": [{"role": "user", "content": task.prompt}]}, timeout)
        content = _response_text(data, "anthropic")
        return ProviderResponse(task.id, self.name, model, content, usage=data.get("usage", {}))


@dataclass
class GeminiProvider(Provider):
    name: str = "gemini"

    def configured(self) -> bool:
        return _configured("GEMINI_API_KEY", "GEMINI_MODEL")

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        key = _api_key("GEMINI_API_KEY")
        model = _model("GEMINI_MODEL")
        base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        data = _post(f"{base}/models/{quote(model)}:generateContent?key={quote(key)}",
                     {"Content-Type": "application/json"},
                     {"systemInstruction": {"parts": [{"text": task.system}]},
                      "contents": [{"role": "user", "parts": [{"text": task.prompt}]}],
                      "generationConfig": {"maxOutputTokens": MAX_OUTPUT_TOKENS}}, timeout)
        return ProviderResponse(task.id, self.name, model,
                                _response_text(data, "gemini"),
                                usage=data.get("usageMetadata", {}))


@dataclass
class GeminiJarvisProvider(GeminiProvider):
    """Gemini transport with a dedicated Jarvis workflow identity."""

    name: str = "gemini-jarvis"


@dataclass
class PerplexityProvider(Provider):
    name: str = "perplexity"

    def configured(self) -> bool:
        return _configured("PERPLEXITY_API_KEY", "PERPLEXITY_MODEL")

    def complete(self, task: Task, timeout: int) -> ProviderResponse:
        key = _api_key("PERPLEXITY_API_KEY")
        model = _model("PERPLEXITY_MODEL")
        base = os.getenv("PERPLEXITY_BASE_URL", "https://api.perplexity.ai").rstrip("/")
        data = _post(f"{base}/chat/completions",
                     {"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                     {"model": model, "max_tokens": MAX_OUTPUT_TOKENS, "messages": [
                         {"role": "system", "content": task.system},
                         {"role": "user", "content": task.prompt}]}, timeout)
        content = _response_text(data, "perplexity")
        usage = data.get("usage", {})
        if data.get("citations"):
            usage = {**usage, "citations": data["citations"]}
        return ProviderResponse(task.id, self.name, model, content, usage=usage)


def providers() -> dict[str, Provider]:
    items: list[Provider] = [MockProvider(), OpenAIProvider(), ChatGPTProvider(),
                             AnthropicProvider(), GeminiProvider(), GeminiJarvisProvider(),
                             PerplexityProvider()]
    return {item.name: item for item in items}
