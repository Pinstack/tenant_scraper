# Tenant Scraper - Architecture Documentation

**Generated:** 2025-11-13  
**Project Type:** CLI Tool (Python)

## Executive Summary

Tenant Scraper is built as a modular Python CLI tool using Playwright for browser automation. The architecture follows a layered approach with clear separation between CLI interface, core scraping logic, and utility components.

## Technology Stack

### Core Technologies

- **Python 3.9+** - Primary language
- **Playwright** - Browser automation framework
- **asyncio** - Asynchronous execution
- **argparse** - Command-line argument parsing
- **pandas** - Data processing and CSV handling

### Key Dependencies

**Runtime Dependencies:**
- `playwright>=1.40.0` - Browser automation (requires `playwright install chromium`)
- `pandas>=2.0.0` - CSV processing and data manipulation
- `aiohttp>=3.8.0` - Async HTTP client (for future enhancements)
- `beautifulsoup4>=4.12.0` - HTML parsing (for text extraction fallback)
- `blackboxprotobuf>=1.0.1` - Protocol buffer parsing (for network traffic analysis)

**Development Dependencies:**
- `pytest>=7.4.0` - Testing framework
- `black>=23.0.0` - Code formatting
- `flake8>=6.0.0` - Linting
- `vulture>=2.7` - Dead code detection

## Architecture Pattern

**CLI Tool with Async Core**

The application follows a traditional CLI architecture:

```
┌─────────────────────────────────────┐
│         CLI Layer (cli.py)          │
│  - Argument parsing                 │
│  - Input validation                 │
│  - Output formatting                │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Core Scraper (scraper.py)      │
│  - Browser management                │
│  - Page interaction                  │
│  - Data extraction                  │
│  - Error handling                   │
└─────────────────────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Utility Components              │
│  - Text extraction                  │
│  - Data validation                  │
│  - Logging                          │
└─────────────────────────────────────┘
```

## Component Overview

### 1. CLI Module (`cli.py`)

**Purpose:** Command-line interface and entry point

**Key Functions:**
- `main()` - Entry point, argument parsing
- `setup_logging()` - Logging configuration
- `save_to_json()` - JSON output formatting
- `save_to_csv()` - CSV output formatting

**Responsibilities:**
- Parse command-line arguments
- Validate inputs (URLs, CSV files)
- Coordinate scraping operations
- Format and save output files
- Handle batch processing

### 2. Core Scraper (`scraper.py`)

**Purpose:** Main scraping logic and browser automation

**Key Classes:**

#### `TenantScraper`
Main scraper class implementing async context manager pattern.

**Key Methods:**

**Public API:**
- `scrape_tenants(maps_url, extraction_mode="directory", *, fetch_details=False)` - Main public API method
  - Supports two extraction modes: "directory" (default) and "categories"
  - Handles browser setup/cleanup automatically via context manager

**Private Methods (Internal Implementation):**
- `__aenter__()` / `__aexit__()` - Context manager lifecycle
- `_setup_browser()` - Browser initialization
- `_handle_consent_page()` - Google consent handling
- `_scrape_tenants_from_directory()` - Directory view extraction (internal)
- `_scrape_tenants_by_categories()` - Category-based extraction (internal)
- `_extract_tenants_from_dom()` - DOM-based extraction
- `_perform_with_retries()` - Retry logic with backoff

**Key Features:**
- Async/await pattern throughout
- Resource blocking for performance
- Retry logic with exponential backoff
- Context-aware logging

#### `ScraperSettings`
Configuration dataclass for scraper behaviour.

**Settings (Default Values):**
- `block_resources: bool = True` - Enable resource blocking (default: enabled)
- `aggressive_block: bool = False` - Aggressive blocking mode (default: disabled)
- `blocked_resource_types: Iterable[str] = {"image", "media"}` - Resource types to block
- `blocked_hosts: Iterable[str] = {"lh3.googleusercontent.com", ...}` - Image CDN hosts to block
- `aggressive_hosts: Iterable[str] = {"maps.googleapis.com", "maps.gstatic.com"}` - Additional hosts for aggressive mode
- `action_retries: int = 2` - Retry count for failed operations (default: 2)
- `action_retry_backoff: float = 0.5` - Backoff delay in seconds (default: 0.5s, exponential)

#### `DirectoryTextExtractor`
Text-based extraction fallback when DOM extraction fails.

