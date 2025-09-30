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
        "urls",
        nargs="+",
        help="Google Maps URL(s) for the mall(s) to scrape"
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
        "--details",
        action="store_true",
        help="After loading the directory, click through tenant cards to gather detailed info (uses same browser session)"
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

    # Determine output format
    if args.format:
        output_format = args.format
    elif args.output and args.output.suffix.lower() == '.csv' and len(args.urls) == 1:
        output_format = 'csv'
    else:
        output_format = 'json'

    output_paths = []
    if len(args.urls) == 1:
        if args.output:
            output_paths.append(args.output)
        else:
            output_paths.append(Path(f"tenants.{output_format}"))
    else:
        if args.output and args.output.suffix:
            raise SystemExit("When providing multiple URLs, --output must point to a directory")

        base_dir = args.output or Path("tenants_outputs")
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
                for url, destination in zip(args.urls, output_paths):
                    print(f"Scraping tenants from: {url} (mode: {args.mode})")
                    if args.mode == "directory":
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
