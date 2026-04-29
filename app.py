"""
app.py — Production-ready single API
Run: uvicorn app:app --host 0.0.0.0 --port 8000

Single endpoint: GET /parse?text=...
  1. LLM extracts products from raw text
  2. SIM type resolved in Python (iPhones only)
  3. DB queried for color candidates (iPhones only)
  4. LLM picks best color match (iPhones only)
  Returns flat JSON array of enriched products.
"""


import asyncio
import json
import logging
import os
import sys
from contextlib import asynccontextmanager
from typing import Optional

import asyncpg
import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel, field_validator

from sim_rules import SimCardType, resolve_sim_type
from color_overrides import OVERRIDES as COLOR_OVERRIDES

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# ── CONFIG — adjust these values ─────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# LLM provider — configure in config.py (switch between Anthropic and OpenAI)
from config import LLM_PROVIDER, LLM_API_URL, LLM_API_KEY, LLM_MODEL, LLM_TIMEOUT

# Postgres
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
    f"/{os.getenv('DB_NAME')}"
)
DB_POOL_MIN  = 2    # min connections in pool
DB_POOL_MAX  = 10   # max connections in pool

# DB query — adjust table/column names to match your schema
# DB query — adjust table/column names to match your schema
DB_TABLE              = "public.products"
DB_COL_PRODUCT_LINE   = "product_type"
DB_COL_MODEL_NAME     = "model"
DB_COL_CATEGORY       = "category"
DB_COL_STORAGE        = "size"
DB_COL_COUNTRY        = "country_code"
DB_COL_SIM_TYPE       = "sim_card_type"
DB_COL_COLOR          = "color"

# ══════════════════════════════════════════════════════════════════════════════


# ── Logging ───────────────────────────────────────────────────────────────────

from datetime import datetime as _dt

def _ts() -> str:
    return _dt.now().strftime("%Y-%m-%d %H:%M:%S")

_uvicorn_logger = logging.getLogger("uvicorn.error")
_uvicorn_logger.setLevel(logging.INFO)

class _Logger:
    def info(self, msg, *args):
        _uvicorn_logger.info(f"[{_ts()}] " + (msg % args if args else msg))
    def warning(self, msg, *args):
        _uvicorn_logger.warning(f"[{_ts()}] " + (msg % args if args else msg))
    def error(self, msg, *args):
        _uvicorn_logger.error(f"[{_ts()}] " + (msg % args if args else msg))

logger = _Logger()

logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)


# ── Pydantic models ───────────────────────────────────────────────────────────

class EnrichedProduct(BaseModel):
    # Core fields (matches legacy format)
    productName:      Optional[str] = None
    model:            Optional[str] = None
    size:             Optional[str] = None
    color_from_text: Optional[str] = None
    # Order info
    quantity:         int           = 1
    price:            float         = 0.0
    requestedText:    str
    countryCode:      Optional[str] = None
    # SIM (iPhones only)
    simType:          Optional[SimCardType] = None
    simConflict:      bool          = False
    # LLM extracted fields
    brand:        Optional[str] = None
    product_type:     Optional[str] = None
    category:     Optional[str] = None
    variant:      Optional[str] = None
    model_code:   Optional[str] = None
    ram:          Optional[str] = None
    LLM_color_en:     Optional[str] = None
    prod_year:         Optional[str] = None
    # Color match (iPhones only)
    matched_color:    Optional[str] = None


# ── Step 1 prompt ─────────────────────────────────────────────────────────────

