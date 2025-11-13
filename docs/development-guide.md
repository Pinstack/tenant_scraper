# Tenant Scraper - Development Guide

**Generated:** 2025-11-13

## Prerequisites

- **Python:** 3.9 or higher
- **pip:** Python package manager
- **Playwright:** Browser automation framework (installed via pip)
- **Git:** Version control (optional)

## Environment Setup

### 1. Clone Repository

```bash
git clone <repository-url>
cd tenant_scraper
```

### 2. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install Playwright Browsers

```bash
playwright install chromium
```

### 5. Install Package in Development Mode

```bash
pip install -e .
```

This installs the package in editable mode, so changes to source code are immediately available.

## Local Development

### Running the CLI

#### Single Mall Scraping

```bash
tenant-scraper "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A" -o output.json
```

#### Batch Processing (CSV)

```bash
tenant-scraper --csv data/mecsr_malls_with_google_urls.csv --output outputs/mecsr
```

#### Verbose Logging

```bash
tenant-scraper "https://maps.app.goo.gl/..." -v -o output.json
```

### Using the Python API

```python
import asyncio
from tenant_scraper import TenantScraper

async def main():
    async with TenantScraper(headless=True) as scraper:
        # Directory mode (default) - extracts all tenants
        tenants = await scraper.scrape_tenants(
            "https://maps.app.goo.gl/...",
            extraction_mode="directory"
        )
        
        # Categories mode - extracts by processing each category
        tenants = await scraper.scrape_tenants(
            "https://maps.app.goo.gl/...",
            extraction_mode="categories"
        )
        
        for tenant in tenants:
            print(f"{tenant['name']} - {tenant['category']}")

asyncio.run(main())
```

## Build Process

### Package Installation

```bash
pip install -e .
```

### Distribution Build (if needed)

```bash
python setup.py sdist bdist_wheel
```

## Testing

### Run All Tests

```bash
pytest
```

### Run Specific Test File

```bash
pytest tests/test_scraper.py
```

### Run with Verbose Output

```bash
pytest -v
```

### Run with Coverage

```bash
pytest --cov=src/tenant_scraper --cov-report=html
```

## Code Quality

### Format Code

```bash
black src/
```

### Lint Code

```bash
flake8 src/
```

### Find Dead Code

```bash
vulture src/
```

## Common Development Tasks

### Adding New Extraction Fields

1. Modify `_extract_tenants_from_dom()` in `scraper.py`
2. Update `DirectoryTextExtractor.extract_tenants_from_text()` if using text fallback
3. Update tests to cover new fields
4. Update CLI output formatting if needed

### Adding New CLI Options

1. Modify `argparse` setup in `cli.py` `main()` function
2. Pass options to `TenantScraper` constructor or methods
3. Update `ScraperSettings` if needed
4. Add tests for new options

### Debugging

#### Enable Verbose Logging

```bash
tenant-scraper -v "https://maps.app.goo.gl/..." -o output.json
```

#### Run with Visible Browser

```bash
tenant-scraper --no-headless "https://maps.app.goo.gl/..." -o output.json
```

#### Disable Resource Blocking (for debugging)

Modify `ScraperSettings` or use CLI options to disable blocking.

## Project Structure

- **Source Code:** `src/tenant_scraper/`
- **Tests:** `tests/`
- **Scripts:** `scripts/`
- **Documentation:** `docs/`
- **Data:** `data/`
- **Outputs:** `outputs/`

## Dependencies

See `requirements.txt` for complete list. Key dependencies:

- `playwright>=1.40.0` - Browser automation
- `pandas>=2.0.0` - Data processing
- `pytest>=7.4.0` - Testing framework

## Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/new-feature
   ```

2. **Make Changes**
   - Write code
   - Add tests
   - Update documentation

3. **Test Changes**
   ```bash
   pytest
   black src/
   flake8 src/
   ```

4. **Commit Changes**
   ```bash
   git add .
   git commit -m "Add new feature"
   ```

5. **Run Integration Tests**
   - Test with real Google Maps URLs
   - Verify output format

## Troubleshooting

### Playwright Installation Issues

```bash
playwright install --force chromium
```

### Import Errors

Ensure package is installed in editable mode:
```bash
pip install -e .
```

### Browser Launch Failures

- Check Playwright installation
- Verify system dependencies
- Try running with `--no-headless` to see browser

### Google Maps Blocking

- The scraper handles consent pages automatically
- If issues persist, check user agent and browser args in `_setup_browser()`

## Contributing

### Code Style

- Follow PEP 8
- Use `black` for formatting
- Run `flake8` before committing

### Testing

- Write tests for new features
- Ensure all tests pass before submitting
- Add integration tests for complex features

### Documentation

- Update README.md for user-facing changes
- Update docstrings for API changes
- Add examples for new features

## Next Steps

- Review [Architecture Documentation](./architecture.md) for system design
- Check [Source Tree Analysis](./source-tree-analysis.md) for code organization
- See README.md for usage examples

