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

load_dotenv()

# ══════════════════════════════════════════════════════════════════════════════
# ── CONFIG — adjust these values ─────────────────────────────────────────────
# ══════════════════════════════════════════════════════════════════════════════

# Anthropic
ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
# LLM_MODEL         = "claude-sonnet-4-20250514"
LLM_MODEL         = "claude-haiku-4-5-20251001"
LLM_TIMEOUT       = 120.0   # seconds — increase if you see timeouts

# Postgres
DATABASE_URL = (
    f"postgresql://{os.getenv('DB_USER')}:{os.getenv('DB_PASSWORD')}"
    f"@{os.getenv('DB_HOST', 'localhost')}:{os.getenv('DB_PORT', '5432')}"
    f"/{os.getenv('DB_NAME')}"
)
DB_POOL_MIN  = 2    # min connections in pool
DB_POOL_MAX  = 10   # max connections in pool

# DB query — adjust table/column names to match your schema
DB_TABLE              = "ai_product.products"
DB_COL_PRODUCT_LINE   = '"LLM_product_line"'
DB_COL_MODEL_NAME     = '"LLM_model_name"'
DB_COL_CATEGORY       = '"LLM_category"'
DB_COL_STORAGE        = '"LLM_storage"'
DB_COL_COUNTRY        = "extracted_country_code"
DB_COL_SIM_TYPE       = "new_sim_card_type"
DB_COL_COLOR          = '"LLM_color_en"'

# ══════════════════════════════════════════════════════════════════════════════


# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger("app")


# ── Pydantic models ───────────────────────────────────────────────────────────

class EnrichedProduct(BaseModel):
    # Core fields (matches legacy format)
    productName:      Optional[str] = None
    productType:      Optional[str] = None
    model:            Optional[str] = None
    size:             Optional[str] = None
    color:            Optional[str] = None
    # Order info
    quantity:         int           = 1
    price:            float         = 0.0
    requestedText:    str
    countryCode:      Optional[str] = None
    # SIM (iPhones only)
    simType:          Optional[SimCardType] = None
    simConflict:      bool          = False
    # LLM extracted fields
    LLM_brand:        Optional[str] = None
    LLM_product_line: Optional[str] = None
    LLM_category:     Optional[str] = None
    LLM_model_name:   Optional[str] = None
    LLM_variant:      Optional[str] = None
    LLM_model_code:   Optional[str] = None
    LLM_storage:      Optional[str] = None
    LLM_ram:          Optional[str] = None
    LLM_color_en:     Optional[str] = None
    LLM_year:         Optional[str] = None
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
  "requestedText":    "...",  // Exact raw text the user wrote for this product — do NOT strip or modify anything
  "countryCode":      null,   // 2-letter ISO code ONLY if flag/country explicitly in this line
  "LLM_brand":        "...",  // Apple | Samsung | Garmin | Poco | Dyson | Sony | etc.
  "LLM_product_line": "...",  // iPhone | MacBook | iPad | Galaxy | Watch | Forerunner | etc.
  "LLM_category":     "...",  // phone | laptop | tablet | watch | earbuds | accessory | other
  "LLM_model_name":   "...",  // Model WITHOUT brand/line: "16 Pro" | "A56" | "Pro 14" | "55"
  "LLM_variant":      "...",  // Pro | Plus | Ultra | Mini | Air | Max | SE | null
  "LLM_model_code":   "...",  // SKU code: "MW2X3" | "SM-A520F" | null
  "LLM_storage":      "...",  // Storage as <N>GB or <N>TB | null
  "LLM_ram":          "...",  // RAM only if separate from storage: "8GB" | null
  "LLM_color_en":     "...",  // Color translated/normalized to English: "белый"→"White" | "синий"→"Blue" | null
  "LLM_year":         "...",  // Year if mentioned: "2024" | null
  "productName":      "...",  // Full constructed name: brand + line + model + storage + color. e.g. "iPhone 17 256GB Black" | "Samsung Galaxy A56 256GB Light Gray"
  "productType":      "...",  // Top-level type: iPhone | MacBook | iPad | Samsung | Apple Watch | Airpods | Dyson | Other
  "model":            "...",  // Model identifier for any product: "17" | "16 Pro" | "Mini 7" | "S25 Ultra" | "Pro 14" — null if not determinable
  "size":             "...",  // Storage as <N>GB or <N>TB — same as LLM_storage but always present if determinable
  "color":            "...",  // Raw color EXACTLY as user wrote it, any language — do NOT translate or normalize
  "simType":          null    // iPhone only — extract ONLY if explicitly stated in text:
                              //   "esim"/"есим"            → "ESIM_ONLY_SINGLE"
                              //   "2sim"/"2 сим"           → "PHYSICAL_DUAL"
                              //   "1sim"/"1 сим"           → "PHYSICAL_SINGLE_WITHOUT_ESIM"
                              //   "1sim"+"esim"/"сим"+"есим" → "PHYSICAL_PLUS_ESIM"
                              //   Nothing mentioned        → null (server will resolve from country)
                              //   Always null for non-iPhones
}