EXTRACT_PROMPT = """You are a product extraction assistant. Follow ALL instructions carefully and precisely.

=== STEP 1 — THINK FIRST (do NOT output this) ===
Before writing any JSON, mentally identify:
1. How many real products are in the text?
2. What raw text belongs to each product?
3. Is each segment actually a real product listing, or just a note/comment/instruction?
   - Real product: has a recognizable product name, model, or SKU (e.g. "17 Pro 256GB Black 54000")
   - NOT a product: conversational notes, instructions, prices alone, Russian words like "отложи"/"хорошо"/"привет"/"берём"/"го"/"ок", standalone numbers without context

=== STEP 2 — OUTPUT ===
Return ONLY a JSON array. Response MUST start with "[" and end with "]". No explanations, no markdown, no preamble.
Every object MUST have ALL fields listed below in EXACTLY this order. Never omit a field. Use null if not determinable.

=== FIELD DEFINITIONS (use this exact order in every object) ===
{
  "is_real_product":  true,   // boolean — true if this is a real product listing, false if it is a note/comment/instruction/non-product text
  "productName":      "...",  // Full constructed name: brand + line + model + storage + color. e.g. "iPhone 17 256GB Black" | null if not a real product
  "model":            "...",  // iPhone: "16+" → "16 Plus" | "17" | "16 Pro" | "17 Pro Max" | "17 Air" | "17e" | "13 Mini" | "14 Plus" | iPad: "Mini 7" | "Air" | "Pro 13" | Other: "A56" | "S25 Ultra" | "Pro 14" | "Forerunner 55" | null if not determinable
  "size":             "...",  // Storage as <N>GB or <N>TB | null if not determinable
  "color_from_text":  "...",  // Raw color EXACTLY as user wrote it, any language — do NOT translate or normalize | null if not mentioned
  "quantity":         1,      // Positive integer, default 1, Cannot be Negative Number or Zero. If quantity is not mentioned, default to 1. If quantity is mentioned as part of a price (e.g. "31.5x4"), extract it and use it here, but do NOT modify the price field (keep it as the full price, e.g. "31.5x4" → quantity: 4, price: 31500). If quantity is preceded by a "-", don't include quantity as negative, just extract the number (e.g. "72600-2" → quantity: 2, price: 72600).
  "price":            0,      // Float, default 0
  "requestedText":    "...",  // Exact raw text the user wrote for this segment — do NOT strip or modify anything (keep typos, Russian words, emojis, spacing exactly as written)
  "countryCode":      null,   // 2-letter ISO code ONLY if flag/country explicitly in this segment (e.g. "🇺🇸"→"US", "🇮🇳"→"IN", "🇨🇳"→"CN") | null if not mentioned | if multiple countries, take the first
  "brand":            "...",  // Apple | Samsung | Garmin | Poco | Dyson | Sony | etc. | null if not a real product
  "product_type":     "...",  // iPhone | MacBook | iPad | Galaxy | Watch | Forerunner | etc. | null if not a real product
  "category":         "...",  // phone | laptop | tablet | watch | earbuds | accessory | other | null if not a real product
  "variant":          "...",  // Pro | Plus | Ultra | Mini | Air | Max | SE | e | null
  "model_code":       "...",  // SKU code: "MW2X3" | "SM-A520F" | null
  "ram":              "...",  // RAM only if separate from storage: "8GB" | null
  "LLM_color_en":     "...",  // Color translated/normalized to English: "белый"→"White" | "синий"→"Blue" | null if no color
  "prod_year":        "...",  // Year if mentioned: "2024" | null
  "simType":          null    // iPhone only — extract ONLY if explicitly stated in text:
                              //   "sim+esim"/"esim+sim"/"sim-esim"/"esim-sim"/"sim/esim"/"1sim"+"esim"/"сим"+"есим" → "PHYSICAL_PLUS_ESIM"
                              //   "1sim"/"1сим"/"1 sim"/"1 сим" alone → "PHYSICAL_PLUS_ESIM"
                              //   if "sim" and "esim" mentioned together in any format → "PHYSICAL_PLUS_ESIM"
                              //   "esim"/"есим"/"только esim" alone → "ESIM_ONLY_SINGLE"
                              //   "E-sim"/"e-sim"/"(E-sim)"/"Dual Esim"/"dual esim"/"2esim"/"2 esim" alone → "ESIM_ONLY_SINGLE"
                              //   "iPhone 17 Air" / "Айфон 17 Эйр" / "iPhone Air" → "ESIM_ONLY_SINGLE"
                              //   "2sim"/"2сим"/"2 sim"/"2 сим"/"dual sim"/"двойной сим"/"два сим" → "PHYSICAL_DUAL"
                              //   any other sim mention → "PHYSICAL_PLUS_ESIM"
                              //   nothing mentioned → "PHYSICAL_PLUS_ESIM"
                              //   always null for non-iPhones
}

=== QUANTITY ===
Default 1. x2 / 2шт / 35600-2 (price-qty) / 31.5x4 (price 31500, qty 4)
"green-2" = color green qty 2. "72600-2" = price 72600 qty 2.

=== PRICE ===
Default 0. "35,3"→35300 / "31.5x4"→price 31500 qty 4 / "3500 дают 3400"→3400
If multiple prices appear, take the lowest one. e.g. "54500 1шт ? 54700" → price: 54500

=== REQUESTEDTEXT ===
Keep exactly as the user wrote it — do NOT strip, clean, or modify anything.
Copy the raw text for this segment as-is, including typos, Russian words, emojis, spacing.

=== VARIANT ===
model→variant: variant should contain non-numeric part of model
"16 Pro"→"Pro" | "55"→null | "13 Mini"→"Mini" | "14 Plus"→"Plus" | "15 Pro Max"→"Pro Max" | "17e"→"e" | "S25 Ultra"→"Ultra" | "16e"→"e"

=== MODEL RULES ===
16E ≠ 16 (model: "16E"). PRO→Pro, PLUS→Plus, MAX→Max. N+→"N Plus": 15+→"15 Plus" | 16+→"16 Plus" | 17+→"17 Plus".
iPhone 16Max → model: "16 Pro Max", variant: "Pro Max", not "16 Max". iPhone never releases a "Max" variant without "Pro". If "Max" is mentioned → always assume "Pro Max".
"Air" alone → iPhone 17 Air (product_type: "iPhone", model: "17 Air").
"Air 7"/"iPad Air" → iPad (product_type: "iPad", model: null).
Samsung: "Galaxy A5 SM-A520F 3GB/32GB" → model:"A5", model_code:"SM-A520F", ram:"3GB", size:"32GB"

=== FIELD NOTES ===
- model: human-readable model id — "16 Pro" | "A5" | "Pro 14" | "Forerunner 55" | null if not determinable
- model_code: hardware SKU only — "SM-A520F" | "MW2X3" | "MH9J4" | null if not present. Always separate from model.
- size: storage only — "128GB" | "1TB". Never put RAM here.
- ram: RAM only if explicitly separate from storage — "8GB" | null

=== EXAMPLES ===
Input: "iPad Mini 7 128GB Space Gray Wi-Fi MXN63 35700"
[{"is_real_product":true,"productName":"iPad Mini 7 128GB Space Gray Wi-Fi MXN63","model":"Mini 7","size":"128GB","color_from_text":"Space Gray","quantity":1,"price":35700,"requestedText":"iPad Mini 7 128GB Space Gray Wi-Fi MXN63 35700","countryCode":null,"brand":"Apple","product_type":"iPad","category":"tablet","variant":"Mini","model_code":"MXN63","ram":null,"LLM_color_en":"Space Gray","prod_year":null,"simType":null}]

Input: "Pencil Pro 2025 MX2D3 8500"
[{"is_real_product":true,"productName":"Apple Pencil Pro 2025","model":null,"size":null,"color_from_text":null,"quantity":1,"price":8500,"requestedText":"Pencil Pro 2025 MX2D3 8500","countryCode":null,"brand":"Apple","product_type":"Pencil","category":"accessory","variant":"Pro","model_code":"MX2D3","ram":null,"LLM_color_en":null,"prod_year":"2025","simType":null}]

Input: "16 Pro 256 Black 🇮🇳 54000"
[{"is_real_product":true,"productName":"iPhone 16 Pro 256GB Black","model":"16 Pro","size":"256GB","color_from_text":"Black","quantity":1,"price":54000,"requestedText":"16 Pro 256 Black 🇮🇳 54000","countryCode":"IN","brand":"Apple","product_type":"iPhone","category":"phone","variant":"Pro","model_code":null,"ram":null,"LLM_color_en":"Black","prod_year":null,"simType":null}]

Input: "17 Pro Max 1024 ГБ серебристый eSIM : 1 132 17 Pro Max 1024 ГБ синий eSIM : 1 126,8"
[{"is_real_product":true,"productName":"iPhone 17 Pro Max 1024GB Silver","model":"17 Pro Max","size":"1024GB","color_from_text":"серебристый","quantity":1,"price":132000,"requestedText":"17 Pro Max 1024 ГБ серебристый eSIM : 1 132","countryCode":null,"brand":"Apple","product_type":"iPhone","category":"phone","variant":"Pro Max","model_code":null,"ram":null,"LLM_color_en":"Silver","prod_year":null,"simType":"ESIM_ONLY_SINGLE"},{"is_real_product":true,"productName":"iPhone 17 Pro Max 1024GB Blue","model":"17 Pro Max","size":"1024GB","color_from_text":"синий","quantity":1,"price":126800,"requestedText":"17 Pro Max 1024 ГБ синий eSIM : 1 126,8","countryCode":null,"brand":"Apple","product_type":"iPhone","category":"phone","variant":"Pro Max","model_code":null,"ram":null,"LLM_color_en":"Blue","prod_year":null,"simType":"ESIM_ONLY_SINGLE"}]

Input: "iPhone 17 256gb Black sim+esim\n65 отложи"
[{"is_real_product":true,"productName":"iPhone 17 256GB Black","model":"17","size":"256GB","color_from_text":"Black","quantity":1,"price":0,"requestedText":"iPhone 17 256gb Black sim+esim","countryCode":null,"brand":"Apple","product_type":"iPhone","category":"phone","variant":null,"model_code":null,"ram":null,"LLM_color_en":"Black","prod_year":null,"simType":"PHYSICAL_PLUS_ESIM"},{"is_real_product":false,"productName":null,"model":null,"size":null,"color_from_text":null,"quantity":1,"price":0,"requestedText":"65 отложи","countryCode":null,"brand":null,"product_type":null,"category":null,"variant":null,"model_code":null,"ram":null,"LLM_color_en":null,"prod_year":null,"simType":null}]
"""

