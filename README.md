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
python scripts/scrape_mecsr_csv.py
python scripts/scrape_mecsr_csv.py custom_malls.csv --output-dir results/
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

- `urls`: Google Maps URL(s) for the mall(s) to scrape (**required**, one or more)
- `-o, --output`: Output file path (for single URL) or directory (for multiple URLs)
- `--format`: Output format (json/csv, auto-detected from file extension)
- `--headless`: Run in headless mode (default: True)
- `--no-headless`: Run with visible browser window
- `--mode`: Extraction mode ('directory' or 'categories', default: 'directory')
- `--details`: Extract detailed contact info from individual tenant cards
- `--no-block-resources`: Disable resource blocking for debugging
- `--aggressive-block`: Block additional map-related resources for faster scraping
- `-v, --verbose`: Enable verbose logging

### Error Handling

- **No URLs provided**: The scraper requires at least one Google Maps URL
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

## Contributing

The core scraping functionality is now working! Contributions are welcome for:
- Additional data extraction fields (more detailed business info)
- Support for different mall types and layouts
- Performance optimizations
- Error handling improvements
- Documentation and testing enhancements

## License

MIT License - see LICENSE file for details.
