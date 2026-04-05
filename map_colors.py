"""
map_colors.py
Adds official_color column to ai_product.iphone_colors by matching
LLM_color_en against official Apple color names from the CSV per model.

Run: python map_colors.py [--dry-run]
"""

import asyncio
import json
import logging
import os

import asyncpg
import httpx
from dotenv import load_dotenv

load_dotenv()

DB_HOST      = os.getenv("DB_HOST", "localhost")
DB_PORT      = os.getenv("DB_PORT", "5432")
DB_NAME      = os.getenv("DB_NAME")
DB_USER      = os.getenv("DB_USER")
DB_PASSWORD  = os.getenv("DB_PASSWORD")
DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL             = "claude-haiku-4-5-20251001"

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
logger = logging.getLogger("map_colors")


# ── Official color map from CSV ───────────────────────────────────────────────
# model_key (lowercase) → list of official color names

OFFICIAL_COLORS: dict[str, list[str]] = {
    "11":           ["(PRODUCT) RED", "Green", "Purple", "Yellow", "Black", "White"],
    "11 pro":       ["Midnight Green", "Space Gray", "Gold", "Silver"],
    "11 pro max":   ["Midnight Green", "Space Gray", "Gold", "Silver"],
    "12":           ["(PRODUCT) RED", "Green", "Black", "Blue", "Purple", "White"],
    "12 mini":      ["(PRODUCT) RED", "Green", "Black", "Blue", "Purple", "White"],
    "12 pro":       ["Graphite", "Pacific Blue", "Gold", "Silver"],
    "12 pro max":   ["Graphite", "Pacific Blue", "Gold", "Silver"],
    "13":           ["Midnight", "Starlight", "(PRODUCT) RED", "Pink", "Green", "Blue"],
    "13 mini":      ["Midnight", "Starlight", "(PRODUCT) RED", "Pink", "Green", "Blue"],
    "13 pro":       ["Alpine Green", "Sierra Blue", "Gold", "Graphite", "Silver"],
    "13 pro max":   ["Alpine Green", "Sierra Blue", "Gold", "Graphite", "Silver"],
    "14":           ["Midnight", "Starlight", "(PRODUCT) RED", "Blue", "Purple", "Yellow"],
    "14 plus":      ["Midnight", "Starlight", "(PRODUCT) RED", "Blue", "Purple", "Yellow"],
    "14 pro":       ["Deep Purple", "Space Black", "Gold", "Silver"],
    "14 pro max":   ["Deep Purple", "Space Black", "Gold", "Silver"],
    "15":           ["Black", "Blue", "Green", "Pink", "Yellow"],
    "15 plus":      ["Black", "Blue", "Green", "Pink", "Yellow"],
    "15 pro":       ["Black Titanium", "Blue Titanium", "Natural Titanium", "White Titanium"],
    "15 pro max":   ["Black Titanium", "Blue Titanium", "Natural Titanium", "White Titanium"],
    "16":           ["Ultramarine", "Black", "Pink", "Teal", "White"],
    "16 plus":      ["Ultramarine", "Black", "Pink", "Teal", "White"],
    "16 pro":       ["Desert Titanium", "Black Titanium", "Natural Titanium", "White Titanium"],
    "16 pro max":   ["Desert Titanium", "Black Titanium", "Natural Titanium", "White Titanium"],
    "16e":          ["Black", "White"],
    "17":           ["Mist Blue", "Black", "Lavender", "Sage", "White"],
    "17 air":       ["Cloud White", "Light Gold", "Sky Blue", "Space Black"],
    "17 plus":      ["Mist Blue", "Black", "Lavender", "Sage", "White"],
    "17 pro":       ["Cosmic Orange", "Deep Blue", "Silver"],
    "17 pro max":   ["Cosmic Orange", "Deep Blue", "Silver"],
    "17e":          ["Soft Pink", "Black", "White"],
    "se":           ["Gold", "Rose Gold", "Silver", "Space Gray"],
    "se 2":         ["(PRODUCT) RED", "Black", "White"],
    "se 3":         ["Midnight", "Starlight", "(PRODUCT) RED"],
    "xr":           ["(PRODUCT) RED", "Yellow", "White", "Coral", "Black", "Blue"],
}


