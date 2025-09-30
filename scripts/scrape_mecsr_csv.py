"""Batch scraper for MECsr mall list."""

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import List, Dict

import pandas as pd

from tenant_scraper.scraper import TenantScraper


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return slug or "mall"


async def scrape_malls(csv_path: Path, output_dir: Path, fetch_details: bool = False) -> List[Dict[str, any]]:
    df = pd.read_csv(csv_path)

    if 'google_maps_url' not in df.columns or 'name' not in df.columns:
        raise ValueError("CSV must contain 'name' and 'google_maps_url' columns")

    rows = df[['name', 'google_maps_url']].dropna()
    output_dir.mkdir(parents=True, exist_ok=True)

    aggregated: List[Dict[str, any]] = []

    scraper = TenantScraper()
    async with scraper:
        for idx, (mall_name, url) in enumerate(rows.itertuples(index=False), start=1):
            mall_name = str(mall_name).strip()
            url = str(url).strip()
            if not url:
                continue

            print(f"[{idx}/{len(rows)}] Scraping {mall_name} -> {url}")

            mall_slug = slugify(mall_name or f"mall-{idx}")
            destination = output_dir / f"{mall_slug}.json"

            if destination.exists():
                print(f"  → Skipping (already scraped)")
                continue

            try:
                tenants = await scraper._scrape_tenants_from_directory(
                    url,
                    fetch_details=fetch_details,
                )
            except Exception as exc:
                print(f"  ✗ Failed: {exc}")
                continue

            for tenant in tenants:
                tenant['mall_name'] = mall_name
                tenant['source_url'] = url

            aggregated.extend(tenants)

            with destination.open('w', encoding='utf-8') as handle:
                json.dump(tenants, handle, ensure_ascii=False, indent=2)

            print(f"  ✓ {len(tenants)} tenants written to {destination}")

    return aggregated


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape all malls in MECsr CSV")
    parser.add_argument("csv", type=Path, help="Path to mecsr_malls_with_google_urls.csv")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("batch_outputs"),
        help="Directory to store per-mall tenant files",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Also scrape tenant detail pages",
    )
    parser.add_argument(
        "--aggregate-file",
        type=Path,
        default=Path("batch_outputs/tenants_aggregate.json"),
        help="Optional path to write combined tenants",
    )

    args = parser.parse_args()

    aggregated = asyncio.run(scrape_malls(args.csv, args.output_dir, fetch_details=args.details))

    if aggregated:
        args.aggregate_file.parent.mkdir(parents=True, exist_ok=True)
        with args.aggregate_file.open('w', encoding='utf-8') as handle:
            json.dump(aggregated, handle, ensure_ascii=False, indent=2)
        print(f"Aggregated {len(aggregated)} tenants saved to {args.aggregate_file}")


if __name__ == "__main__":
    main()
