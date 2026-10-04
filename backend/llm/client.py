"""The single seam agents call through. Mirrors the original mock_llm.py
design: agents never talk to a provider directly, so swapping models or
adding fallback behavior happens in one place.
"""

import json
import logging
import re
from typing import Callable

import httpx

from backend.config import SLOT_PROVIDERS
from backend.llm.providers import get_provider
from backend.models import LLMResult

logger = logging.getLogger(__name__)

_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*|\s*```")


def extract_json(text: str) -> dict | None:
    cleaned = _JSON_FENCE_RE.sub("", text).strip()
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None
    try:
        return json.loads(cleaned[start : end + 1])
    except json.JSONDecodeError:
        return None


def complete(slot: str, system: str, user: str, mock_fn: Callable[[], str]) -> LLMResult:
    """Try the slot's assigned provider; fall back to the deterministic mock
    on missing key, network error, or timeout - the pipeline must never break
    because a provider call failed.
    """
    spec = SLOT_PROVIDERS[slot]
    provider = get_provider(spec["provider"])

    if provider.available():
        try:
            text = provider.complete(system, user, spec["temperature"])
            return LLMResult(text=text, provider=provider.name, model=provider.model, mode="live")
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.warning("Provider %s failed for slot %s (%s); falling back to mock", provider.name, slot, exc)

    return LLMResult(text=mock_fn(), provider="mock", model="mock", mode="mock")