COLOR_MATCH_PROMPT = """\
You are an Apple iPhone color expert. Match the extracted color to an official Apple color name for the given model.

Return ONLY: {"official_color": "..." or null}
- official_color must be copied EXACTLY from the official_colors list
- Return null if the extracted color clearly does not match any official color for this model
- Examples of good matches: "White" → "Starlight" (iPhone 13) | "Black" → "Midnight" (iPhone 13) | "White" → "White Titanium" (iPhone 15 Pro)
- "Natural" → "Natural Titanium" | "Desert" → "Desert Titanium" | "Pacific blue" → "Pacific Blue"
- "(PRODUCT) RED" matches any red variant
- Examples of null: "White" for iPhone 15 Plus (no white — only Black/Blue/Green/Pink/Yellow) | "Purple" for iPhone 15 Pro (no purple)
- When the color clearly does not exist for this model, return null rather than guessing wrong
"""


# ── Manual overrides ─────────────────────────────────────────────────────────
# (model_key, llm_color_lower) → official_color
# Use when LLM_color_en is wrong but you know the correct mapping
OVERRIDES: dict[tuple[str, str], str] = {
    # 11
    ("11", "black"): "Black",
    ("11", "green"): "Green",
    ("11", "purple"): "Purple",
    ("11", "red"): "(PRODUCT) RED",
    ("11", "white"): "White",
    ("11", "yellow"): "Yellow",
    # 12
    ("12", "black"): "Black",
    ("12", "blue"): "Blue",
    ("12", "green"): "Green",
    ("12", "purple"): "Purple",
    ("12", "red"): "(PRODUCT) RED",
    ("12", "white"): "White",
    # 12 Mini
    ("12 mini", "black"): "Black",
    ("12 mini", "blue"): "Blue",
    ("12 mini", "green"): "Green",
    ("12 mini", "purple"): "Purple",
    ("12 mini", "red"): "(PRODUCT) RED",
    ("12 mini", "white"): "White",
    # 13
    ("13", "alpine green"): "Green",
    ("13", "black"): "Midnight",
    ("13", "blue"): "Blue",
    ("13", "green"): "Green",
    ("13", "midnight"): "Midnight",
    ("13", "pink"): "Pink",
    ("13", "red"): "(PRODUCT) RED",
    ("13", "starlight"): "Starlight",
    ("13", "white"): "Starlight",
    # 13 Mini
    ("13 mini", "black"): "Midnight",
    ("13 mini", "blue"): "Blue",
    ("13 mini", "green"): "Green",
    ("13 mini", "midnight"): "Midnight",
    ("13 mini", "pink"): "Pink",
    ("13 mini", "red"): "(PRODUCT) RED",
    ("13 mini", "starlight"): "Starlight",
    ("13 mini", "white"): "Starlight",
    # 13 Pro
    ("13 pro", "alpine green"): "Alpine Green",
    ("13 pro", "black"): "Graphite",
    ("13 pro", "gold"): "Gold",
    ("13 pro", "graphite"): "Graphite",
    ("13 pro", "sierra blue"): "Sierra Blue",
    ("13 pro", "silver"): "Silver",
    # 13 Pro Max
    ("13 pro max", "alpine green"): "Alpine Green",
    ("13 pro max", "black"): "Graphite",
    ("13 pro max", "gold"): "Gold",
    ("13 pro max", "graphite"): "Graphite",
    ("13 pro max", "sierra blue"): "Sierra Blue",
    ("13 pro max", "silver"): "Silver",
    # 14
    ("14", "blue"): "Blue",
    ("14", "deep purple"): "Purple",
    ("14", "midnight"): "Midnight",
    ("14", "purple"): "Purple",
    ("14", "red"): "(PRODUCT) RED",
    ("14", "starlight"): "Starlight",
    ("14", "yellow"): "Yellow",
    # 14 Plus
    ("14 plus", "black"): "Midnight",
    ("14 plus", "blue"): "Blue",
    ("14 plus", "midnight"): "Midnight",
    ("14 plus", "purple"): "Purple",
    ("14 plus", "red"): "(PRODUCT) RED",
    ("14 plus", "starlight"): "Starlight",
    ("14 plus", "white"): "Starlight",
    ("14 plus", "yellow"): "Yellow",
    # 14 Pro
    ("14 pro", "black"): "Space Black",
    ("14 pro", "deep purple"): "Deep Purple",
    ("14 pro", "gold"): "Gold",
    ("14 pro", "purple"): "Deep Purple",
    ("14 pro", "silver"): "Silver",
    ("14 pro", "space black"): "Space Black",
    ("14 pro", "white"): "Silver",
    # 14 Pro Max
    ("14 pro max", "black"): "Space Black",
    ("14 pro max", "deep purple"): "Deep Purple",
    ("14 pro max", "gold"): "Gold",
    ("14 pro max", "purple"): "Deep Purple",
    ("14 pro max", "silver"): "Silver",
    ("14 pro max", "space black"): "Space Black",
    ("14 pro max", "white"): "Silver",
    # 15
    ("15", "red"): "Pink",
    ("15", "white"): "Blue",
    ("15", "purple"): "Pink",
    ("15", "black"): "Black",
    ("15", "blue"): "Blue",
    ("15", "green"): "Green",
    ("15", "pink"): "Pink",
    ("15", "yellow"): "Yellow",
    # 15 Plus
    ("15 plus", "black"): "Black",
    ("15 plus", "blue"): "Blue",
    ("15 plus", "green"): "Green",
    ("15 plus", "pink"): "Pink",
    ("15 plus", "white"): "Blue",
    ("15 plus", "purple"): "Pink",
    ("15 plus", "red"): "Pink",
    ("15 plus", "yellow"): "Yellow",
    # 15 Pro
    ("15 pro", "black"): "Black Titanium",
    ("15 pro", "blue"): "Blue Titanium",
    ("15 pro", "natural"): "Natural Titanium",
    ("15 pro", "white"): "White Titanium",
    ("15 pro", "gold"): "Natural Titanium",
    ("15 pro", "purple"): "Blue Titanium",
    # 15 Pro Max
    ("15 pro max", "black"): "Black Titanium",
    ("15 pro max", "blue"): "Blue Titanium",
    ("15 pro max", "blue titanium"): "Blue Titanium",
    ("15 pro max", "natural"): "Natural Titanium",
    ("15 pro max", "natural titanium"): "Natural Titanium",
    ("15 pro max", "white"): "White Titanium",
    ("15 pro max", "white titanium"): "White Titanium",
    ("15 pro max", "gold"): "Natural Titanium",
    ("15 pro max", "purple"): "Blue Titanium",
    # 16
    ("16", "black"): "Black",
    ("16", "pink"): "Pink",
    ("16", "teal"): "Teal",
    ("16", "ultramarine"): "Ultramarine",
    ("16", "white"): "White",
    # 16 Plus
    ("16 plus", "black"): "Black",
    ("16 plus", "pink"): "Pink",
    ("16 plus", "teal"): "Teal",
    ("16 plus", "ultramarine"): "Ultramarine",
    ("16 plus", "white"): "White",
    # 16 Pro
    ("16 pro", "black"): "Black Titanium",
    ("16 pro", "desert"): "Desert Titanium",
    ("16 pro", "natural"): "Natural Titanium",
    ("16 pro", "white"): "White Titanium",
    # 16 Pro Max
    ("16 pro max", "black"): "Black Titanium",
    ("16 pro max", "desert"): "Desert Titanium",
    ("16 pro max", "natural"): "Natural Titanium",
    ("16 pro max", "white"): "White Titanium",
    # 16E
    ("16e", "black"): "Black",
    ("16e", "white"): "White",
    # 17
    ("17", "black"): "Black",
    ("17", "blue"): "Mist Blue",
    ("17", "lavender"): "Lavender",
    ("17", "sage"): "Sage",
    ("17", "white"): "White",
    # 17 Air
    ("17 air", "black"): "Space Black",
    ("17 air", "blue"): "Sky Blue",
    ("17 air", "cloud white"): "Cloud White",
    ("17 air", "gold"): "Light Gold",
    ("17 air", "light gold"): "Light Gold",
    ("17 air", "sky blue"): "Sky Blue",
    ("17 air", "space black"): "Space Black",
    ("17 air", "white"): "Cloud White",
    # 17 Pro
    ("17 pro", "blue"): "Deep Blue",
    ("17 pro", "orange"): "Cosmic Orange",
    ("17 pro", "silver"): "Silver",
    # 17 Pro Max
    ("17 pro max", "blue"): "Deep Blue",
    ("17 pro max", "orange"): "Cosmic Orange",
    ("17 pro max", "silver"): "Silver",
    # 17E
    ("17e", "black"): "Black",
    ("17e", "pink"): "Soft Pink",
    ("17e", "white"): "White",
    # SE (1st gen)
    ("se", "black"): "Space Gray",
    ("se", "red"): "(PRODUCT) RED",
    ("se", "white"): "Silver",
    # SE 2
    ("se 2", "black"): "Black",
    ("se 2", "red"): "(PRODUCT) RED",
    ("se 2", "white"): "White",
    # SE 3
    ("se 3", "black"): "Midnight",
    ("se 3", "red"): "(PRODUCT) RED",
    ("se 3", "white"): "Starlight",
    # XR
    ("xr", "black"): "Black",
    ("xr", "red"): "(PRODUCT) RED",
}


