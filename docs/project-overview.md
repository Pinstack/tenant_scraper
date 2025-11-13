# Tenant Scraper - Project Overview

**Generated:** 2025-11-13  
**Project Type:** CLI Tool (Python)  
**Architecture:** Monolith

## Executive Summary

Tenant Scraper is a Python command-line tool that automatically extracts tenant/brand information from shopping mall listings on Google Maps. The tool uses Playwright to simulate user interactions, bypassing Google Maps' anti-automation measures, and extracts comprehensive tenant data including names, categories, ratings, locations, and contact information.

## Technology Stack

| Category | Technology | Version | Justification |
|----------|-----------|---------|---------------|
| Language | Python | 3.9+ | Primary development language |
| Web Automation | Playwright | >=1.40.0 | Browser automation for Google Maps interaction |
| Data Processing | Pandas | >=2.0.0 | CSV processing and data manipulation |
| HTTP Client | Requests | >=2.31.0 | HTTP requests for API calls |
| HTML Parsing | BeautifulSoup4 | >=4.12.0 | HTML parsing and extraction |
| Testing | Pytest | >=7.4.0 | Unit and integration testing |
| Code Quality | Black, Flake8, Vulture | Various | Code formatting, linting, dead code detection |
| Async HTTP | aiohttp | >=3.8.0 | Asynchronous HTTP client |
| Protobuf | blackboxprotobuf | >=1.0.1 | Protocol buffer parsing |

## Architecture Pattern

**CLI Tool Architecture** - Single-entry point command-line application with modular components:

- **Entry Point:** `tenant_scraper.cli:main` (via setuptools console_scripts)
- **Core Module:** `tenant_scraper.scraper` - Contains main scraping logic
- **CLI Module:** `tenant_scraper.cli` - Command-line interface and argument parsing

## Repository Structure

**Type:** Monolith - Single cohesive codebase

```
tenant_scraper/
├── src/tenant_scraper/     # Main package
│   ├── __init__.py        # Package initialization, exports TenantScraper
│   ├── scraper.py         # Core scraping logic (2900+ lines)
│   └── cli.py             # Command-line interface
├── tests/                  # Test suite
├── scripts/                # Utility scripts
├── docs/                   # Documentation
├── data/                   # Data files and samples
├── outputs/                # Generated output files
├── setup.py                # Package configuration
└── requirements.txt        # Python dependencies
```

## Key Features

- ✅ Google Maps consent page handling (automatic detection and interaction)
- ✅ Directory view access via "View all" button click
- ✅ Dual extraction modes: directory view and category-based extraction
- ✅ Infinite scroll support for large mall directories
- ✅ Comprehensive tenant data extraction (name, category, rating, location, phone, maps_link)
- ✅ Multiple output formats (JSON, CSV) with auto-detection
- ✅ Batch processing from CSV input with individual and aggregate outputs
- ✅ FSQ-OS-Places integration for data enrichment (via separate scripts)
- ✅ Resource blocking for performance optimization (configurable)
- ✅ Retry logic with exponential backoff for reliability

## Entry Points

- **CLI Command:** `tenant-scraper` (installed via setuptools)
- **Python API:** `from tenant_scraper import TenantScraper`

## Getting Started

See [Development Guide](./development-guide.md) for setup and usage instructions.

## Related Documentation

- [Architecture Documentation](./architecture.md) - Detailed system architecture
- [Source Tree Analysis](./source-tree-analysis.md) - Directory structure breakdown
- [Development Guide](./development-guide.md) - Setup and development workflow

