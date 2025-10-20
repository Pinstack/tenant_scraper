# Tenant Scraper

A tool to automatically extract tenant/brand information from shopping mall listings on Google Maps.

## ✅ Current Status: WORKING

**Success**: Google Maps anti-automation blocker has been bypassed! The scraper now successfully extracts tenant data by simulating user interactions to access directory content.

## Features

- ✅ Automatically handles Google Maps consent pages
- ✅ Manipulates URLs to access directory view
- ✅ Scrolls through directory to reveal all individual tenants (**infinite scroll enhancement needed for large malls**)
- ✅ Extracts comprehensive tenant information:
  - Name and category
  - Rating and status
  - Floor/unit location
  - Phone number and individual map links
- ✅ Outputs structured data (JSON/CSV)
- ✅ Extracts mall business categories and tenant counts
- ✅ **NEW: FSQ-OS-Places enrichment** - Enrich scraped data with Foursquare's global POI database (100M+ venues)

## Installation

1. Clone or download this repository
2. Create a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Install Playwright browsers:
   ```bash
   playwright install chromium
   ```
5. Install the package:
   ```bash
   pip install -e .
   ```

## Usage

### Command Line

#### Single Mall
```bash
tenant-scraper "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A" -o output.json
```

#### Multiple Malls
```bash
tenant-scraper "https://maps.app.goo.gl/..." "https://maps.app.goo.gl/..." "https://maps.app.goo.gl/..."
```
When providing multiple URLs, the scraper creates an `outputs/` directory and saves each mall to a separate file named after the domain.

#### Batch Processing (CSV)
```bash
# Use the unified CLI with --csv
tenant-scraper --csv data/mecsr_malls_with_google_urls.csv --output outputs/mecsr

# Optionally also write an aggregate file
tenant-scraper --csv data/mecsr_malls_with_google_urls.csv \
  --output outputs/mecsr \
  --aggregate-file outputs/mecsr/tenants_aggregate.json
```
Processes all malls listed in a CSV file with Google Maps URLs. Creates individual files for each mall plus an aggregated results file.

### Python API

```python
import asyncio
from tenant_scraper import TenantScraper

async def main():
    async with TenantScraper(headless=True) as scraper:
        tenants = await scraper.scrape_tenants("https://maps.app.goo.gl/FsGevWWrjvab4tZ9A")

        for tenant in tenants:
            print(f"{tenant['name']} - {tenant['category']}")

asyncio.run(main())
```

## Command Line Options

- `urls`: Google Maps URL(s) for the mall(s) to scrape (zero or more)
- `--csv`: CSV file with `name` and `google_maps_url` columns for batch mode
- `-o, --output`: Output file (single URL) or directory (multiple URLs or CSV)
- `--aggregate-file`: When using `--csv`, path to write a combined JSON/CSV file
- `--format`: Output format (json/csv, auto-detected from file extension)
- `--headless`: Run in headless mode (default: True)
- `--no-headless`: Run with visible browser window
- `--mode`: Extraction mode ('directory' or 'categories', default: 'directory')
- `--details`: Temporarily disabled (card-click detail extraction deferred)
- `--no-block-resources`: Disable resource blocking for debugging
- `--aggressive-block`: Block additional map-related resources for faster scraping
- `-v, --verbose`: Enable verbose logging

### Error Handling

- **No input provided**: Provide URL(s) or `--csv`
- **Invalid URL**: Must be a valid Google Maps place URL
- **Network issues**: Check internet connectivity
- **Large malls**: May require longer processing time for complete tenant extraction

## Output Format

The scraper outputs structured data with the following fields:

```json
[
  {
    "name": "Store Name",
    "category": "Retail",
    "rating": 4.5,
    "floor_unit": "Level 2",
    "status": "open",
    "phone": "+1-555-0123",
    "maps_link": "https://maps.google.com/..."
  }
]
```

## Development

### Setup Development Environment

```bash
pip install -r requirements.txt
pip install black flake8 vulture pytest  # Development tools
```

### Run Tests

```bash
pytest
```

### Code Quality

```bash
black src/  # Format code
flake8 src/  # Lint code
vulture src/  # Find dead code
```

## Troubleshooting

### ✅ Issue Resolved: Directory Access Working

The Google Maps anti-automation blocker has been successfully bypassed using user interaction simulation.

**Solution Implemented:**
- Load original mall URL → Handle consent → Click "View all" button
- This simulates the exact user workflow that triggers directory loading
- URL changes to include `!10e3` parameter after "View all" click
- Directory categories and tenant counts are successfully extracted

**If you encounter issues:**
- Ensure Playwright is properly installed: `pip install playwright && playwright install`
- Check that the mall URL is a valid Google Maps place URL
- Verify internet connectivity for Google Maps access
- **For large malls**: The current implementation may miss tenant categories if infinite scroll isn't fully implemented

## FSQ-OS-Places Integration

Enhance your scraped tenant data with Foursquare's comprehensive global POI database:

### Quick Start
```bash
# One-command setup with sample data
python scripts/quickstart_fsq.py

# Enrich your scraped tenants
python scripts/enrich_tenants_with_fsq.py \
  --input outputs/mecsr/complete_tenants_aggregate.json \
  --output outputs/mecsr/tenants_enriched.json
```

### What You Get
- **Canonical brand names** and official websites
- **Contact information** (phone, email)
- **Category standardization** across data sources
- **Business verification** and freshness dates
- **Chain identification** and store counts

### Data Access
1. **Request access** to FSQ-OS-Places: https://huggingface.co/datasets/foursquare/fsq-os-places
2. **Download** the 11.3GB parquet dataset
3. **Load into PostgreSQL** with spatial indexing
4. **Enrich** your scraped data automatically

See `docs/FSQ_INTEGRATION.md` for complete setup and usage instructions.

## Contributing

The core scraping functionality is now working! Contributions are welcome for:
- Additional data extraction fields (more detailed business info)
- Support for different mall types and layouts
- Performance optimizations
- Error handling improvements
- Documentation and testing enhancements
- FSQ-OS-Places integration improvements

## License

MIT License - see LICENSE file for details.
