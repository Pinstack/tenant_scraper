#!/usr/bin/env python3
"""
Enrich scraped tenant brands using the Brandfetch API to derive canonical
brand names and official domains. Results are cached to avoid re-requests.

Usage:
  python scripts/enrich_with_brandfetch.py \
    --input outputs/mecsr/complete_tenants_aggregate.json \
    --out-brands outputs/canonical_brands.json \
    --out-occupancies outputs/occupancies.json \
    --concurrency 5

Requirements:
  - Set BRANDFETCH_API_KEY in your environment
  - Network connectivity

Notes:
  - The script works best when tenant records include a website field from
    detailed scraping (use --details during scraping). If a website is
    missing, it falls back to Brandfetch's search endpoint by name.
  - Caches results in outputs/brandfetch_cache.json by default to respect
    rate limits and speed up re-runs.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from dataclasses import dataclass
import difflib
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import aiohttp


BRANDFETCH_BASE = "https://api.brandfetch.io/v2"


def _slugify_name(name: str) -> str:
    """Create a normalized slug key for brand names (for dedupe)."""
    s = name.strip().lower()
    # Remove common non-name prefixes and descriptors
    s = re.sub(r"^(the|store|shop)\s+", "", s)
    # Remove punctuation except '&' which is often meaningful
    s = re.sub(r"[^a-z0-9&\s]", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def _normalize_domain(url_or_domain: str) -> Optional[str]:
    if not url_or_domain:
        return None
    text = url_or_domain.strip()
    # Extract domain from URL if needed
    m = re.match(r"^(?:https?://)?([^/]+)", text)
    domain = m.group(1) if m else text
    domain = domain.lower()
    domain = domain.split("@")[0]  # avoid accidental emails
    # strip common prefixes
    if domain.startswith("www."):
        domain = domain[4:]
    # quick sanity checks
    if "." not in domain or any(c in domain for c in " <>\"'()"):
        return None
    return domain


def _load_json(path: Path, default):
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return default


@dataclass
class BrandfetchResult:
    key: str  # normalized brand key (by name or domain)
    source: str  # "domain" | "search"
    canonical_name: Optional[str]
    domain: Optional[str]
    brand_id: Optional[str]
    website: Optional[str]
    logos: List[Dict[str, Any]]
    colors: List[Dict[str, Any]]
    raw: Dict[str, Any]
    score: Optional[float] = None
    confidence: Optional[str] = None
    candidates: Optional[List[Dict[str, Any]]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "key": self.key,
            "source": self.source,
            "canonical_name": self.canonical_name,
            "domain": self.domain,
            "brand_id": self.brand_id,
            "website": self.website,
            "logos": self.logos,
            "colors": self.colors,
            "raw": self.raw,
            "score": self.score,
            "confidence": self.confidence,
            "candidates": self.candidates,
        }


class BrandfetchClient:
    def __init__(self, api_key: str, *, session: Optional[aiohttp.ClientSession] = None):
        self.api_key = api_key
        self._session = session

    async def __aenter__(self):
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._session:
            await self._session.close()
            self._session = None

    async def get_brand(self, domain_or_id: str) -> Optional[Dict[str, Any]]:
        """Fetch a brand by domain or ID.

        GET /v2/brands/{domain_or_id}
        """
        assert self._session is not None
        url = f"{BRANDFETCH_BASE}/brands/{domain_or_id}"
        async with self._session.get(url, timeout=20) as resp:
            if resp.status == 200:
                return await resp.json()
            if resp.status in (404, 422):
                return None
            text = await resp.text()
            raise RuntimeError(f"Brandfetch get_brand {resp.status}: {text[:200]}")

    async def search(self, query: str, *, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for brands by name.

        GET /v2/search/{query}?limit=N
        """
        assert self._session is not None
        q = query.strip()
        if not q:
            return []
        url = f"{BRANDFETCH_BASE}/search/{aiohttp.helpers.quote(q)}?limit={int(limit)}"
        async with self._session.get(url, timeout=20) as resp:
            if resp.status == 200:
                data = await resp.json()
                # Expect a list of results; each item may include 'name', 'domain', 'id'
                if isinstance(data, list):
                    return data
                # Some responses might wrap results
                if isinstance(data, dict) and "results" in data:
                    results = data.get("results")
                    if isinstance(results, list):
                        return results
                return []
            if resp.status in (404, 422):
                return []
            text = await resp.text()
            raise RuntimeError(f"Brandfetch search {resp.status}: {text[:200]}")


def _name_similarity(a: str, b: str) -> float:
    """Return 0..1 similarity between two names using difflib ratio."""
    a = a.strip().lower()
    b = b.strip().lower()
    if not a or not b:
        return 0.0
    return difflib.SequenceMatcher(None, a, b).ratio()


def _token_overlap(a: str, b: str) -> float:
    at = {t for t in re.findall(r"\b\w+\b", a.lower()) if len(t) > 1}
    bt = {t for t in re.findall(r"\b\w+\b", b.lower()) if len(t) > 1}
    if not at or not bt:
        return 0.0
    inter = len(at & bt)
    return inter / max(len(at), len(bt))


