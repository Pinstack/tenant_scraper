#!/usr/bin/env python3
"""
Curate low-confidence category mappings using a free LLM via OpenRouter.

Reads data/categories_needing_review.json and proposes improved
google_category mappings drawn from the Google category list.

Usage:
  OPENROUTER_API_KEY=... python scripts/curate_categories_openrouter.py \
    --input data/categories_needing_review.json \
    --categories data/google_business_categories_complete.json \
    --out outputs/curated_category_mappings_llm.json \
    --model openrouter/auto \
    --concurrency 4

Notes:
  - Network access and an OpenRouter API key are required.
  - Results are cached in outputs/openrouter_category_cache.json.
  - The prompt instructs the model to return strict JSON.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import aiohttp


OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


def load_categories(complete_categories_path: Path) -> List[str]:
    with complete_categories_path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    # Expect a flat list under 'categories'
    cats = data.get("categories") or []
    if not isinstance(cats, list):
        raise SystemExit("categories file must contain a flat 'categories' list")
    # Deduplicate and keep stable order
    seen = set()
    out: List[str] = []
    for c in cats:
        if isinstance(c, str) and c not in seen:
            out.append(c)
            seen.add(c)
    return out


def load_review_input(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def build_prompt(source_category: str, allowed: List[str]) -> str:
    instructions = (
        "You are mapping tenant categories to the closest Google Business Profile category.\n"
        "- Input: a single source tenant category string.\n"
        "- Output: a JSON object with keys: google_category (must be one of the allowed list), confidence ('high'|'medium'|'low').\n"
        "- Choose the single best match. If none is suitable, use 'Other > General > Unspecified' with 'low' confidence.\n"
        "- Respond with JSON only.\n"
    )
    # To keep the prompt reasonable in size, provide a compact allowed list (first N + hint to match broadly)
    sample = allowed[:3000]  # adequate breadth while staying within token limits for most models
    allowed_blob = "\n".join(f"- {c}" for c in sample)
    return (
        f"{instructions}\n"
        f"Source category: {source_category}\n"
        f"Allowed categories (subset of full list):\n{allowed_blob}\n"
        "Return: {\"google_category\": \\"<one from list>\\", \"confidence\": \"high|medium|low\"}"
    )


async def call_openrouter(session: aiohttp.ClientSession, model: str, prompt: str) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that returns strict JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    async with session.post(OPENROUTER_URL, json=payload, timeout=60) as resp:
        if resp.status != 200:
            text = await resp.text()
            raise RuntimeError(f"OpenRouter {resp.status}: {text[:200]}")
        data = await resp.json()
        try:
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
        except Exception as e:
            raise RuntimeError(f"Unexpected OpenRouter response shape: {e}")


async def curate(
    items: List[Tuple[str, Dict[str, Any]]],
    allowed_categories: List[str],
    *,
    api_key: str,
    model: str,
    concurrency: int,
    cache_path: Path,
) -> Dict[str, Dict[str, Any]]:
    cache: Dict[str, Any] = {}
    if cache_path.exists():
        try:
            cache = json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            cache = {}

    sem = asyncio.Semaphore(max(1, min(concurrency, 8)))
    out: Dict[str, Dict[str, Any]] = {}

    headers = {
        "Authorization": f"Bearer {api_key}",
        "HTTP-Referer": "https://github.com/",
        "X-Title": "tenant-scraper-category-curation",
    }
    async with aiohttp.ClientSession(headers=headers) as session:
        async def one(key: str, meta: Dict[str, Any]):
            if key in cache:
                out[key] = cache[key]
                return
            prompt = build_prompt(key, allowed_categories)
            async with sem:
                try:
                    resp = await call_openrouter(session, model, prompt)
                    # Basic validation
                    gc = str(resp.get("google_category", "")).strip()
                    conf = str(resp.get("confidence", "low")).strip().lower()
                    if not gc:
                        gc = "Other > General > Unspecified"
                    if conf not in ("high", "medium", "low"):
                        conf = "low"
                    result = {"google_category": gc, "confidence": conf}
                    cache[key] = result
                    out[key] = result
                finally:
                    # persist cache progressively
                    cache_path.parent.mkdir(parents=True, exist_ok=True)
                    cache_path.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

        await asyncio.gather(*(one(k, v) for k, v in items))

    return out


def main():
    parser = argparse.ArgumentParser(description="Curate categories using OpenRouter LLM")
    parser.add_argument("--input", type=Path, default=Path("data/categories_needing_review.json"))
    parser.add_argument("--categories", type=Path, default=Path("data/google_business_categories_complete.json"))
    parser.add_argument("--out", type=Path, default=Path("outputs/curated_category_mappings_llm.json"))
    parser.add_argument("--cache", type=Path, default=Path("outputs/openrouter_category_cache.json"))
    parser.add_argument("--model", type=str, default="openrouter/auto")
    parser.add_argument("--concurrency", type=int, default=4)

    args = parser.parse_args()
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise SystemExit("OPENROUTER_API_KEY environment variable is required")

    review = load_review_input(args.input)
    categories_map = review.get("categories", {})
    if not isinstance(categories_map, dict):
        raise SystemExit("Unexpected input format: missing 'categories' map")

    # Build worklist from keys (tenant category names)
    items = list(categories_map.items())
    # Filter to only low/none/medium
    work = [(k, v) for k, v in items if str(v.get("confidence", "")).lower() in ("low", "none", "medium")]

    allowed = load_categories(args.categories)
    curated = asyncio.run(
        curate(work, allowed, api_key=api_key, model=args.model, concurrency=args.concurrency, cache_path=args.cache)
    )

    # Compose output in a simple mapping structure
    out = {
        "description": "LLM-curated mappings for categories needing review",
        "source": str(args.input),
        "model": args.model,
        "total_reviewed": len(work),
        "mappings": {k: curated.get(k, {}) for k, _ in work},
    }
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(work)} curated mappings → {args.out}")


if __name__ == "__main__":
    main()

