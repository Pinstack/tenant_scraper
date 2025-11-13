# Tenant Scraper - Documentation Index

**Generated:** 2025-11-13  
**Master AI Entry Point**

## Project Overview

- **Type:** CLI Tool (Python)
- **Architecture:** Monolith
- **Primary Language:** Python 3.9+
- **Framework:** Playwright (Browser Automation)

## Quick Reference

- **Tech Stack:** Python 3.9+, Playwright, Pandas, asyncio
- **Entry Point:** `tenant_scraper.cli:main` (CLI command: `tenant-scraper`)
- **Architecture Pattern:** CLI Tool with Async Core
- **Package Location:** `src/tenant_scraper/`

## Generated Documentation

- [Project Overview](./project-overview.md) - Executive summary and high-level overview
- [Product Requirements Document](./PRD.md) - Product requirements, current features, and future vision
- [Architecture Documentation](./architecture.md) - Detailed system architecture, patterns, and solution design
- [Source Tree Analysis](./source-tree-analysis.md) - Directory structure and organization
- [Development Guide](./development-guide.md) - Setup, testing, and development workflow
- [Implementation Readiness Report](./implementation-readiness-report-2025-11-13.md) - Validation of PRD and Architecture alignment

## Existing Documentation

- [README.md](../README.md) - User-facing documentation and usage guide
- [FSQ Integration Guide](./FSQ_INTEGRATION.md) - Foursquare OS Places integration

## Project Structure

```
tenant_scraper/
├── src/tenant_scraper/    # Main package (scraper.py, cli.py)
├── tests/                 # Test suite
├── scripts/               # Utility scripts
├── docs/                  # Documentation (this directory)
├── data/                  # Data files
└── outputs/               # Generated outputs
```

## Key Components

### Core Modules

- **`scraper.py`** (~2900 lines) - Main scraping logic
  - `TenantScraper` - Main scraper class
  - `ScraperSettings` - Configuration
  - `DirectoryTextExtractor` - Text extraction fallback
  
- **`cli.py`** (~275 lines) - Command-line interface
  - `main()` - Entry point
  - Argument parsing and output formatting

### Entry Points

- **CLI:** `tenant-scraper` command (via setuptools)
- **Python API:** `from tenant_scraper import TenantScraper`

## Getting Started

1. **Setup:** See [Development Guide](./development-guide.md) for environment setup
2. **Usage:** See README.md for command-line usage examples
3. **Architecture:** See [Architecture Documentation](./architecture.md) for system design
4. **Development:** See [Development Guide](./development-guide.md) for development workflow

## Technology Stack Summary

| Category | Technology |
|----------|-----------|
| Language | Python 3.9+ |
| Browser Automation | Playwright |
| Data Processing | Pandas |
| Async Framework | asyncio |
| Testing | pytest |

## Key Features

- Google Maps tenant data extraction (name, category, rating, location, phone)
- Automatic consent page handling
- Directory view navigation via "View all" button
- Dual extraction modes: directory view and category-based
- Multiple output formats (JSON, CSV)
- Batch processing from CSV input
- FSQ-OS-Places integration (via scripts)
- Resource blocking for performance optimization

## Development Workflow

1. Install dependencies: `pip install -r requirements.txt`
2. Install Playwright browsers: `playwright install chromium`
3. Install package: `pip install -e .`
4. Run tests: `pytest`
5. Format code: `black src/`
6. Lint code: `flake8 src/`

## Next Steps for AI-Assisted Development

When planning new features or modifications:

1. **Review Architecture:** Start with [Architecture Documentation](./architecture.md) to understand system design
2. **Check Source Tree:** See [Source Tree Analysis](./source-tree-analysis.md) for code organization
3. **Review Development Guide:** See [Development Guide](./development-guide.md) for setup and testing
4. **Examine Existing Code:** Review `src/tenant_scraper/scraper.py` for implementation patterns

## Documentation Status

✅ **Complete Documentation:**
- Project Overview
- Product Requirements Document (PRD)
- Architecture Documentation
- Source Tree Analysis
- Development Guide
- Implementation Readiness Report
- Master Index (this file)

---

**Note:** This documentation was generated using BMAD document-project workflow for brownfield development support.