def _score_candidate(display_name: str, website_domain: Optional[str], cand_name: Optional[str], cand_domain: Optional[str]) -> float:
    score = 0.0
    # Domain signals
    if website_domain and cand_domain:
        if website_domain == cand_domain:
            score += 1.0
        elif website_domain.endswith(cand_domain) or cand_domain.endswith(website_domain):
            score += 0.6

    # Name similarity
    if cand_name:
        sim = _name_similarity(display_name, cand_name)
        score += sim * 0.5
        tovr = _token_overlap(display_name, cand_name)
        score += tovr * 0.4

    # Penalize overly generic domains
    if cand_domain and any(w in cand_domain for w in ["shop", "store", "retail", "market"]):
        score -= 0.1

    return score


def _score_to_confidence(score: float) -> str:
    if score >= 1.2:
        return "high"
    if score >= 0.8:
        return "medium"
    return "low"


async def _enrich_brand(client: BrandfetchClient, name: str, website: Optional[str]) -> Optional[BrandfetchResult]:
    # Prefer domain if we have a tenant website
    domain = _normalize_domain(website or "") if website else None

    # Try domain path first
    if domain:
        data = await client.get_brand(domain)
        if data:
            res = _to_result(key=domain, source="domain", data=data)
            res.score = 1.5
            res.confidence = "high"
            res.candidates = [{"domain": domain, "name": data.get("name"), "score": res.score}]
            return res

    # Fallback to search by name
    # Use a trimmed/cleaned display name to avoid venue suffixes (e.g., Mall branch)
    q = re.sub(r"\s*[-|–|•].*$", "", name).strip()
    results = await client.search(q, limit=5)
    candidates: List[Tuple[float, Dict[str, Any], Dict[str, Any]]] = []  # (score, item, data)
    for item in results:
        cand_domain = _normalize_domain(str(item.get("domain", "")))
        cand_id = str(item.get("id", "")).strip() or None
        token = cand_domain or cand_id
        if not token:
            continue
        data = await client.get_brand(token)
        if not data:
            continue
        cand_name = data.get("name") or item.get("name")
        sc = _score_candidate(name, domain, cand_name, cand_domain)
        candidates.append((sc, item, data))

    if candidates:
        candidates.sort(key=lambda x: x[0], reverse=True)
        top_score, top_item, top_data = candidates[0]
        res = _to_result(key=_slugify_name(name), source="search-ranked", data=top_data)
        res.score = float(top_score)
        res.confidence = _score_to_confidence(res.score)
        # Emit a compact candidates list for auditability
        res.candidates = [
            {
                "name": (d2.get("name") or i2.get("name")),
                "domain": _normalize_domain(str(i2.get("domain", ""))) or d2.get("domain"),
                "score": float(s2),
            }
            for (s2, i2, d2) in candidates[:5]
        ]
        return res

    return None


def _to_result(*, key: str, source: str, data: Dict[str, Any]) -> BrandfetchResult:
    # Best-effort extraction compatible across possible API shapes
    canonical_name = data.get("name") or data.get("brand", {}).get("name")
    domain = (
        data.get("domain")
        or data.get("brand", {}).get("domain")
        or (data.get("links", {}).get("website") if isinstance(data.get("links"), dict) else None)
    )
    website = None
    if isinstance(data.get("links"), dict):
        website = data["links"].get("website") or data["links"].get("url")
    brand_id = data.get("id") or data.get("brandId")

    logos = []
    if isinstance(data.get("logos"), list):
        logos = data.get("logos", [])
    elif isinstance(data.get("assets"), dict) and isinstance(data["assets"].get("logos"), list):
        logos = data["assets"]["logos"]

    colors = []
    if isinstance(data.get("colors"), list):
        colors = data.get("colors", [])
    elif isinstance(data.get("brand"), dict) and isinstance(data["brand"].get("colors"), list):
        colors = data["brand"]["colors"]

    return BrandfetchResult(
        key=key,
        source=source,
        canonical_name=canonical_name,
        domain=_normalize_domain(domain or "") if domain else None,
        brand_id=brand_id,
        website=website,
        logos=logos,
        colors=colors,
        raw=data,
    )


def _iter_brands(tenants: Iterable[Dict[str, Any]]) -> List[Tuple[str, Optional[str]]]:
    """Yield unique (name, website) pairs for enrichment.

    - Prefers a website if present in any occurrence of the brand.
    - Deduplicates by normalized brand key.
    """
    best: Dict[str, Tuple[str, Optional[str]]] = {}
    for t in tenants:
        name = (t.get("name") or "").strip()
        if not name:
            continue
        key = _slugify_name(name)
        # Prefer an HTTP website from detailed scrape if available
        site = t.get("website") or t.get("url")
        if site and not str(site).lower().startswith("http"):
            site = None
        prev = best.get(key)
        if prev is None or (site and not prev[1]):
            best[key] = (name, site)
    return list(best.values())


