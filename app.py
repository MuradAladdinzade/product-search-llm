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

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger("app")


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

EXTRACT_PROMPT = """\
Extract products from the message and return ONLY a JSON array.

CRITICAL: Response MUST start with "[" and end with "]". No explanations, no markdown, no preamble.
CRITICAL: Use judgment to identify product boundaries — usually each line is a different product, but this is not a rule. A single line may contain multiple products (e.g. "16 Pro Black 256GB 🇺🇸 + 17 Air White 128GB"). A new line may also continue the previous product. Always parse by meaning, not by line.
CRITICAL: If any field cannot be determined → return null. Never omit a field.

=== OUTPUT FIELDS ===
{
  "quantity":         1,      // Positive integer, default 1
  "price":            0,      // Float, default 0
  "requestedText":    "...",  // Exact raw text the user wrote for this product — do NOT strip or modify anything or omit anything (don't do: 17+ 128 Черный 1  64 500 -> requestedText: "17 128 Черный 1  64 500", keep it as is: "17+ 128 Черный 1  64 500")
  "countryCode":      null,   // 2-letter ISO code ONLY if flag/country explicitly in this line (e.g. "🇺🇸"→"US", "🇮🇳"→"IN", "🇨🇳"→"CN") | Country name explicitly mentioned -> Return 2-letter ISO code ONLY| Country iso code written explicitly -> Return 2-letter ISO code ONLY | if multiple countries mentioned for the product, take the first country always.
  "brand":        "...",  // Apple | Samsung | Garmin | Poco | Dyson | Sony | etc.
  "product_type":     "...",  // iPhone | MacBook | iPad | Galaxy | Watch | Forerunner | etc.
  "category":     "...",  // phone | laptop | tablet | watch | earbuds | accessory | other
  "variant":      "...",  // Pro | Plus | Ultra | Mini | Air | Max | SE | null
  "model_code":   "...",  // SKU code: "MW2X3" | "SM-A520F" | null
  "size":         "...",  // Storage as <N>GB or <N>TB | null — same field as size below, only fill once
  "ram":          "...",  // RAM only if separate from storage: "8GB" | null
  "LLM_color_en":     "...",  // Color translated/normalized to English: "белый"→"White" | "синий"→"Blue" | if color field is null, then return null
  "prod_year":         "...",  // Year if mentioned: "2024" | null
  "productName":      "...",  // Full constructed name: brand + line + model + storage + color. e.g. "iPhone 17 256GB Black" | "Samsung Galaxy A56 256GB Light Gray"
  "model":            "...",  // iPhone: "16+" → "16 Plus" | "17" | "16 Pro" | "17 Pro Max" | "17 Air" | "17e" | "13 Mini" | "14 Plus" | iPad:   "Mini 7" | "Air" | "Pro 13" | Other:  "A56" | "S25 Ultra" | "Pro 14" | "Forerunner 55" | null if not determinable
  "size":             "...",  // Storage as <N>GB or <N>TB — same as storage but always present if determinable
  "color_from_text":  "...",  // Raw color EXACTLY as user wrote it, any language — do NOT translate or normalize
  "simType":          null    // iPhone only — extract ONLY if explicitly stated in text:
                              //   "1sim"+"esim"/"сим"+"есим" → "PHYSICAL_PLUS_ESIM"
                              //   "sim+esim"/"esim+sim"    → "PHYSICAL_PLUS_ESIM" 
                              //   sim+esim/esim+sim    → "PHYSICAL_PLUS_ESIM" 
                              //   "sim plus esim"/"esim plus sim"    → "PHYSICAL_PLUS_ESIM" 
                              //   "sim-esim"/"сим-есим" → "PHYSICAL_PLUS_ESIM"
                              //   "esim-sim"/"есим-сим" → "PHYSICAL_PLUS_ESIM"
                              //   "1sim/esim"/"сим/есим" → "PHYSICAL_PLUS_ESIM"
                              //   "1sim"/"1сим"           → "PHYSICAL_PLUS_ESIM"
                              //   "1 sim"/"1 сим"           → "PHYSICAL_PLUS_ESIM"
                              //   "1sim"+"esim" / "sim-esim" / "esim-sim"    → "PHYSICAL_PLUS_ESIM"  
                              //   "sim/esim" / "сим-есим" / "сим/есим"        → "PHYSICAL_PLUS_ESIM"  
                              //   "sim/esim" / "сим-есим" / "сим/есим"        → "PHYSICAL_PLUS_ESIM"  
                              //   "1sim"/"1 сим" alone                         → "PHYSICAL_PLUS_ESIM"
                              //   if "sim" and "esim" mentioned together in any format → "PHYSICAL_PLUS_ESIM" (e.g. "1sim"+"esim" / "sim-esim" / "esim-sim" / "sim+esim"/"esim+sim" / "sim/esim" / "сим-есим" / "сим/есим")

                              //   "esim"/"есим"/"только esim"/"только есим" alone → "ESIM_ONLY_SINGLE" (eSIM only, no physical SIM)
                              //   "Iphone 17 Air"/"Айфон 17 Эйр"/"Iphone Air" → "ESIM_ONLY_SINGLE" (eSIM only, no physical SIM)
                              //   "2 sim"/"2 сим"           → "PHYSICAL_DUAL" 
                              //   "2sim"/"2сим"                               → "PHYSICAL_DUAL"
                              //   any other sim mention not covered above      → "PHYSICAL_PLUS_ESIM"
                              //   Nothing mentioned                            → "PHYSICAL_PLUS_ESIM"
                              //   Always null for non-iPhones

}

=== QUANTITY ===
Default 1. x2 / 2шт / 35600-2 (price-qty) / 31.5x4 (price 31500, qty 4)
"green-2" = color green qty 2. "72600-2" = price 72600 qty 2.

=== PRICE ===
Default 0. "35,3"→35300 / "31.5x4"→price 31500 qty 4 / "3500 дают 3400"→3400
If multiple prices appear, take the lowest one. e.g. "54500 1шт ? 54700" → price: 54500

=== REQUESTEDTEXT ===
Keep exactly as the user wrote it — do NOT strip, clean, or modify anything.
Copy the raw text for this product as-is, including typos, Russian words, emojis, spacing.

=== variant ===
model->variant: variant should contain non-numeric part of model
"16 Pro"->Pro | "55"->Null | "13 Mini"->Mini | "14 Plus"->Plus | "15 Pro Max"->Pro Max | "17e"->e | "S25 Ultra"->Ultra | "16e"->e


=== EXAMPLES ===
Input: "iPad Mini 7 128GB Space Gray Wi-Fi MXN63 35700"
{"productName":"iPad Mini 7 128GB Space Gray Wi-Fi MXN63","size":"128GB","color_from_text":"Space Gray","quantity":1,"price":35700,"requestedText":"iPad Mini 7 128GB Space Gray Wi-Fi MXN63","countryCode":null,"simType":null,"brand":"Apple","product_type":"iPad","category":"tablet","model":"Mini 7","variant":"Mini","model_code":"MXN63","size":"128GB","ram":null,"LLM_color_en":"Space Gray","prod_year":null}

Input: "Pencil Pro 2025 MX2D3 8500"
{"productName":"Pencil Pro 2025 MX2D3","size":null,"color_from_text":null,"quantity":1,"price":8500,"requestedText":"Pencil Pro 2025 MX2D3","countryCode":null,"simType":null,"brand":"Apple","product_type":"Pencil","category":"accessory","model":null,"variant":"Pro","model_code":"MX2D3","size":null,"ram":null,"LLM_color_en":null,"prod_year":"2025"}

Input: "16 Pro 256 Black 🇮🇳 54000"
{"productName":"iPhone 16 Pro 256GB Black","size":"256GB","color_from_text":"Black","quantity":1,"price":54000,"requestedText":"16 Pro 256 Black 🇮🇳 54000","countryCode":"IN","simType":null,"brand":"Apple","product_type":"iPhone","category":"phone","model":"16 Pro","variant":"Pro","model_code":null,"size":"256GB","ram":null,"LLM_color_en":"Black","prod_year":null}

=== MODEL RULES ===
16E ≠ 16 (model: "16E"). PRO→Pro, PLUS→Plus, MAX→Max. N+→"N Plus": 15+→"15 Plus" | 16+→"16 Plus" | 17+→"17 Plus".
iPhone 16Max → model: "16 Pro Max", variant: "Pro Max", not "16 Max". iPhone never releases a "Max" variant without "Pro". If "Max" is mentioned → always assume "Pro Max".
"Air" alone → iPhone 17 Air (product_type: "iPhone", model: "17 Air").
"Air 7"/"iPad Air" → iPad (product_type: "iPad", model: null).
Samsung: "Galaxy A5 SM-A520F 3GB/32GB" → model:"A5", code:"SM-A520F", ram:"3GB", storage:"32GB"
 
=== MODEL CODE vs MODEL NAME ===
model_name: human-readable id — "16 Pro" | "A5" | "Pro 14" | "Forerunner 55"
model_code: hardware SKU — "SM-A520F" | "MW2X3" | "MH9J4" (always separate)
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
        raise ValueError(f"No JSON array in response: {raw[:200]}")
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

async def step1_extract(text: str) -> list[dict]:
    """Extract structured products from raw order text. Retries on bad JSON or empty result."""
    for attempt in range(3):
        raw = await _llm_call(EXTRACT_PROMPT, text, max_tokens=8192, cache=True)
        try:
            result = _parse_json_array(raw)
            if not result and attempt < 2:
                    # Only retry if response was suspiciously short — might be truncated
                    if len(raw) > 10:
                        return result  # LLM is confident there are no products
                    await asyncio.sleep(2)
                    continue
            return result
        except Exception as e:
            if attempt < 2:
                await asyncio.sleep(2)
                continue
            raise


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
    global _pool
    _pool = await asyncpg.create_pool(
        DATABASE_URL,
        min_size=DB_POOL_MIN,
        max_size=DB_POOL_MAX,
        server_settings={"client_encoding": "UTF8"},
    )
    yield
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


    # If LLM returned empty, return one fallback product per line
    if not raw_products:
        raw_products = [
            {"requestedText": line}
            for line in text.splitlines()
            if line.strip()
        ] or [{"requestedText": text}]

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
    return list(results)


@app.get("/health")
async def health():
    return {"status": "ok"}