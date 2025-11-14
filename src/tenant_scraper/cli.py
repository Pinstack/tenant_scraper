"""Command-line interface for the tenant scraper.

Adds unified CSV support and temporarily disables the per-tenant details
click path (the flag is accepted but ignored with a warning).
"""

import argparse
import asyncio
import csv
import json
import logging
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence
from urllib.parse import urlparse
from .scraper import TenantScraper, mall_logging_context


def slugify(value: str, fallback: str = "mall") -> str:
    """Create a filesystem-friendly slug from arbitrary text."""

    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value).strip("-")
    return slug or fallback


def determine_output_format(args: argparse.Namespace) -> str:
    """Resolve the desired output format based on CLI flags."""

    if args.format:
        return args.format
    if args.output and args.urls and len(args.urls) == 1 and args.output.suffix.lower() == ".csv":
        return "csv"
    return "json"


def build_parser() -> argparse.ArgumentParser:
    """Build the shared CLI argument parser."""

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
        help="Optional CSV file with 'google_maps_url' and 'name' columns"
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        help="Output file path (single URL) or directory (multiple URLs/CSV)"
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
        help="Extraction mode: 'directory' (default) or 'categories'"
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help=(
            "Enable per-tenant detail extraction by clicking each card. "
            "Extracts phone, website, hours, and address using deterministic selectors. "
            "Adds ~2-4s per tenant (throttling + page loads). "
            "Use for malls with <50 tenants or combine with limits for larger malls."
        )
    )
    parser.add_argument(
        "--no-block-resources",
        action="store_true",
        help="Disable resource blocking (loads all images/media)"
    )
    parser.add_argument(
        "--aggressive-block",
        action="store_true",
        help="Block additional map-related hosts (faster; use only if directory still renders correctly)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser


def prepare_output_paths(
    urls: Sequence[str],
    output_format: str,
    requested_output: Optional[Path],
) -> List[Path]:
    """Create per-URL output destinations, handling slugification for multiples."""

    if not urls:
        return []

    if len(urls) == 1:
        if requested_output:
            return [requested_output]
        return [Path(f"tenants.{output_format}")]

    if requested_output and requested_output.suffix:
        raise SystemExit("When providing multiple URLs, --output must point to a directory")

    base_dir = requested_output or Path("outputs")
    base_dir.mkdir(parents=True, exist_ok=True)

    destinations: List[Path] = []
    for idx, url in enumerate(urls, start=1):
        parsed = urlparse(url)
        slug_source = f"{parsed.netloc}{parsed.path}" or f"mall_{idx}"
        slug = slugify(slug_source, fallback=f"mall-{idx}")
        destinations.append(base_dir / f"{slug}.{output_format}")
    return destinations


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


def write_output(data: List[Dict[str, Any]], destination: Path, output_format: str) -> None:
    """Persist scraped tenants to the requested format."""

    if output_format == 'csv':
        save_to_csv(data, destination)
    else:
        save_to_json(data, destination)


async def scrape_urls(
    scraper: TenantScraper,
    urls: Sequence[str],
    destinations: Sequence[Path],
    *,
    output_format: str,
    extraction_mode: str,
    fetch_details: bool,
) -> None:
    """Scrape one or more URLs and persist to disk."""

    for url, destination in zip(urls, destinations):
        print(f"Scraping tenants from: {url} (mode: {extraction_mode})")
        with mall_logging_context(destination.stem):
            tenants = await scraper.scrape_tenants(
                url,
                extraction_mode=extraction_mode,
                fetch_details=fetch_details,
            )

        write_output(tenants, destination, output_format)
        print(f"Extracted {len(tenants)} tenants")
        print(f"Results saved to: {destination}")


async def scrape_csv(
    scraper: TenantScraper,
    *,
    csv_path: Path,
    base_dir: Path,
    output_format: str,
    aggregate_path: Path,
    fetch_details: bool,
    extraction_mode: str,
) -> List[Dict[str, Any]]:
    """Process a CSV manifest of malls and persist per-mall plus aggregate results."""

    import pandas as pd  # Local import to avoid requiring pandas for URL-only usage

    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    df = pd.read_csv(csv_path)
    if 'google_maps_url' not in df.columns or 'name' not in df.columns:
        raise SystemExit("CSV must contain 'name' and 'google_maps_url' columns")

    rows = df[['name', 'google_maps_url']].dropna()
    rows = rows.drop_duplicates(subset='google_maps_url').reset_index(drop=True)

    base_dir.mkdir(parents=True, exist_ok=True)
    aggregate_path.parent.mkdir(parents=True, exist_ok=True)

    aggregated: List[Dict[str, Any]] = []

    for idx, (mall_name, url) in enumerate(rows.itertuples(index=False), start=1):
        mall_name = str(mall_name).strip()
        url = str(url).strip()
        if not url:
            print(f"[{idx}/{len(rows)}] Skipping {mall_name} (missing URL)")
            continue

        destination = base_dir / f"{slugify(mall_name or f'mall-{idx}')}.{output_format}"
        print(f"[{idx}/{len(rows)}] Scraping {mall_name} -> {url}")

        try:
            with mall_logging_context(mall_name):
                tenants = await scraper.scrape_tenants(
                    url,
                    extraction_mode=extraction_mode,
                    fetch_details=fetch_details,
                )
        except Exception as exc:  # pragma: no cover - runtime logging aid
            print(f"  ✗ Failed: {exc}")
            continue

        for tenant in tenants:
            tenant['mall_name'] = mall_name
            tenant['source_url'] = url
        aggregated.extend(tenants)

        write_output(tenants, destination, output_format)
        print(f"  ✓ {len(tenants)} tenants written to {destination}")

    if aggregated:
        write_output(aggregated, aggregate_path, 'csv' if aggregate_path.suffix.lower() == '.csv' else 'json')
        print(f"Aggregated {len(aggregated)} tenants saved to {aggregate_path}")
    else:
        print("No tenants were scraped; aggregate file not written.")

    return aggregated


async def run_cli(args: argparse.Namespace) -> None:
    """Execute the scraper with either explicit URLs or a CSV manifest."""

    try:
        scraper = TenantScraper(
            headless=args.headless,
            block_resources=not args.no_block_resources,
            aggressive_block=args.aggressive_block,
        )

        output_format = determine_output_format(args)

        async with scraper:
            if args.urls:
                destinations = prepare_output_paths(args.urls, output_format, args.output)
                await scrape_urls(
                    scraper,
                    args.urls,
                    destinations,
                    output_format=output_format,
                    extraction_mode=args.mode,
                    fetch_details=args.details,
                )
            else:
                base_dir = args.output or (Path("outputs") / "mecsr")
                aggregate_path = args.aggregate_file or (base_dir / "tenants_aggregate.json")
                csv_path = args.csv.expanduser().resolve() if args.csv else None
                if not csv_path:
                    raise SystemExit("CSV path is required when no URLs are provided")

                await scrape_csv(
                    scraper,
                    csv_path=csv_path,
                    base_dir=base_dir,
                    output_format=output_format,
                    aggregate_path=aggregate_path,
                    fetch_details=args.details,
                    extraction_mode=args.mode,
                )

    except KeyboardInterrupt:
        print("\nScraping interrupted by user")
        raise SystemExit(1) from None
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        raise SystemExit(1) from exc


def main() -> None:
    """Main CLI entry point."""

    parser = build_parser()
    args = parser.parse_args()

    setup_logging(args.verbose)

    if args.details:
        logging.getLogger(__name__).info(
            "--details requested; enabling experimental per-tenant extraction (may increase runtime)."
        )

    if not args.urls and not args.csv:
        raise SystemExit("Provide Google Maps URL(s) or --csv path")
    if args.urls and args.csv:
        raise SystemExit("Provide either URL(s) or --csv, not both")

    asyncio.run(run_cli(args))


if __name__ == "__main__":
    main()
