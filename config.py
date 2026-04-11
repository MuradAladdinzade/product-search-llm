"""
config.py — LLM provider configuration
Switch between Anthropic and OpenAI by changing LLM_PROVIDER below.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Provider switch ───────────────────────────────────────────────────────────
# Options: "anthropic" | "openai"
LLM_PROVIDER = "openai"



# ── Active model tier ─────────────────────────────────────────────────────────
# Anthropic options: "fast" | "smart"
# OpenAI options:    "nano" | "mini" | "smart" | "gpt5-nano" | "gpt5-mini" | "gpt5" | "gpt-5.1-codex-mini"
MODEL_TIER =  "gpt5-mini"


# ── Anthropic ─────────────────────────────────────────────────────────────────
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODELS  = {
    "fast":    "claude-haiku-4-5-20251001",   # fastest, cheapest
    "smart":   "claude-sonnet-4-6",           # smarter, slower
}

# ── OpenAI ────────────────────────────────────────────────────────────────────
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_MODELS  = {
    # GPT-5 family (current flagship)
    "gpt5-nano":  "gpt-5.4-nano",       # fastest & cheapest GPT-5
    "gpt5-mini":   "gpt-5.4-mini-2026-03-17",     # fast, high-volume
    "gpt5":       "gpt-5.4",            # flagship GPT-5
    # GPT-4.1 family (still available, cheaper)
    "nano":       "gpt-4.1-nano",       # fastest & cheapest overall
    "mini":       "gpt-4.1-mini",       # balanced speed/quality
    "smart":      "gpt-4.1",            # most capable GPT-4.1
    "gpt-5.1-codex-mini": "gpt-5.4-pro-2026-03-05"
}



# ── Resolved values (used by app.py) ─────────────────────────────────────────
if LLM_PROVIDER == "anthropic":
    LLM_API_URL = ANTHROPIC_API_URL
    LLM_API_KEY = ANTHROPIC_API_KEY
    LLM_MODEL   = ANTHROPIC_MODELS[MODEL_TIER]
elif LLM_PROVIDER == "openai":
    LLM_API_URL = OPENAI_API_URL
    LLM_API_KEY = OPENAI_API_KEY
    LLM_MODEL   = OPENAI_MODELS[MODEL_TIER]
else:
    raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}. Use 'anthropic' or 'openai'.")

LLM_TIMEOUT = 120.0