**Methods:**
- `extract_tenants_from_text()` - Parse text content
- `filter_valid_tenants()` - Validation and deduplication

#### `MallContextFilter`
Logging filter to inject mall context into log messages.

### 3. Data Flow

```
User Input (URL/CSV)
    ↓
CLI Validation
    ↓
TenantScraper.scrape_tenants()
    ↓
Browser Setup (Playwright)
    ↓
Navigate to Google Maps URL
    ↓
Handle Consent (if present)
    ↓
Click "View all" → Navigate to Directory
    ↓
Extract Tenants (DOM or Text)
    ↓
Validate & Filter
    ↓
Return Structured Data
    ↓
CLI Output Formatting (JSON/CSV)
    ↓
Save to File(s)
```

## Key Design Patterns

### 1. Async Context Manager
```python
async with TenantScraper() as scraper:
    tenants = await scraper.scrape_tenants(url)
```

### 2. Retry with Backoff
All browser interactions use `_perform_with_retries()` for resilience.

### 3. Resource Blocking
Configurable resource blocking to improve performance while preserving functionality.

### 4. Dual Extraction Strategy
- Primary: DOM-based extraction (more reliable)
- Fallback: Text-based extraction (more resilient)

## Integration Points

### External Services
- **Google Maps** - Source of tenant data
- **FSQ-OS-Places** (optional) - Data enrichment via scripts

### File I/O
- JSON output files
- CSV input/output files
- Log files (via Python logging)

## Error Handling

- **Retry Logic:** Configurable retries with exponential backoff
  - Default: 2 retries with 0.5s initial backoff (exponential: 0.5s, 1.0s)
  - Applied to all browser interactions via `_perform_with_retries()`
- **Timeout Handling:** 30-second default timeouts for page operations
- **Graceful Degradation:** Falls back to text extraction if DOM fails
- **Logging:** Context-aware logging with mall identifiers via `MallContextFilter`
- **Error Recovery:** Batch processing continues on individual failures

## Performance Considerations

- **Resource Blocking:** Blocks images/media to speed up page loads
- **Async Operations:** Non-blocking I/O throughout
- **Selective Blocking:** Can block specific hosts (maps.googleapis.com, etc.)
- **Infinite Scroll:** Handles large directories efficiently

## Testing Strategy

- **Unit Tests:** `tests/test_scraper.py` - Tests for core components
  - Tests `ScraperSettings` configuration
  - Tests resource blocking configuration
  - Tests helper functions and utilities
- **Integration Tests:** End-to-end scraping tests (requires network access)
- **Test Framework:** pytest with async support
- **Test Execution:** `pytest` (run all tests) or `pytest tests/test_scraper.py` (specific file)

## Security Considerations

- **User-Agent Spoofing:** Uses realistic browser user agent
- **Rate Limiting:** Built-in retry delays prevent aggressive requests
- **No Authentication:** Public Google Maps data only

## Architectural Decisions

### Decision 1: Async Context Manager Pattern
**Decision:** Use async context manager for browser lifecycle management  
**Rationale:** Ensures proper resource cleanup, prevents browser leaks, provides clean API  
**Impact:** All scraping operations must use `async with` pattern  
**Status:** ✅ Implemented

### Decision 2: Dual Extraction Strategy
**Decision:** Primary DOM extraction with text-based fallback  
**Rationale:** DOM extraction is more reliable, but text fallback provides resilience against UI changes  
**Impact:** Two extraction paths must be maintained  
**Status:** ✅ Implemented

### Decision 3: Resource Blocking for Performance
**Decision:** Block images/media by default, optionally block map resources  
**Rationale:** Significantly improves page load times while preserving directory functionality  
**Impact:** Must carefully balance blocking to avoid breaking directory view  
**Status:** ✅ Implemented

### Decision 4: Retry Logic with Exponential Backoff
**Decision:** Configurable retries with exponential backoff for all browser interactions  
**Rationale:** Network and UI interactions are inherently flaky, retries improve reliability  
**Impact:** All browser operations wrapped in retry logic  
**Status:** ✅ Implemented

### Decision 5: CLI-First Design with Python API
**Decision:** Primary interface is CLI, with Python API for programmatic access  
**Rationale:** CLI is most common use case, API enables integration and automation  
**Impact:** Both interfaces must be maintained and documented  
**Status:** ✅ Implemented

