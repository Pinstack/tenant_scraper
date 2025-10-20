#!/usr/bin/env python3
"""
Enrich scraped tenant data with FSQ-OS-Places information.

This script takes your Google Maps scraped tenant data and enriches it with
FSQ Places data from PostgreSQL, providing:
- Canonical brand names
- Official websites
- Additional location data
- Chain identification
- Category standardization

Usage:
  python scripts/enrich_tenants_with_fsq.py \
    --input outputs/mecsr/complete_tenants_aggregate.json \
    --output outputs/mecsr/tenants_enriched_with_fsq.json \
    --match-threshold 0.8

Environment Variables:
  POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
"""

from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_db_config() -> dict:
    """Get database configuration from environment variables."""
    return {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5432")),
        "user": os.getenv("POSTGRES_USER", os.getenv("USER")),
        "password": os.getenv("POSTGRES_PASSWORD", ""),
        "database": os.getenv("POSTGRES_DB", "fsq_places"),
    }


def normalize_name(name: str) -> str:
    """Normalize a business name for matching."""
    import re
    
    # Convert to lowercase
    name = name.lower().strip()
    
    # Remove common business suffixes
    suffixes = [
        r'\s+ltd\.?$',
        r'\s+limited$',
        r'\s+inc\.?$',
        r'\s+corp\.?$',
        r'\s+llc$',
        r'\s+&\s+co\.?$',
    ]
    for suffix in suffixes:
        name = re.sub(suffix, '', name, flags=re.IGNORECASE)
    
    # Remove special characters except spaces
    name = re.sub(r'[^\w\s]', '', name)
    
    # Normalize whitespace
    name = re.sub(r'\s+', ' ', name).strip()
    
    return name


def calculate_similarity(name1: str, name2: str) -> float:
    """Calculate similarity between two names using various metrics."""
    from difflib import SequenceMatcher
    
    # Normalize names
    n1 = normalize_name(name1)
    n2 = normalize_name(name2)
    
    # Exact match after normalization
    if n1 == n2:
        return 1.0
    
    # Sequence matcher
    seq_score = SequenceMatcher(None, n1, n2).ratio()
    
    # Token overlap (Jaccard similarity)
    tokens1 = set(n1.split())
    tokens2 = set(n2.split())
    if tokens1 and tokens2:
        intersection = len(tokens1 & tokens2)
        union = len(tokens1 | tokens2)
        jaccard_score = intersection / union if union > 0 else 0
    else:
        jaccard_score = 0
    
    # Weighted combination
    similarity = (seq_score * 0.6) + (jaccard_score * 0.4)
    
    return similarity