async def match_color(model: str, llm_color: str) -> str | None:
    model_key = model.strip().lower() if model else ""
    # Normalize SE variants — keep se 2 / se 3 distinct, collapse others to "se"
    if model_key.startswith("se"):
        if "2" in model_key:
            model_key = "se 2"
        elif "3" in model_key:
            model_key = "se 3"
        else:
            model_key = "se"

    official = OFFICIAL_COLORS.get(model_key)
    if not official:
        return None
    if not llm_color:
        return None

    # Check manual overrides first
    override = OVERRIDES.get((model_key, llm_color.strip().lower()))
    if override:
        return override

    user_msg = json.dumps({
        "model":           model,
        "extracted_color": llm_color,
        "official_colors": official,
    }, ensure_ascii=False)

    for attempt in range(3):
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                ANTHROPIC_API_URL,
                headers={
                    "Content-Type":      "application/json; charset=utf-8",
                    "x-api-key":         ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                },
                json={
                    "model":      MODEL,
                    "max_tokens": 32,
                    "system":     COLOR_MATCH_PROMPT,
                    "messages":   [{"role": "user", "content": user_msg}],
                },
            )
        if resp.status_code == 429:
            wait = 10 * (attempt + 1)
            logger.warning("Rate limited, retrying in %ds...", wait)
            await asyncio.sleep(wait)
            continue
        resp.raise_for_status()
        break

    raw = resp.json()["content"][0]["text"].strip()
    if raw.startswith("```"):
        raw = "\n".join(l for l in raw.splitlines() if not l.startswith("```")).strip()
    # Extract JSON object robustly — ignore any extra text before/after
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON in response: {raw[:100]}")
    return json.loads(raw[start:end+1]).get("official_color")