# ── Step 2 color prompt ───────────────────────────────────────────────────────

COLOR_PROMPT = """\
You are a color matcher. Given the user's requested color and a list of available DB colors, pick the closest match.

Return ONLY: {"matched_color": "..."}
- matched_color must be copied exactly from available_colors
- Always return the closest match, never null
- Translate user color to English first: "белый"→White | "чёрный"→Black | "синий"→Blue | "серый"→Gray | "розовый"→Pink | "зелёный"→Green | "фиолетовый"→Purple
- Always return the closest match, never null
- Partial ok: "black" → "Black Titanium" | "midnight" → "Midnight Black" | "белый" → "White Titanium"
- White looks like "startlight" or "silver"
- Black looks like "midnight" or "space black"
"""


# ── LLM helpers ───────────────────────────────────────────────────────────────

def _parse_json_array(raw: str) -> list[dict]:
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()
    start, end = raw.find("["), raw.rfind("]")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON array in response: {raw}")
    return json.loads(raw[start : end + 1])


async def _llm_call(system: str, user: str, max_tokens: int = 8192, cache: bool = False) -> str:
    """
    Call the configured LLM provider (Anthropic or OpenAI).
    Retries on 429/503/529 with exponential backoff.
    """
    for attempt in range(4):
        try:
            return await _llm_call_inner(system, user, max_tokens, cache)
        except httpx.HTTPStatusError as e:
            if e.response.status_code in (429, 503, 529) and attempt < 3:
                wait = 10 * (attempt + 1)
                await asyncio.sleep(wait)
                continue
            raise
    raise RuntimeError("LLM call failed after 4 attempts")


