import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

KNOWLEDGE_DIR = BASE_DIR / "knowledge"
CHROMA_PATH = str(Path(__file__).resolve().parent / ".chroma_store")
KNOWLEDGE_COLLECTION = "fcrm_knowledge"
DB_PATH = Path(__file__).resolve().parent / "workbench.db"

CORS_ORIGINS = [
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]

RETRIEVAL_TOP_K = 5

# Chunking: after splitting on '##' headings, any section longer than
# CHUNK_MAX_WORDS is further split into overlapping word-count windows (see
# backend/rag/chunker.py) so one oversized section never becomes a single
# low-precision chunk. Current knowledge/*.md sections max out around 116
# words, so this ceiling does not change chunk count for the existing
# corpus - it only kicks in for future, longer documents.
CHUNK_MAX_WORDS = 180
CHUNK_OVERLAP_WORDS = 40

# The institution every agent prompt and the scope guardrail is grounded in.
# Baked into system prompts so assessments are scoped to this bank's scale
# and business lines rather than a generic/hypothetical bank.
BANK_PROFILE = (
    "You are supporting the Financial Crimes Risk Management (FCRM) function of a large national "
    "bank with roughly half a trillion dollars in assets, spanning consumer banking, commercial "
    "banking, payments, and wealth management. The bank is closely supervised and examined on how "
    "well it controls financial crime risk."
)

LLM_MAX_TOKENS = 2000
LLM_TIMEOUT_SECONDS = 45.0

# Each provider spec describes how to build an OpenAI-compatible or Anthropic
# HTTP client. Base URL and model are env-overridable so a stub server (for
# tests) or a newer model name never requires a code change.
#
# Default model is a Groq-hosted reasoning model (GPT-OSS 120B). Reasoning
# models spend part of max_tokens on an internal "reasoning" field before
# emitting the actual answer - reasoning_effort="low" keeps enough budget
# left over for the JSON response instead of it being truncated to empty.
_GROQ_BASE_URL = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
_GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

PROVIDER_SPECS = {
    # Groq (groq.com) - OpenAI-compatible fast inference. Three separate
    # keys, one dedicated per child agent, so each independent LLM call uses
    # its own key/rate limit; each is independently optional (missing key ->
    # that slot falls back to the mock, same as any other provider).
    "groq1": {
        "kind": "openai_compat",
        "base_url": _GROQ_BASE_URL,
        "api_key": os.getenv("GROQ_API_KEY_1"),
        "model": _GROQ_MODEL,
        "reasoning_effort": "low",
    },
    "groq2": {
        "kind": "openai_compat",
        "base_url": _GROQ_BASE_URL,
        "api_key": os.getenv("GROQ_API_KEY_2"),
        "model": _GROQ_MODEL,
        "reasoning_effort": "low",
    },
    "groq3": {
        "kind": "openai_compat",
        "base_url": _GROQ_BASE_URL,
        "api_key": os.getenv("GROQ_API_KEY_3"),
        "model": _GROQ_MODEL,
        "reasoning_effort": "low",
    },
    # xAI Grok - kept for future use, currently unused by any slot below.
    "grok": {
        "kind": "openai_compat",
        "base_url": os.getenv("GROK_BASE_URL", "https://api.x.ai/v1"),
        "api_key": os.getenv("GROK_API_KEY") or os.getenv("XAI_API_KEY"),
        "model": os.getenv("GROK_MODEL", "grok-4"),
    },
    "openai": {
        "kind": "openai_compat",
        "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
        "api_key": os.getenv("OPENAI_API_KEY"),
        "model": os.getenv("OPENAI_MODEL", "gpt-5.1"),
    },
    "anthropic": {
        "kind": "anthropic",
        "base_url": os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
        "api_key": os.getenv("ANTHROPIC_API_KEY"),
        "model": os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
    },
}

# Which provider each ensemble slot uses, and the sampling temperature for
# that slot's call. Each of the 3 child agents now runs on Groq (same model)
# with its own dedicated API key/rate limit - what makes them independent is
# each agent's own specialist system prompt (see
# backend/agents/assessor.py:SLOT_SPECIALISTS) plus its own key. master_agent
# and scope_guard run sequentially (not concurrently with the 3 child
# agents), so they safely reuse two of those same keys.
SLOT_PROVIDERS = {
    "agent1": {"provider": "groq1", "temperature": 0.2},
    "agent2": {"provider": "groq2", "temperature": 0.2},
    "agent3": {"provider": "groq3", "temperature": 0.2},
    "master_agent": {"provider": "groq1", "temperature": 0.0},
    "scope_guard": {"provider": "groq2", "temperature": 0.0},
}