async def main(dry_run: bool = False):
    pool = await asyncpg.create_pool(
        DATABASE_URL, min_size=1, max_size=5,
        server_settings={"client_encoding": "UTF8"}
    )

    # Add column
    async with pool.acquire() as conn:
        await conn.execute("""
            ALTER TABLE ai_product.iphone_colors
            ADD COLUMN IF NOT EXISTS official_color TEXT
        """)
    logger.info("Column official_color ready")

    # Read all rows
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT "LLM_model_name", "LLM_color_en"
            FROM ai_product.iphone_colors

        """)
    logger.info("Read %d rows to process", len(rows))

    updates = []
    for row in rows:
        model    = row["LLM_model_name"]
        color_en = row["LLM_color_en"]
        try:
            official = await match_color(model, color_en)
            await asyncio.sleep(0.3)   # small delay to avoid rate limits
        except Exception as e:
            logger.error("Failed for model=%s color=%s: %s", model, color_en, e)
            official = None

        updates.append((model, color_en, official))
        logger.info("  %s / %r → %r", model, color_en, official)

    if not dry_run:
        async with pool.acquire() as conn:
            await conn.executemany("""
                UPDATE ai_product.iphone_colors
                SET official_color = $3
                WHERE "LLM_model_name" = $1
                  AND "LLM_color_en"   = $2
            """, updates)
        logger.info("Updated %d rows", len(updates))

    await pool.close()
    logger.info("Done.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    asyncio.run(main(args.dry_run))