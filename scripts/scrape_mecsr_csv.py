"""Batch scraper for MECsr mall list."""

import argparse
import asyncio
import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

from tenant_scraper.scraper import TenantScraper, mall_logging_context


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = PROJECT_ROOT / "data" / "mecsr_malls_with_google_urls.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "mecsr"
DEFAULT_AGGREGATE_FILENAME = "tenants_aggregate.json"


if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='%(message)s')


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return slug or "mall"


async def scrape_malls(csv_path: Path, output_dir: Path, fetch_details: bool = False) -> List[Dict[str, Any]]:
    df = pd.read_csv(csv_path)

    if 'google_maps_url' not in df.columns or 'name' not in df.columns:
        raise ValueError("CSV must contain 'name' and 'google_maps_url' columns")

    rows = df[['name', 'google_maps_url']].dropna()
    rows = rows.drop_duplicates(subset='google_maps_url').reset_index(drop=True)
    print(f"Loaded {len(rows)} malls from {csv_path}")
    output_dir.mkdir(parents=True, exist_ok=True)

    aggregated: List[Dict[str, Any]] = []

    scraper = TenantScraper()
    async with scraper:
        for idx, (mall_name, url) in enumerate(rows.itertuples(index=False), start=1):
            mall_name = str(mall_name).strip()
            url = str(url).strip()
            if not url:
                print(f"[{idx}/{len(rows)}] Skipping {mall_name} (missing URL)")
                continue

            print(f"[{idx}/{len(rows)}] Scraping {mall_name} -> {url}")

            mall_slug = slugify(mall_name or f"mall-{idx}")
            destination = output_dir / f"{mall_slug}.json"

            if destination.exists():
                print(f"  → Skipping (already scraped)")
                continue

            try:
                with mall_logging_context(mall_name):
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
    parser.add_argument(
        "csv",
        nargs="?",
        type=Path,
        default=DEFAULT_CSV,
        help=f"Path to mecsr_malls_with_google_urls.csv (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Directory to store per-mall tenant files (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Also scrape tenant detail pages",
    )
    parser.add_argument(
        "--aggregate-file",
        type=Path,
        default=None,
        help="Optional path to write combined tenants (default inside output dir)",
    )

    args = parser.parse_args()
    csv_path = args.csv.expanduser().resolve()
    if not csv_path.exists():
        parser.error(f"CSV file not found: {csv_path}")

    output_dir = args.output_dir.expanduser()
    aggregate_file = args.aggregate_file
    if aggregate_file is None:
        aggregate_file = output_dir / DEFAULT_AGGREGATE_FILENAME
    else:
        aggregate_file = aggregate_file.expanduser()

    print(f"Saving per-mall outputs to {output_dir}")
    print(f"Aggregate output will be written to {aggregate_file}")

    aggregated = asyncio.run(scrape_malls(csv_path, output_dir, fetch_details=args.details))

    if aggregated:
        aggregate_file.parent.mkdir(parents=True, exist_ok=True)
        with aggregate_file.open('w', encoding='utf-8') as handle:
            json.dump(aggregated, handle, ensure_ascii=False, indent=2)
        print(f"Aggregated {len(aggregated)} tenants saved to {aggregate_file}")
    else:
        print("No tenants were scraped; aggregate file not written.")


if __name__ == "__main__":
    main()