async def enrich_brands(
    tenants: List[Dict[str, Any]],
    api_key: str,
    *,
    concurrency: int = 5,
    cache_path: Optional[Path] = None,
) -> Dict[str, Dict[str, Any]]:
    """Return a mapping of brand_key -> BrandfetchResult (as dict)."""
    if cache_path is None:
        cache_path = Path("outputs/brandfetch_cache.json")
    cache = _load_json(cache_path, default={})

    # Build worklist
    pairs = _iter_brands(tenants)
    work: List[Tuple[str, str, Optional[str]]] = []  # (key, display_name, website)
    for display_name, website in pairs:
        key = _slugify_name(display_name)
        if key in cache:
            continue
        work.append((key, display_name, website))

    sem = asyncio.Semaphore(max(1, min(concurrency, 10)))
    results: Dict[str, Dict[str, Any]] = {}

    async with BrandfetchClient(api_key) as client:
        async def one(item: Tuple[str, str, Optional[str]]):
            key, name, website = item
            async with sem:
                try:
                    res = await _enrich_brand(client, name, website)
                    if res:
                        as_dict = res.to_dict()
                        cache[key] = as_dict
                        results[key] = as_dict
                except Exception as e:
                    # Keep going; log minimal info to cache as a marker
                    cache[key] = {"error": str(e)[:200]}

        await asyncio.gather(*(one(x) for x in work))

    # Persist cache
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    with cache_path.open("w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)

    return cache


def load_tenants(path: Path) -> List[Dict[str, Any]]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        # Accept either list of tenants or dict with tenants array
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            if "tenants" in data and isinstance(data["tenants"], list):
                return data["tenants"]
    raise ValueError("Unsupported tenants file format")


def build_occupancies(
    tenants: List[Dict[str, Any]],
    brand_map: Dict[str, Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """Produce a simple occupancy list linking malls to canonical brands.

    Output fields:
      - mall_name
      - brand_key
      - brand_canonical_name
      - brand_domain
      - category (raw)
      - google_categories.full_hierarchy (if present)
    """
    rows: List[Dict[str, Any]] = []
    for t in tenants:
        name = (t.get("name") or "").strip()
        if not name:
            continue
        key = _slugify_name(name)
        bf = brand_map.get(key) or {}
        rows.append(
            {
                "mall_name": t.get("mall_name"),
                "brand_key": key,
                "brand_display_name": name,
                "brand_canonical_name": bf.get("canonical_name"),
                "brand_domain": bf.get("domain"),
                "brand_id": bf.get("brand_id"),
                "category": t.get("category"),
                "google_category_hierarchy": (
                    (t.get("google_categories") or {}).get("full_hierarchy")
                    if isinstance(t.get("google_categories"), dict)
                    else None
                ),
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description="Enrich tenants with Brandfetch canonical brand info")
    parser.add_argument(
        "--input",
        type=Path,
        default=Path("outputs/mecsr/complete_tenants_aggregate.json"),
        help="Path to tenants JSON (aggregated)",
    )
    parser.add_argument(
        "--out-brands",
        type=Path,
        default=Path("outputs/canonical_brands.json"),
        help="Where to write the canonical brand index",
    )
    parser.add_argument(
        "--out-occupancies",
        type=Path,
        default=Path("outputs/occupancies.json"),
        help="Where to write mall→brand occupancy links",
    )
    parser.add_argument(
        "--cache",
        type=Path,
        default=Path("outputs/brandfetch_cache.json"),
        help="Cache file for Brandfetch responses",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Max concurrent Brandfetch lookups",
    )

    args = parser.parse_args()

    api_key = os.getenv("BRANDFETCH_API_KEY")
    if not api_key:
        raise SystemExit("BRANDFETCH_API_KEY environment variable is required")

    tenants = load_tenants(args.input)
    print(f"Loaded {len(tenants)} tenants from {args.input}")

    brand_map = asyncio.run(
        enrich_brands(
            tenants,
            api_key,
            concurrency=args.concurrency,
            cache_path=args.cache,
        )
    )

    # Persist canonical brands (sorted by key)
    items = sorted(brand_map.items(), key=lambda kv: kv[0])
    brands_out = [dict({"brand_key": k}, **(v if isinstance(v, dict) else {"raw": v})) for k, v in items]
    args.out_brands.parent.mkdir(parents=True, exist_ok=True)
    with args.out_brands.open("w", encoding="utf-8") as f:
        json.dump(brands_out, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(brands_out)} canonical brands → {args.out_brands}")

    # Build occupancy links
    occupancies = build_occupancies(tenants, brand_map)
    with args.out_occupancies.open("w", encoding="utf-8") as f:
        json.dump(occupancies, f, ensure_ascii=False, indent=2)
    print(f"Wrote {len(occupancies)} occupancy rows → {args.out_occupancies}")


if __name__ == "__main__":
    main()