def find_fsq_matches(
    conn: psycopg2.extensions.connection,
    tenant_name: str,
    country: Optional[str] = None,
    locality: Optional[str] = None,
    latitude: Optional[float] = None,
    longitude: Optional[float] = None,
    radius_km: float = 0.5,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find potential FSQ matches for a tenant.
    
    Uses multiple strategies:
    1. Exact name match in same locality
    2. Fuzzy name match in same locality
    3. Name match within geographic radius (if coordinates provided)
    4. Fuzzy search across country
    """
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    matches = []
    
    normalized_name = normalize_name(tenant_name)
    
    try:
        # Strategy 1: Exact normalized name match in locality
        if locality:
            cursor.execute("""
                SELECT *,
                       1.0 as match_score,
                       'exact_locality' as match_type
                FROM fsq_places
                WHERE LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9\\s]', '', 'g')) = %s
                  AND LOWER(locality) = %s
                LIMIT %s
            """, (normalized_name, locality.lower(), limit))
            matches.extend(cursor.fetchall())
        
        # Strategy 2: Geographic proximity (if coordinates provided)
        if latitude and longitude and len(matches) < limit:
            cursor.execute("""
                SELECT *,
                       ST_Distance(
                           geom,
                           ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography
                       ) / 1000.0 as distance_km,
                       similarity(LOWER(name), %s) as match_score,
                       'geographic' as match_type
                FROM fsq_places
                WHERE ST_DWithin(
                    geom,
                    ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                    %s * 1000  -- Convert km to meters
                )
                  AND similarity(LOWER(name), %s) > 0.3
                ORDER BY distance_km ASC, match_score DESC
                LIMIT %s
            """, (
                longitude, latitude, tenant_name.lower(),
                longitude, latitude, radius_km,
                tenant_name.lower(), limit - len(matches)
            ))
            matches.extend(cursor.fetchall())
        
        # Strategy 3: Fuzzy text search in country
        if country and len(matches) < limit:
            cursor.execute("""
                SELECT *,
                       similarity(LOWER(name), %s) as match_score,
                       'fuzzy_country' as match_type
                FROM fsq_places
                WHERE country = %s
                  AND similarity(LOWER(name), %s) > 0.5
                ORDER BY match_score DESC
                LIMIT %s
            """, (tenant_name.lower(), country.upper(), tenant_name.lower(), limit - len(matches)))
            matches.extend(cursor.fetchall())
        
        # Strategy 4: Global fuzzy search (last resort)
        if len(matches) < limit:
            cursor.execute("""
                SELECT *,
                       similarity(LOWER(name), %s) as match_score,
                       'fuzzy_global' as match_type
                FROM fsq_places
                WHERE similarity(LOWER(name), %s) > 0.6
                ORDER BY match_score DESC
                LIMIT %s
            """, (tenant_name.lower(), tenant_name.lower(), limit - len(matches)))
            matches.extend(cursor.fetchall())
    
    except Exception as e:
        logger.warning(f"Error finding FSQ matches for '{tenant_name}': {e}")
    finally:
        cursor.close()
    
    return matches


def enrich_tenant(
    conn: psycopg2.extensions.connection,
    tenant: Dict[str, Any],
    match_threshold: float = 0.8
) -> Dict[str, Any]:
    """Enrich a single tenant with FSQ data."""
    enriched = tenant.copy()
    
    # Extract location data
    name = tenant.get("name", "")
    if not name:
        return enriched
    
    # Find FSQ matches
    matches = find_fsq_matches(
        conn,
        tenant_name=name,
        country=tenant.get("country"),
        locality=tenant.get("locality"),
        latitude=tenant.get("latitude"),
        longitude=tenant.get("longitude"),
    )
    
    if not matches:
        enriched["fsq_match"] = None
        enriched["fsq_confidence"] = 0.0
        return enriched
    
    # Get best match
    best_match = matches[0]
    similarity = calculate_similarity(name, best_match["name"])
    
    # Add FSQ enrichment
    enriched["fsq_match"] = {
        "fsq_place_id": best_match["fsq_place_id"],
        "fsq_name": best_match["name"],
        "fsq_website": best_match.get("website"),
        "fsq_email": best_match.get("email"),
        "fsq_phone": best_match.get("phone"),
        "fsq_categories": best_match.get("categories"),
        "fsq_verified": best_match.get("verified"),
        "match_type": best_match.get("match_type"),
        "match_score": float(best_match.get("match_score", 0)),
        "similarity": similarity,
    }
    enriched["fsq_confidence"] = similarity
    
    # If high confidence match, use FSQ data to fill missing fields
    if similarity >= match_threshold:
        if not tenant.get("website") and best_match.get("website"):
            enriched["website"] = best_match["website"]
        if not tenant.get("email") and best_match.get("email"):
            enriched["email"] = best_match["email"]
        if not tenant.get("phone") and best_match.get("phone"):
            enriched["phone"] = best_match["phone"]
    
    return enriched


def load_tenants(path: Path) -> List[Dict[str, Any]]:
    """Load tenant data from JSON file."""
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and "tenants" in data:
            return data["tenants"]
    raise ValueError("Unsupported tenant file format")


def main():
    parser = argparse.ArgumentParser(
        description="Enrich tenant data with FSQ-OS-Places"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Input tenant JSON file"
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output enriched tenant JSON file"
    )
    parser.add_argument(
        "--match-threshold",
        type=float,
        default=0.8,
        help="Similarity threshold for high-confidence matches (0-1)"
    )
    
    args = parser.parse_args()
    
    # Load tenants
    logger.info(f"Loading tenants from {args.input}...")
    tenants = load_tenants(args.input)
    logger.info(f"Loaded {len(tenants)} tenants")
    
    # Connect to database
    config = get_db_config()
    logger.info(f"Connecting to PostgreSQL at {config['host']}:{config['port']}/{config['database']}...")
    conn = psycopg2.connect(**config)
    
    # Enable similarity extension for fuzzy matching
    cursor = conn.cursor()
    cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    conn.commit()
    cursor.close()
    
    # Enrich tenants
    logger.info("Enriching tenants with FSQ data...")
    enriched_tenants = []
    matched = 0
    high_confidence = 0
    
    for i, tenant in enumerate(tenants):
        if (i + 1) % 100 == 0:
            logger.info(f"Processing {i + 1}/{len(tenants)}...")
        
        enriched = enrich_tenant(conn, tenant, args.match_threshold)
        enriched_tenants.append(enriched)
        
        if enriched.get("fsq_match"):
            matched += 1
            if enriched.get("fsq_confidence", 0) >= args.match_threshold:
                high_confidence += 1
    
    conn.close()
    
    # Save enriched data
    logger.info(f"Saving enriched data to {args.output}...")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as f:
        json.dump(enriched_tenants, f, ensure_ascii=False, indent=2)
    
    # Print statistics
    logger.info("\n" + "=" * 60)
    logger.info("ENRICHMENT STATISTICS")
    logger.info("=" * 60)
    logger.info(f"Total tenants:              {len(tenants)}")
    logger.info(f"Matched with FSQ:           {matched} ({matched/len(tenants)*100:.1f}%)")
    logger.info(f"High confidence matches:    {high_confidence} ({high_confidence/len(tenants)*100:.1f}%)")
    logger.info(f"Output saved to:            {args.output}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()