=== REQUESTEDTEXT ===
Keep exactly as the user wrote it — do NOT strip, clean, or modify anything.
Copy the raw text for this product as-is, including typos, Russian words, emojis, spacing.

=== QUANTITY ===
Default 1. x2 / 2шт / 35600-2 (price-qty) / 31.5x4 (price 31500, qty 4)
"green-2" = color green qty 2. "72600-2" = price 72600 qty 2.

=== PRICE ===
Default 0. "35,3"→35300 / "31.5x4"→price 31500 qty 4 / "3500 дают 3400"→3400
If multiple prices appear, take the first one. e.g. "54500 1шт ? 54700" → price: 54500

=== EXAMPLES ===
Input: "iPad Mini 7 128GB Space Gray Wi-Fi MXN63 35700"
{"productName":"iPad Mini 7 128GB Space Gray Wi-Fi MXN63","productType":"iPad","model":"Mini 7","size":"128GB","color":"Space Gray","quantity":1,"price":35700,"requestedText":"iPad Mini 7 128GB Space Gray Wi-Fi MXN63","countryCode":null,"simType":null,"LLM_brand":"Apple","LLM_product_line":"iPad","LLM_category":"tablet","LLM_model_name":"Mini 7","LLM_variant":"Mini","LLM_model_code":"MXN63","LLM_storage":"128GB","LLM_ram":null,"LLM_color_en":"Space Gray","LLM_year":null}

Input: "Pencil Pro 2025 MX2D3 8500"
{"productName":"Pencil Pro 2025 MX2D3","productType":"Pencil","model":null,"size":null,"color":null,"quantity":1,"price":8500,"requestedText":"Pencil Pro 2025 MX2D3","countryCode":null,"simType":null,"LLM_brand":"Apple","LLM_product_line":"Pencil","LLM_category":"accessory","LLM_model_name":null,"LLM_variant":"Pro","LLM_model_code":"MX2D3","LLM_storage":null,"LLM_ram":null,"LLM_color_en":null,"LLM_year":"2025"}

Input: "16 Pro 256 Black 🇮🇳 54000"
{"productName":"iPhone 16 Pro 256GB Black","productType":"iPhone","model":"16 Pro","size":"256GB","color":"Black","quantity":1,"price":54000,"requestedText":"16 Pro 256 Black 🇮🇳 54000","countryCode":"IN","simType":null,"LLM_brand":"Apple","LLM_product_line":"iPhone","LLM_category":"phone","LLM_model_name":"16 Pro","LLM_variant":"Pro","LLM_model_code":null,"LLM_storage":"256GB","LLM_ram":null,"LLM_color_en":"Black","LLM_year":null}

=== MODEL RULES ===
16E ≠ 16 (model: "16E"). PRO→Pro, PLUS→Plus, MAX→Max. 15+→"15 Plus".
"Air" alone → iPhone 17 Air (line: "iPhone", model: "17 Air").
"Air 7"/"iPad Air" → iPad (line: "iPad", model: null).
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
    Call the Anthropic API.
    Set cache=True to enable prompt caching on the system prompt (saves cost + latency on repeated calls).
    Requires system prompt to be >= 1024 tokens to be eligible for caching.
    """
    # Build system block — with or without cache_control
    if cache:
        system_block = [
            {
                "type": "text",
                "text": system,
                "cache_control": {"type": "ephemeral"},
            }
        ]
    else:
        system_block = system

    async with httpx.AsyncClient(timeout=LLM_TIMEOUT) as client:
        resp = await client.post(
            ANTHROPIC_API_URL,
            headers={
                "Content-Type":        "application/json; charset=utf-8",
                "x-api-key":           ANTHROPIC_API_KEY,
                "anthropic-version":   "2023-06-01",
                "anthropic-beta":      "prompt-caching-2024-07-31",
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
    logger.info(
        "Tokens — input: %d | cache_created: %d | cache_read: %d | output: %d",
        usage.get("input_tokens", 0),
        usage.get("cache_creation_input_tokens", 0),
        usage.get("cache_read_input_tokens", 0),
        usage.get("output_tokens", 0),
    )
    return data["content"][0]["text"].strip()


# ── DB helpers ────────────────────────────────────────────────────────────────

async def fetch_color_candidates(
    pool: asyncpg.Pool,
    product_line: Optional[str],
    model_name: Optional[str],
    category: Optional[str],
    storage: Optional[str]   = None,
    country_code: Optional[str] = None,
    sim_type: Optional[str]  = None,
) -> list[dict]:
    """
    Query DB for color candidates using ILIKE (contains) for text fields,
    exact match for country, sim_type, storage.
    ⚠️  ADJUST the WHERE clause to match your schema if needed.
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(f"""
            SELECT DISTINCT {DB_COL_COLOR} AS color
            FROM   {DB_TABLE}
            WHERE  {DB_COL_COLOR} IS NOT NULL
              AND  ($1::text IS NULL OR {DB_COL_PRODUCT_LINE} ILIKE $1)
              AND  ($2::text IS NULL OR {DB_COL_MODEL_NAME}   ILIKE $2)
              AND  ($3::text IS NULL OR {DB_COL_CATEGORY}     ILIKE $3)
              AND  ($4::text IS NULL OR {DB_COL_STORAGE}      = $4)
              AND  ($5::text IS NULL OR {DB_COL_COUNTRY}      = $5)
              AND  ($6::text IS NULL OR {DB_COL_SIM_TYPE}     = $6)
        """,
            f"%{product_line}%" if product_line else None,
            f"%{model_name}%"   if model_name   else None,
            f"%{category}%"     if category      else None,
            storage,
            country_code,
            sim_type,
        )
    return [{"color": r["color"]} for r in rows]


