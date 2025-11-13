# Tenant Scraper - Source Tree Analysis

**Generated:** 2025-11-13

## Directory Structure

```
tenant_scraper/
├── src/
│   └── tenant_scraper/          # Main package directory
│       ├── __init__.py           # Package initialization, exports TenantScraper
│       ├── scraper.py            # Core scraping logic (2900+ lines)
│       └── cli.py                # Command-line interface (275 lines)
│
├── tests/                        # Test suite
│   ├── __init__.py
│   ├── test_scraper.py          # Unit tests for scraper
│   └── test_parser_snapshot.py   # Parser snapshot tests
│
├── scripts/                      # Utility scripts
│   ├── scrape_mecsr_csv.py      # MECSR CSV batch processing
│   ├── enrich_tenants_with_fsq.py # FSQ-OS-Places enrichment
│   ├── capture_network_traffic.py # Network traffic capture
│   ├── capture_comprehensive_maps.py # Maps data capture
│   └── [other utility scripts]
│
├── docs/                         # Documentation
│   ├── FSQ_INTEGRATION.md       # FSQ integration guide
│   ├── sprint-artifacts/        # Sprint documentation
│   └── stories/                 # User stories
│
├── data/                         # Data files
│   ├── mecsr_malls_with_google_urls.csv
│   ├── google_business_categories.json
│   └── [other data files]
│
├── outputs/                      # Generated outputs
│   ├── mecsr/                   # MECSR mall outputs
│   └── [other output directories]
│
├── memory-bank/                  # Project memory/context
│   ├── activeContext.md
│   ├── progress.md
│   ├── systemPatterns.md
│   └── techContext.md
│
├── bmad/                         # BMAD methodology files
│   └── [BMAD configuration and workflows]
│
├── setup.py                      # Package setup configuration
├── requirements.txt              # Python dependencies
└── README.md                     # Project README
```

## Critical Directories

### `src/tenant_scraper/`
**Purpose:** Main package containing core functionality

- **`__init__.py`**: Package initialization, exports `TenantScraper` class
- **`scraper.py`**: Core scraping logic (~2900 lines)
  - `TenantScraper` class - Main scraper implementation
  - `ScraperSettings` dataclass - Configuration
  - `DirectoryTextExtractor` class - Text extraction fallback
  - `MallContextFilter` - Logging filter
- **`cli.py`**: Command-line interface (~275 lines)
  - `main()` - Entry point
  - Argument parsing and validation
  - Output formatting functions

### `tests/`
**Purpose:** Test suite

- **`test_scraper.py`**: Unit tests for scraper components
- **`test_parser_snapshot.py`**: Parser snapshot tests

### `scripts/`
**Purpose:** Utility scripts for various tasks

- Batch processing scripts
- Data enrichment scripts
- Network traffic capture scripts
- Category mapping scripts

### `docs/`
**Purpose:** Project documentation

- Integration guides
- Sprint artifacts
- User stories

## Entry Points

### Primary Entry Point
- **CLI Command:** `tenant-scraper` (defined in `setup.py` entry_points)
  - Points to: `tenant_scraper.cli:main`

### Python API Entry Point
- **Import:** `from tenant_scraper import TenantScraper`
  - Exported from: `src/tenant_scraper/__init__.py`

## Key Files

### Configuration Files
- **`setup.py`**: Package metadata, dependencies, entry points
- **`requirements.txt`**: Python package dependencies
- **`README.md`**: Project documentation and usage guide

### Core Implementation Files
- **`scraper.py`**: Largest file (~2900 lines), contains all scraping logic
- **`cli.py`**: CLI interface and argument handling

## File Patterns

### Python Files
- **Source:** `src/**/*.py`
- **Tests:** `tests/**/*.py`
- **Scripts:** `scripts/**/*.py`

### Configuration Files
- **Package:** `setup.py`, `requirements.txt`
- **BMAD:** `bmad/**/*.yaml`, `bmad/**/*.md`

### Data Files
- **CSV:** `data/**/*.csv`
- **JSON:** `data/**/*.json`, `outputs/**/*.json`

## Module Organization

The project follows a simple, flat package structure:

```
tenant_scraper/
├── __init__.py      # Public API exports
├── scraper.py       # Core functionality
└── cli.py           # CLI interface
```

This structure is appropriate for a CLI tool with focused functionality.

## Integration Points

### External Dependencies
- Playwright (browser automation)
- Pandas (data processing)
- Requests/aiohttp (HTTP clients)

### Data Flow
- Input: URLs or CSV files → CLI
- Processing: CLI → Scraper → Google Maps
- Output: Scraper → CLI → JSON/CSV files

## Development Areas

### Core Logic
- `src/tenant_scraper/scraper.py` - Main development focus

### CLI Interface
- `src/tenant_scraper/cli.py` - User-facing interface

### Utilities
- `scripts/` - Various utility scripts for data processing

