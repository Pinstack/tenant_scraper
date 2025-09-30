"""Command-line interface for the tenant scraper."""

import argparse
import asyncio
import json
import csv
import logging
import sys
from pathlib import Path
from .scraper import TenantScraper


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
        "url",
        help="Google Maps URL for the mall to scrape"
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
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)

    # Determine output format
    if args.format:
        output_format = args.format
    elif args.output:
        if args.output.suffix.lower() == '.csv':
            output_format = 'csv'
        else:
            output_format = 'json'
    else:
        output_format = 'json'

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        output_file = Path(f"tenants.{output_format}")

    async def run_scraper():
        try:
            # Initialize scraper
            scraper = TenantScraper(headless=args.headless)

            # Scrape data
            print(f"Scraping tenants from: {args.url} (mode: {args.mode})")
            tenants = await scraper.scrape_tenants(args.url, args.mode)

            # Save results
            if output_format == 'json':
                save_to_json(tenants, output_file)
            else:
                save_to_csv(tenants, output_file)

            print(f"Extracted {len(tenants)} tenants")
            print(f"Results saved to: {output_file}")

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