async def _llm_call_inner(system: str, user: str, max_tokens: int = 8192, cache: bool = False) -> str:
    """Single attempt LLM call."""
    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:

        if LLM_PROVIDER == "anthropic":
            system_block = (
                [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
                if cache else system
            )
            resp = await client.post(
                LLM_API_URL,
                headers={
                    "Content-Type":      "application/json; charset=utf-8",
                    "x-api-key":         LLM_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "anthropic-beta":    "prompt-caching-2024-07-31",
                },
                json={
                    "model":      LLM_MODEL,
                    "max_tokens": max_tokens,
                    "system":     system_block,
                    "messages":   [{"role": "user", "content": user}],
                },
            )
            resp.raise_for_status()
            data  = resp.json()
            usage = data.get("usage", {})
            return data["content"][0]["text"].strip()

        elif LLM_PROVIDER == "openai":
            # GPT-5.4 family requires /v1/responses endpoint
            # GPT-4.1 family uses /v1/chat/completions
            is_gpt5 = LLM_MODEL.startswith("gpt-5")
            headers = {
                "Content-Type":  "application/json; charset=utf-8",
                "Authorization": f"Bearer {LLM_API_KEY}",
            }
            if is_gpt5:
                url  = "https://api.openai.com/v1/responses"
                body = {
                    "model": LLM_MODEL,
                    "input": [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                    "max_output_tokens": max_tokens,
                    # "service_tier": "priority",  # Add this line to use the priority tier for faster responses
                }
            else:
                url  = LLM_API_URL
                body = {
                    "model":      LLM_MODEL,
                    "max_tokens": max_tokens,
                    "messages":   [
                        {"role": "system", "content": system},
                        {"role": "user",   "content": user},
                    ],
                }
            resp = await client.post(url, headers=headers, json=body)
            resp.raise_for_status()
            data  = resp.json()
            usage = data.get("usage", {})
            if is_gpt5:
                # Responses API returns output as a list of content blocks
                return data["output"][-1]["content"][0]["text"].strip()
            else:
                return data["choices"][0]["message"]["content"].strip()

        else:
            raise ValueError(f"Unknown LLM_PROVIDER: {LLM_PROVIDER!r}")


# ── DB helpers ────────────────────────────────────────────────────────────────

async def fetch_official_colors(
    pool: asyncpg.Pool,
    model_name: Optional[str],
) -> list[str]:
    """Query public.products for official color names for this model."""
    if not model_name:
        return []
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT DISTINCT color
            FROM   public.products
            WHERE  "model" = $1
              AND  color IS NOT NULL
              AND product_type ILIKE 'iPhone'
              AND category ILIKE 'phone'
        """, model_name)
    return [r["color"] for r in rows]


# ── Core pipeline steps ───────────────────────────────────────────────────────

REQUIRED_FIELDS = ("model", "quantity", "price", "requestedText")  # kept for backward compat

# Required fields by product type — used for retry validation
IPHONE_REQUIRED     = ("model", "quantity", "price", "requestedText")
NON_IPHONE_REQUIRED = ("quantity", "price", "requestedText")

# Final drop required fields — checked after productName fallback is applied
IPHONE_FINAL_REQUIRED     = ("model", "quantity", "price", "requestedText")
NON_IPHONE_FINAL_REQUIRED = ("quantity", "price", "requestedText", "productName")


def _is_iphone_dict(p: dict) -> bool:
    """Check if a raw dict is an iPhone product."""
    return (
        (p.get("brand") or "").lower() == "apple"
        and "iphone" in (p.get("product_type") or "").lower()
        and (p.get("category") or "").lower() == "phone"
    )


def _missing_required_single(p: dict) -> list[str]:
    """Return list of null required fields for a single product dict (type-aware)."""
    fields = IPHONE_REQUIRED if _is_iphone_dict(p) else NON_IPHONE_REQUIRED
    return [f for f in fields if p.get(f) is None]


async def _extract_single(requested_text: str, is_iphone: bool, max_attempts: int) -> dict:
    """
    Retry extraction for a single product by its requestedText.
    Returns the best result after all attempts.
    """
    fields = IPHONE_REQUIRED if is_iphone else NON_IPHONE_REQUIRED
    best = None
    for attempt in range(max_attempts):
        raw = await _llm_call(EXTRACT_PROMPT, requested_text, max_tokens=1024, cache=False)
        logger.info("── STEP 1 retry (attempt %d/%d) for %r ──\n%s", attempt + 1, max_attempts, requested_text[:60], raw)
        try:
            results = _parse_json_array(raw)
            if not results:
                await asyncio.sleep(0.5)
                continue
            p = results[0]
            nulls = [f for f in fields if p.get(f) is None]
            if not nulls:
                return p
            best = p
            logger.warning("Retry attempt %d/%d — still null fields %s for %r", attempt + 1, max_attempts, nulls, requested_text[:60])
            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5)
        except Exception as e:
            logger.warning("Retry attempt %d/%d failed: %s", attempt + 1, max_attempts, e)
            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5)
    return best or {}


async def step1_extract(text: str) -> list[dict]:
    """
    Extract structured products from raw order text.
    1. First call: full text → get all products with is_real_product flag
    2. Non-real products → dropped immediately, no retry
    3. Real products with null required fields → retried individually by requestedText
    4. Order preserved by Python, not LLM
    """
    max_attempts = 5

    # ── First pass: full text ─────────────────────────────────────────────────
    # Estimate output tokens: each non-empty line ≈ 1 product ≈ 300 tokens
    _lines = [l for l in text.splitlines() if l.strip()]
    
    _estimated = max(len(_lines), len(text) // 60)
    _max_tokens = max(8192, min(96000, _estimated * 350))

    first_result = []
    for attempt in range(max_attempts):
        raw = await _llm_call(EXTRACT_PROMPT, text, max_tokens=_max_tokens, cache=True)
        logger.info("── STEP 1 LLM raw (attempt %d) ──\n%s", attempt + 1, raw)
        try:
            first_result = _parse_json_array(raw)
            if not first_result:
                if len(raw) > 10:
                    return []  # LLM is confident there are no products
                await asyncio.sleep(0.5)
                continue
            break  # got a parseable result
        except Exception as e:
            if attempt < max_attempts - 1:
                await asyncio.sleep(0.5)
                continue
            raise

    if not first_result:
        return []

    # ── Per-product processing: preserve original order ───────────────────────
    final_results = []
    retry_tasks = []  # (original_index, product) pairs needing retry

    for i, p in enumerate(first_result):
        is_real = p.get("is_real_product", True)  # default True if field missing

        if not is_real:
            logger.info("Skipping non-real product at index %d: requestedText=%r", i, p.get("requestedText", "")[:60])
            continue  # drop, no retry

        nulls = _missing_required_single(p)
        if not nulls:
            final_results.append((i, p))  # good, keep as-is
        else:
            logger.warning("Real product[%d] has null required fields %s — will retry individually", i, nulls)
            retry_tasks.append((i, p))

    # ── Retry individually for real products with missing fields ──────────────
    if retry_tasks:
        retried = await asyncio.gather(*[
            _extract_single(
                p.get("requestedText") or text,
                is_iphone=_is_iphone_dict(p),
                max_attempts=3 if _is_iphone_dict(p) else 2,
            )
            for _, p in retry_tasks
        ])
        for (i, _), retried_p in zip(retry_tasks, retried):
            if retried_p:
                final_results.append((i, retried_p))
            else:
                logger.warning("Retry failed for product[%d], dropping", i)

    # ── Sort by original index to preserve order ──────────────────────────────
    final_results.sort(key=lambda x: x[0])
    return [p for _, p in final_results]


async def step2_match_color(
    pool: asyncpg.Pool,
    model_name: Optional[str],
    requested_text: str,
    color_en: Optional[str],
) -> Optional[str]:
    """
    1. Check OVERRIDES dict (instant, no API call)
    2. Query products table + LLM picks best match
    """
    if not color_en and not requested_text:
        return None

    model_key = (model_name or "").strip().lower()
    color_key = (color_en or "").strip().lower()

    override = COLOR_OVERRIDES.get((model_key, color_key))
    if override:
            return override

    official_colors = await fetch_official_colors(pool, model_name)
    if not official_colors:
        return None

    user_msg = json.dumps({
        "requested_text":     requested_text,
        "user_color_english": color_en,
        "available_colors":   official_colors,
    }, ensure_ascii=False)

    for attempt in range(3):
        try:
            raw = await _llm_call(COLOR_PROMPT, user_msg, max_tokens=64)
            break
        except Exception as e:
            if "429" in str(e) and attempt < 2:
                wait = 10 * (attempt + 1)
                await asyncio.sleep(wait)
            else:
                raise
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        return None
    matched_color = json.loads(raw[start:end+1]).get("matched_color")
    logger.info("── STEP 2 color match ── model=%r requested=%r color_en=%r → matched=%r",
        model_name, requested_text, color_en, matched_color)
    return matched_color


def _is_iphone(product: dict) -> bool:
    brand    = (product.get("brand") or "").lower()
    line     = (product.get("product_type") or "").lower()
    category = (product.get("category") or "").lower()
    return brand == "apple" and "iphone" in line and category == "phone"


# ── FastAPI app ───────────────────────────────────────────────────────────────

_pool: Optional[asyncpg.Pool] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Apply timestamp format to uvicorn.error handlers (runs per worker)
    _fmt = logging.Formatter("%(asctime)s %(levelname)s — %(message)s")
    for _h in logging.getLogger("uvicorn.error").handlers:
        _h.setFormatter(_fmt)
    for _h in logging.getLogger("uvicorn.access").handlers:
        _h.setFormatter(logging.Formatter('%(asctime)s %(levelname)s — %(message)s'))
    global _pool
    logger.info("Starting app worker pid=%s", os.getpid())
    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=DB_POOL_MIN,
        max_size=DB_POOL_MAX,
        server_settings={"client_encoding": "UTF8"},
    )
    logger.info("DB pool created pid=%s", os.getpid())
    yield
    logger.info("Shutting down worker pid=%s", os.getpid())
    await _pool.close()


app = FastAPI(title="Product Parser", version="1.0.0", lifespan=lifespan)


@app.get("/parse", response_model=list[EnrichedProduct])
async def parse(
    text: str = Query(..., description="Raw order text, may be multi-line"),
):
    """
    Full pipeline in one call:
      Step 1 — LLM extracts products from raw text
      Step 2 — SIM rules applied (iPhones only)
      Step 3 — DB color match via LLM (iPhones only, runs concurrently)

    Returns a flat JSON array of enriched products.
    """
    if not text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    _t0 = asyncio.get_event_loop().time()
    logger.info("\n" + "="*80)
    logger.info("── REQUEST ── %r", text)

    # ── Step 1: extract ───────────────────────────────────────────────────────
    try:
        raw_products = await step1_extract(text)
    except Exception as e:
        logger.error("Step 1 failed after all retries: %s", e)
        # Return one fallback product per non-empty line instead of crashing
        fallback = [
            EnrichedProduct(requestedText=line).model_dump()
            for line in text.splitlines()
            if line.strip()
        ] or [EnrichedProduct(requestedText=text).model_dump()]
        return [EnrichedProduct.model_validate(r) for r in fallback]

    logger.info("── STEP 1 parsed ── %d product(s):\n%s", len(raw_products), json.dumps(raw_products, ensure_ascii=False, indent=2))


    # If LLM returned empty, return one fallback product per line
    if not raw_products:
        raw_products = [
            {"requestedText": line}
            for line in text.splitlines()
            if line.strip()
        ] or [{"requestedText": text}]

    # ── Filter: normalize size, strip internal fields, drop products missing required fields ─
    _GB_TO_TB = {"1024GB": "1TB", "2048GB": "2TB"}
    valid_products, dropped = [], []
    for raw in raw_products:
        # Normalize size
        if raw.get("size") in _GB_TO_TB:
            raw["size"] = _GB_TO_TB[raw["size"]]
        # Strip is_real_product — internal field, never exposed in API response
        raw.pop("is_real_product", None)
        # Build productName fallback for non-iPhones before validation
        if not _is_iphone_dict(raw) and not raw.get("productName"):
            parts = [raw.get("product_type"), raw.get("model"), raw.get("size"), raw.get("color_from_text")]
            raw["productName"] = " ".join(p for p in parts if p) or None
        # Validate required fields (type-aware)
        final_required = IPHONE_FINAL_REQUIRED if _is_iphone_dict(raw) else NON_IPHONE_FINAL_REQUIRED
        nulls = [f for f in final_required if raw.get(f) is None]
        if nulls:
            logger.warning("Dropping product with null required fields %s: %r", nulls, raw)
            dropped.append(raw)
        else:
            valid_products.append(raw)

    if dropped and not valid_products:
        # Every product was invalid — return empty list rather than crash
        logger.error("All %d products dropped due to null required fields", len(dropped))
        return []

    raw_products = valid_products

    # ── Step 2: SIM + color match concurrently ────────────────────────────────
    async def enrich(raw: dict) -> EnrichedProduct:
        # Pydantic validation + field coercion
        p = EnrichedProduct.model_validate(raw)

        # Resolve SIM type (iPhones only)
        if _is_iphone(raw):
            # Pass LLM-extracted simType as the explicit indicator to resolve_sim_type
            # so it is used when no country code is present
            sim = resolve_sim_type(
                product_type="iPhone",
                model=p.model,
                country_code=p.countryCode,
                requested_text=p.requestedText,
                llm_sim_type=p.simType,  # LLM-extracted value from Step 1
            )
            p.simType     = sim["simType"]
            p.simConflict = sim["simConflict"]

            # Color match from DB
            try:
                p.matched_color = await step2_match_color(
                    _pool,
                    p.model,
                    p.requestedText,
                    p.LLM_color_en,
                )
            except Exception as e:
                logger.error("Step 2 color match failed for %s: %s", p.requestedText, e)

        return p

    # Run enrichment for all products concurrently
    results = await asyncio.gather(*[enrich(r) for r in raw_products])
    results = list(results)

    out = [r.model_dump() for r in results]
    _elapsed = asyncio.get_event_loop().time() - _t0
    logger.info("── FINAL OUTPUT ── %d product(s) in %.2fs:\n%s", len(out), _elapsed, json.dumps(out, ensure_ascii=False, indent=2))
    logger.info("="*80 + "\n")
    return results


@app.get("/health")
async def health():
    logger.info("Health check pid=%s", os.getpid())
    return {"status": "ok"}