## Solution Design for Future Enhancements

### Enhancement: Parallel Batch Processing
**Architecture Approach:**
- Use `asyncio.gather()` or `asyncio.Semaphore` for concurrency control
- Limit concurrent browser instances (e.g., max 3-5)
- Implement progress tracking per mall
- Aggregate results after all completions

**Integration Points:**
- Extend `cli.py` batch processing logic
- Add concurrency configuration to `ScraperSettings`
- Maintain isolation between browser contexts

### Enhancement: Enhanced Infinite Scroll
**Architecture Approach:**
- Implement scroll detection (check if new content loaded)
- Add scroll progress tracking
- Implement scroll timeout (stop after N seconds without new content)
- Add resume capability for interrupted scrapes

**Integration Points:**
- Enhance `_extract_tenants_from_dom()` method
- Add scroll state tracking to `TenantScraper` class
- Implement progress callbacks for CLI feedback

### Enhancement: FSQ-OS-Places Integration
**Architecture Approach:**
- Create separate enrichment module (`enrichment.py`)
- Use spatial indexing for location matching
- Implement fuzzy matching for name variations
- Cache enrichment results to avoid duplicate queries

**Integration Points:**
- Add enrichment step after scraping
- Extend tenant data structure with enriched fields
- Add CLI flag for enabling/disabling enrichment

### Enhancement: Web Interface (Vision)
**Architecture Approach:**
- Use FastAPI for REST API backend
- Separate frontend (React/Vue) for UI
- Use existing `TenantScraper` as backend service
- Implement job queue for async processing

**Integration Points:**
- Create API layer wrapping `TenantScraper`
- Add authentication/authorization
- Implement job status tracking
- Add WebSocket support for real-time progress

## Implementation Patterns for AI Agents

### Pattern 1: Browser Interaction
**Consistency Rule:** All browser interactions must use `_perform_with_retries()`  
**Example:**
```python
await self._perform_with_retries(
    "click view all button",
    lambda: self.page.locator('button:has-text("View all")').click()
)
```

### Pattern 2: Data Extraction
**Consistency Rule:** Use public API `scrape_tenants()` for all extraction needs  
**Example:**
```python
# Public API usage (recommended)
async with TenantScraper() as scraper:
    tenants = await scraper.scrape_tenants(url, extraction_mode="directory")
    
# Internal fallback (only if needed)
# The scraper automatically falls back to text extraction if DOM extraction fails
```

### Pattern 3: Error Handling
**Consistency Rule:** Log errors with mall context, continue processing on individual failures  
**Example:**
```python
try:
    tenants = await scraper.scrape_tenants(url)
except Exception as e:
    logger.error(f"[{mall_name}] Failed to scrape: {e}")
    continue  # In batch processing
```

### Pattern 4: Configuration
**Consistency Rule:** Use `ScraperSettings` dataclass for all configuration  
**Example:**
```python
settings = ScraperSettings(
    block_resources=True,
    aggressive_block=False,
    action_retries=3
)
scraper = TenantScraper(settings=settings)
```

## Integration Architecture

### Current Integrations

**Google Maps:**
- **Type:** Web scraping via browser automation
- **Authentication:** None required (public data)
- **Rate Limiting:** Built-in retry delays
- **Error Handling:** Retry with backoff, fallback extraction

**FSQ-OS-Places (Scripts):**
- **Type:** External script integration
- **Authentication:** HuggingFace dataset access
- **Data Format:** PostgreSQL database
- **Integration:** Separate enrichment scripts

### Future Integration Points

**REST API (Vision):**
- **Type:** HTTP API
- **Authentication:** API keys or OAuth
- **Rate Limiting:** Per-user quotas
- **Error Handling:** Standard HTTP status codes

**Web Interface (Vision):**
- **Type:** Web application
- **Frontend:** React/Vue SPA
- **Backend:** FastAPI REST API
- **Real-time:** WebSocket for progress updates

## Development Workflow

See [Development Guide](./development-guide.md) for setup, testing, and contribution guidelines.

## References

- **PRD:** [Product Requirements Document](./PRD.md) - Functional and non-functional requirements
- **Brownfield Documentation:** [Project Index](./index.md) - Comprehensive project documentation
- **Source Tree:** [Source Tree Analysis](./source-tree-analysis.md) - Directory structure

