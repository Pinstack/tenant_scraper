"""Batch scraper for MECsr mall list (thin wrapper around tenant_scraper.cli helpers)."""

import argparse
import asyncio
import logging
from pathlib import Path

from tenant_scraper.cli import scrape_csv
from tenant_scraper.scraper import TenantScraper


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CSV = PROJECT_ROOT / "data" / "mecsr_malls_with_google_urls.csv"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "outputs" / "mecsr"
DEFAULT_AGGREGATE_FILENAME = "tenants_aggregate.json"


if not logging.getLogger().handlers:
    logging.basicConfig(level=logging.INFO, format='%(message)s')


def build_parser() -> argparse.ArgumentParser:
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
        "--aggregate-file",
        type=Path,
        default=None,
        help="Optional path to write combined tenants (default inside output dir)",
    )
    parser.add_argument(
        "--details",
        action="store_true",
        help="Also scrape tenant detail pages",
    )
    return parser


async def run(args: argparse.Namespace) -> None:
    csv_path = args.csv.expanduser().resolve()
    if not csv_path.exists():
        raise SystemExit(f"CSV file not found: {csv_path}")

    output_dir = args.output_dir.expanduser()
    aggregate_file = (args.aggregate_file or (output_dir / DEFAULT_AGGREGATE_FILENAME)).expanduser()

    print(f"Saving per-mall outputs to {output_dir}")
    print(f"Aggregate output will be written to {aggregate_file}")

    scraper = TenantScraper()
    async with scraper:
        await scrape_csv(
            scraper,
            csv_path=csv_path,
            base_dir=output_dir,
            output_format="json",
            aggregate_path=aggregate_file,
            fetch_details=args.details,
            extraction_mode="directory",
        )


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
