"""Command-line interface for the tenant scraper.

Adds unified CSV support and temporarily disables the per-tenant details
click path (the flag is accepted but ignored with a warning).
"""

import argparse
import asyncio
import json
import csv
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List
from .scraper import TenantScraper, mall_logging_context


def setup_logging(verbose: bool = False) -> None:
    """Set up logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )


def save_to_json(data: list, output_file: Path) -> None:
    """Save data to JSON file."""
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def save_to_csv(data: list, output_file: Path) -> None:
    """Save data to CSV file."""
    if not data:
        return

    fieldnames = data[0].keys()
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract tenant information from Google Maps mall listings"
    )
    parser.add_argument(
        "urls",
        nargs="*",
        help="Google Maps URL(s) for the mall(s) to scrape"
    )
    parser.add_argument(
        "--csv",
        type=Path,
        help="Optional CSV file (e.g., MECsr) with a 'google_maps_url' and 'name' column"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (extension determines format: .json or .csv)"
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        help="Output format (overrides file extension)"
    )
    parser.add_argument(
        "--aggregate-file",
        type=Path,
        default=None,
        help="When using --csv, optional path to write combined tenants (default inside output dir)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        default=True,
        help="Run browser in headless mode (default: True)"
    )
    parser.add_argument(
        "--no-headless",
        action="store_false",
        dest="headless",
        help="Run browser in visible mode"
    )
    parser.add_argument(
        "--mode",
        choices=["directory", "categories"],
        default="directory",
        help="Extraction mode: 'directory' for main directory view, 'categories' for category-based extraction"
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Temporarily disabled: per-tenant card clicks are deferred"
    )
    parser.add_argument(
        "--no-block-resources",
        action="store_true",
        help="Disable resource blocking (loads all images/media)"
    )
    parser.add_argument(
        "--aggressive-block",
        action="store_true",
        help="Block additional map-related hosts (faster, but only use if directory still renders correctly)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Temporarily disable details path
    if args.details:
        logging.getLogger(__name__).info(
            "--details requested; enabling experimental per-tenant extraction (may increase runtime)."
        )

    # Validate input source
    if not args.urls and not args.csv:
        raise SystemExit("Provide Google Maps URL(s) or --csv path")
    if args.urls and args.csv:
        raise SystemExit("Provide either URL(s) or --csv, not both")

    # Determine output format
    if args.format:
        output_format = args.format
    elif args.output and args.output.suffix.lower() == '.csv' and args.urls and len(args.urls) == 1:
        output_format = 'csv'
    else:
        output_format = 'json'

    output_paths = []
    if args.urls:
        if len(args.urls) == 1:
            if args.output:
                output_paths.append(args.output)
            else:
                output_paths.append(Path(f"tenants.{output_format}"))
        else:
            if args.output and args.output.suffix:
                raise SystemExit("When providing multiple URLs, --output must point to a directory")

            base_dir = args.output or Path("outputs")
            base_dir.mkdir(parents=True, exist_ok=True)

            from urllib.parse import urlparse
            import re

            for idx, url in enumerate(args.urls, start=1):
                parsed = urlparse(url)
                slug_source = f"{parsed.netloc}{parsed.path}" or f"mall_{idx}"
                slug = re.sub(r"[^a-zA-Z0-9]+", "-", slug_source).strip("-") or f"mall-{idx}"
                output_paths.append(base_dir / f"{slug}.{output_format}")

    async def run_scraper():
        try:
            scraper = TenantScraper(
                headless=args.headless,
                block_resources=not args.no_block_resources,
                aggressive_block=args.aggressive_block,
            )

            async with scraper:
                if args.urls:
                    # URL mode
                    for url, destination in zip(args.urls, output_paths):
                        print(f"Scraping tenants from: {url} (mode: {args.mode})")
                        if args.mode == "directory":
                            with mall_logging_context(destination.stem):
                                tenants = await scraper._scrape_tenants_from_directory(
                                    url,
                                    fetch_details=args.details,
                                )
                        else:
                            tenants = await scraper._scrape_tenants_by_categories(url)

                        if output_format == 'json':
                            save_to_json(tenants, destination)
                        else:
                            save_to_csv(tenants, destination)

                        print(f"Extracted {len(tenants)} tenants")
                        print(f"Results saved to: {destination}")
                else:
                    # CSV mode
                    import pandas as pd
                    csv_path = args.csv.expanduser().resolve()
                    if not csv_path.exists():
                        raise SystemExit(f"CSV file not found: {csv_path}")

                    df = pd.read_csv(csv_path)
                    if 'google_maps_url' not in df.columns or 'name' not in df.columns:
                        raise SystemExit("CSV must contain 'name' and 'google_maps_url' columns")

                    rows = df[['name', 'google_maps_url']].dropna()
                    rows = rows.drop_duplicates(subset='google_maps_url').reset_index(drop=True)

                    base_dir = args.output or Path("outputs") / "mecsr"
                    base_dir.mkdir(parents=True, exist_ok=True)

                    aggregate_path = args.aggregate_file or (base_dir / "tenants_aggregate.json")
                    aggregated: List[Dict[str, Any]] = []

                    def slugify(value: str) -> str:
                        import re as _re
                        return _re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-") or "mall"

                    for idx, (mall_name, url) in enumerate(rows.itertuples(index=False), start=1):
                        mall_name = str(mall_name).strip()
                        url = str(url).strip()
                        if not url:
                            print(f"[{idx}/{len(rows)}] Skipping {mall_name} (missing URL)")
                            continue

                        dest = base_dir / f"{slugify(mall_name or f'mall-{idx}')}.{output_format}"
                        print(f"[{idx}/{len(rows)}] Scraping {mall_name} -> {url}")

                        try:
                            with mall_logging_context(mall_name):
                                tenants = await scraper._scrape_tenants_from_directory(
                                    url,
                                    fetch_details=args.details,
                                )
                        except Exception as exc:
                            print(f"  ✗ Failed: {exc}")
                            continue

                        for t in tenants:
                            t['mall_name'] = mall_name
                            t['source_url'] = url
                        aggregated.extend(tenants)

                        if output_format == 'json':
                            save_to_json(tenants, dest)
                        else:
                            save_to_csv(tenants, dest)

                        print(f"  ✓ {len(tenants)} tenants written to {dest}")

                    # Write aggregate
                    if aggregated:
                        if aggregate_path.suffix.lower() == '.csv':
                            save_to_csv(aggregated, aggregate_path)
                        else:
                            save_to_json(aggregated, aggregate_path)
                        print(f"Aggregated {len(aggregated)} tenants saved to {aggregate_path}")

        except KeyboardInterrupt:
            print("\nScraping interrupted by user")
            sys.exit(1)
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            if args.verbose:
                import traceback
                traceback.print_exc()
            sys.exit(1)

    # Run the async scraper
    asyncio.run(run_scraper())


if __name__ == "__main__":
    main()