# ── Core pipeline steps ───────────────────────────────────────────────────────

async def step1_extract(text: str) -> list[dict]:
    """Extract structured products from raw order text."""
    raw = await _llm_call(EXTRACT_PROMPT, text, max_tokens=8192, cache=True)
    return _parse_json_array(raw)


async def step2_match_color(
    pool: asyncpg.Pool,
    product_line: Optional[str],
    model_name: Optional[str],
    category: Optional[str],
    requested_text: str,
    color_en: Optional[str],
    storage: Optional[str]      = None,
    country_code: Optional[str] = None,
    sim_type: Optional[str]     = None,
) -> Optional[str]:
    """
    Query DB for candidates with all available filters, ask LLM to pick best color.
    Falls back to broader query if no candidates found with strict filters.
    Returns matched_color from DB candidates.
    """
    # Try strict match first (with storage, country, sim_type)
    candidates = await fetch_color_candidates(
        pool, product_line, model_name, category,
        storage=storage, country_code=country_code, sim_type=sim_type
    )
    # Fallback: drop storage, country, sim_type if no results
    if not candidates:
        logger.warning("No candidates with strict filters, falling back for %s %s", product_line, model_name)
        candidates = await fetch_color_candidates(pool, product_line, model_name, category)
    if not candidates:
        logger.warning("No DB candidates at all for %s / %s / %s", product_line, model_name, category)
        return None

    user_msg = json.dumps({
        "requested_text":     requested_text,
        "user_color_english": color_en,
        "available_colors":   candidates,
    }, ensure_ascii=False)

    raw = await _llm_call(COLOR_PROMPT, user_msg, max_tokens=64)
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()

    matched_color = json.loads(raw).get("matched_color")
    return matched_color


def _is_iphone(product: dict) -> bool:
    brand = (product.get("LLM_brand") or "").lower()
    line  = (product.get("LLM_product_line") or "").lower()
    return brand == "apple" and "iphone" in line


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
    logger.info("DB pool ready (min=%d max=%d)", DB_POOL_MIN, DB_POOL_MAX)
    yield
    await _pool.close()
    logger.info("DB pool closed")


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

    logger.info("Parsing: %r", text[:100])

    # ── Step 1: extract ───────────────────────────────────────────────────────
    try:
        raw_products = await step1_extract(text)
    except Exception as e:
        logger.error("Step 1 failed: %s", e)
        raise HTTPException(status_code=502, detail=f"Extraction failed: {e}")

    logger.info("Step 1 extracted %d products", len(raw_products))

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
                model=p.LLM_model_name,
                country_code=p.countryCode,
                requested_text=p.requestedText,
                llm_sim_type=p.simType,  # LLM-extracted value from Step 1
            )
            p.simType     = sim["simType"]
            p.simConflict = sim["simConflict"]
            if sim["simConflict"]:
                logger.warning("SIM conflict: %s | text=%s country=%s",
                               p.requestedText, sim["simExtracted"], sim["simCountry"])

            # Color match from DB
            try:
                p.matched_color = await step2_match_color(
                    _pool,
                    p.LLM_product_line,
                    p.LLM_model_name,
                    p.LLM_category,
                    p.requestedText,
                    p.LLM_color_en,
                    storage=p.LLM_storage,
                    country_code=p.countryCode,
                    sim_type=p.simType.value if p.simType else None,
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