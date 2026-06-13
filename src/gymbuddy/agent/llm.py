"""Groq LLM wrapper — free-tier friendly.

Provides:
  - chat(messages, tools=...) → raw Groq response (supports function calling)
  - complete(prompt) → str
Caching: identical requests are memoized on disk (diskcache) so re-runs during
development don't burn rate limits.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from gymbuddy.config import settings

_client = None
_cache = None


def _get_client():
    global _client
    if _client is None:
        from groq import Groq  # lazy import

        _client = Groq(api_key=settings.groq_api_key)
    return _client


def _get_cache():
    global _cache
    if _cache is None:
        import diskcache  # lazy import

        _cache = diskcache.Cache(str(Path(settings.data_dir) / "cache" / "llm"))
    return _cache


def _key(payload: dict[str, Any]) -> str:
    blob = json.dumps(payload, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode()).hexdigest()


def chat(
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    tool_choice: str = "auto",
    temperature: float = 0.2,
    max_tokens: int = 1024,
    use_cache: bool = True,
) -> Any:
    """Call Groq chat completions. Returns the raw message object (which may
    contain tool_calls). Tool-call responses are not cached (they're cheap and
    state-dependent); plain completions are.
    """
    payload = {
        "model": settings.groq_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice

    cacheable = use_cache and not tools
    if cacheable:
        ck = _key(payload)
        cached = _get_cache().get(ck)
        if cached is not None:
            return cached

    resp = _get_client().chat.completions.create(**payload)
    msg = resp.choices[0].message

    if cacheable:
        _get_cache().set(ck, msg)
    return msg


def complete(prompt: str, system: str | None = None, **kw: Any) -> str:
    messages: list[dict[str, Any]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    msg = chat(messages, **kw)
    return (msg.content or "").strip()
