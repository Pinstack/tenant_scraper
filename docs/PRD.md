# Tenant Scraper - Product Requirements Document

**Author:** Raed  
**Date:** 2025-11-13  
**Document Version:** 1.0  
**Project Version:** 0.2.0

---

## Executive Summary

Tenant Scraper is a Python command-line tool that automatically extracts comprehensive tenant/brand information from shopping mall listings on Google Maps. The tool solves the problem of manually collecting tenant data from mall directories by automating the extraction process through intelligent browser automation.

### What Makes This Special

The "magic moment" occurs when users can extract complete tenant directories from Google Maps with a single command, transforming hours of manual data collection into seconds of automated processing. The tool successfully bypasses Google Maps' anti-automation measures through intelligent user interaction simulation, making it reliable and robust for production use.

**Key Differentiators:**
- **Intelligent Automation:** Successfully handles Google Maps consent pages and anti-bot measures
- **Comprehensive Data Extraction:** Captures name, category, rating, location, phone, and more
- **Batch Processing:** Processes multiple malls from CSV input
- **Data Enrichment:** Integration with FSQ-OS-Places for enhanced data quality
- **Developer-Friendly:** Both CLI and Python API interfaces

---

## Project Classification

**Technical Type:** CLI Tool (Python)  
**Domain:** Data Extraction / Web Scraping  
**Complexity:** Medium

**Project Type:** Command-line tool for automated data extraction from Google Maps mall listings. Built with Python 3.9+, Playwright for browser automation, and designed for both single-use and batch processing scenarios.

**Architecture Pattern:** CLI Tool with Async Core - Layered architecture separating CLI interface, core scraping logic, and utility components.

---

## Success Criteria

### Primary Success Metrics

**User Value:**
- **Time Savings:** Reduce manual data collection from hours to seconds per mall
- **Data Completeness:** Extract 90%+ of available tenant data from mall directories
- **Website Extraction:** Achieve 90%+ website extraction rate for businesses with websites listed on Google Maps (critical quality requirement)
- **Reliability:** Successfully process 95%+ of valid Google Maps mall URLs
- **Accuracy:** Maintain 98%+ data accuracy (correct tenant names, categories, locations)

**Technical Excellence:**
- **Performance:** Process single mall in under 2 minutes (excluding network latency)
- **Robustness:** Handle Google Maps UI changes gracefully with fallback extraction methods
- **Maintainability:** Clear code structure enabling easy updates for Google Maps changes

**Developer Experience:**
- **Ease of Use:** Single command execution for common use cases
- **Flexibility:** Both CLI and programmatic API access
- **Documentation:** Comprehensive docs enabling new contributors

### Business Metrics (if applicable)

- **Adoption:** Number of malls processed successfully
- **Data Quality:** Percentage of enriched records via FSQ-OS-Places integration
- **Community:** Contributions and feature requests indicating active use

---

## Product Scope

### MVP - Minimum Viable Product (Current State)

**Core Functionality (✅ Implemented):**

1. **Google Maps Integration**
   - Handle consent pages automatically
   - Navigate to directory view via "View all" button
   - Extract tenant data from directory listings

2. **Data Extraction**
   - Tenant name and category
   - Rating and review count
   - Floor/unit location
   - Phone number (when available)
   - Individual map links
   - Business status (open/closed)

3. **Output Formats**
   - JSON output (structured data)
   - CSV output (spreadsheet-friendly)
   - Batch processing support

4. **CLI Interface**
   - Single URL processing
   - Multiple URL processing
   - CSV batch mode
   - Verbose logging option
   - Headless/visible browser modes

5. **Python API**
   - Async context manager interface
   - Programmatic access to scraping functionality

### Growth Features (Post-MVP)

> **Dependency Note (Epic 1 – Google Maps Card Behaviour Discovery):** Detailed tenant extraction stories are blocked until the discovery memo documents card selectors, event flow, and network payload structure. All growth features referencing card clicks or per-tenant data must reference the outputs of this investigation once available.

**Enhanced Extraction:**

1. **Improved Infinite Scroll**
   - Complete implementation for large malls (100+ tenants)
   - Progress indicators during long extractions
   - Resume capability for interrupted scrapes

2. **Additional Data Fields**
   - Business hours
   - Website URLs (**90%+ extraction rate required** - most important field)
   - Social media links
   - Price range indicators
   - Photos/imagery URLs

3. **Data Enrichment**
   - FSQ-OS-Places integration (partially implemented)
   - Automatic category standardization
   - Brand identification and chain detection
   - Data freshness validation

4. **Performance Optimizations**
   - Parallel processing for batch operations
   - Caching of consent page handling
   - Smart resource blocking strategies

5. **Error Handling & Recovery**
   - Automatic retry with exponential backoff (implemented)
   - Graceful degradation to text extraction (implemented)
   - Detailed error reporting and logging

### Vision (Future)

**Advanced Capabilities:**

1. **Multi-Source Integration**
   - Support for other mapping services (Apple Maps, Bing Maps)
   - Aggregation across multiple sources
   - Conflict resolution and data merging

2. **Real-Time Monitoring**
   - Track tenant changes over time
   - Alert on new tenants or closures
   - Historical data tracking

3. **Web Interface**
   - Browser-based UI for non-technical users
   - Visual progress indicators
   - Interactive data exploration

4. **API Service**
   - RESTful API for programmatic access
   - Rate limiting and authentication
   - Webhook support for async processing

5. **Data Analytics**
   - Tenant category analysis
   - Mall comparison tools
   - Market trend identification

---

## CLI Tool Specific Requirements

### Command-Line Interface

**Input Methods:**
- Single URL: `tenant-scraper "https://maps.app.goo.gl/..."`
- Multiple URLs: Space-separated list
- CSV batch: `--csv data/malls.csv`

**Output Configuration:**
- File output: `-o output.json` or `--output directory/`
- Format selection: `--format json|csv` (auto-detected from extension)
- Aggregate files: `--aggregate-file` for batch operations

**Execution Modes:**
- Headless mode (default): `--headless`
- Visible browser: `--no-headless`
- Verbose logging: `-v` or `--verbose`

**Performance Options:**
- Resource blocking: `--no-block-resources` (disable)
- Aggressive blocking: `--aggressive-block` (enable)

**Extraction Modes:**
- `--mode directory` (default): Extract individual tenants from main directory view
- `--mode categories`: Extract tenants by processing each business category separately

**Additional Options:**
- `--details`: Enable per-tenant card detail extraction (currently experimental, may increase runtime)
- `--no-block-resources`: Disable resource blocking (loads all images/media, slower)
- `--aggressive-block`: Block additional map-related hosts for faster scraping (use with caution)

### Python API Interface

**Core Interface:**
```python
import asyncio
from tenant_scraper import TenantScraper

async def main():
    async with TenantScraper(headless=True) as scraper:
        # Directory mode (default) - extracts all tenants from main directory
        tenants = await scraper.scrape_tenants(url, extraction_mode="directory")
        
        # Categories mode - extracts tenants by processing each category
        tenants = await scraper.scrape_tenants(url, extraction_mode="categories")
        
        # With detailed extraction (per-tenant card clicks)
        tenants = await scraper.scrape_tenants(
            url, 
            extraction_mode="directory",
            fetch_details=True
        )

asyncio.run(main())
```

**Method Signature:**
```python
async def scrape_tenants(
    maps_url: str,
    extraction_mode: str = "directory",  # "directory" or "categories"
    *,
    fetch_details: bool = False
) -> List[Dict[str, Any]]
```

**Configuration:**
- Browser settings via `ScraperSettings` dataclass
- Resource blocking configuration (default: enabled)
- Retry configuration (default: 2 retries, 0.5s backoff)
- Timeout settings (default: 30 seconds)

### Data Structures

**Tenant Object:**
```python
{
    "name": str,           # Business name (required)
    "category": str,       # Business category (required)
    "rating": float,      # Average rating (optional)
    "review_count": int,   # Number of reviews (optional)
    "floor_unit": str,     # Location within mall (optional)
    "status": str,         # "open" | "closed" | "unknown" (optional)
    "phone": str,          # Phone number (optional, if available)
    "maps_link": str,      # Google Maps URL (optional)
    # Fields added in batch CSV mode:
    "mall_name": str,      # Mall name (only in CSV batch mode)
    "source_url": str      # Source Google Maps URL (only in CSV batch mode)
}
```

**Note:** Fields marked as optional may be `None` or missing depending on available data. The `mall_name` and `source_url` fields are only added when processing multiple malls via CSV batch mode.

---

## Functional Requirements

### FR1: Google Maps Integration

**FR1.1: Consent Page Handling**
- **Requirement:** Automatically detect and handle Google Maps consent pages
- **Acceptance Criteria:**
  - Detect consent page presence
  - Click appropriate consent button
  - Handle regional variations (EU, US, etc.)
  - Retry on failure with exponential backoff

**FR1.2: Directory Navigation**
- **Requirement:** Navigate from mall overview to directory view
- **Acceptance Criteria:**
  - Click "View all" button to access directory
  - Handle URL parameter changes (`!10e3` addition)
  - Verify directory view loaded successfully
  - Handle cases where directory view unavailable

**FR1.3: Anti-Automation Bypass**
- **Requirement:** Successfully bypass Google Maps anti-bot measures
- **Acceptance Criteria:**
  - Simulate realistic user interactions
  - Use appropriate user agent strings
  - Handle rate limiting gracefully
  - Maintain session continuity

### FR2: Data Extraction

**FR2.1: DOM-Based Extraction**
- **Requirement:** Extract tenant data from DOM elements
- **Acceptance Criteria:**
  - Identify tenant card elements reliably
  - Extract all available data fields
  - Handle missing fields gracefully
  - Validate extracted data format

**FR2.2: Text-Based Fallback**
- **Requirement:** Fallback extraction when DOM fails
- **Acceptance Criteria:**
  - Parse page text content
  - Identify tenant patterns in text
  - Extract available information
  - Filter invalid entries

**FR2.3: Data Validation**
- **Requirement:** Validate and clean extracted data
- **Acceptance Criteria:**
  - Remove duplicates
  - Filter invalid entries (UI text, etc.)
  - Standardize data formats
  - Handle special characters

### FR3: Output Generation

**FR3.1: JSON Output**
- **Requirement:** Generate structured JSON output
- **Acceptance Criteria:**
  - Valid JSON format
  - Proper encoding (UTF-8)
  - Pretty-printed for readability
  - Consistent structure across tenants

**FR3.2: CSV Output**
- **Requirement:** Generate CSV output for spreadsheet tools
- **Acceptance Criteria:**
  - Proper CSV formatting
  - Header row included
  - Handle special characters in CSV
  - Compatible with Excel/Google Sheets

**FR3.3: Batch Processing**
- **Requirement:** Process multiple malls from CSV input
- **Acceptance Criteria:**
  - Read CSV with mall URLs
  - Process each mall independently
  - Generate individual output files
  - Optionally create aggregate file
  - Handle failures gracefully (continue processing)

### FR4: Error Handling

**FR4.1: Retry Logic**
- **Requirement:** Retry failed operations with backoff
- **Acceptance Criteria:**
  - Configurable retry count
  - Exponential backoff delays
  - Log retry attempts
  - Fail gracefully after max retries

**FR4.2: Error Reporting**
- **Requirement:** Provide clear error messages
- **Acceptance Criteria:**
  - Descriptive error messages
  - Context-aware logging
  - Mall identifier in logs
  - Actionable error guidance

### FR5: Performance Optimization

**FR5.1: Resource Blocking**
- **Requirement:** Block unnecessary resources for speed
- **Acceptance Criteria:**
  - Block images and media by default
  - Optionally block map resources
  - Preserve directory functionality
  - Configurable blocking levels

**FR5.2: Infinite Scroll Handling**
- **Requirement:** Handle large directories efficiently
- **Acceptance Criteria:**
  - Scroll to load all tenants
  - Detect when no more tenants available
  - Progress indication (future)
  - Memory-efficient processing

---

## Non-Functional Requirements

### Performance

**NFR1: Execution Speed**
- **Requirement:** Process single mall in reasonable time
- **Criteria:** 
  - Small malls (<50 tenants): < 1 minute
  - Medium malls (50-200 tenants): < 2 minutes
  - Large malls (200+ tenants): < 5 minutes
  - Excludes network latency

**NFR2: Resource Usage**
- **Requirement:** Efficient browser resource usage
- **Criteria:**
  - Block unnecessary resources
  - Minimize memory footprint
  - Clean browser context after use

### Reliability

**NFR3: Success Rate**
- **Requirement:** High success rate for valid inputs
- **Criteria:**
  - 95%+ success rate for valid Google Maps URLs
  - Graceful handling of edge cases
  - Fallback mechanisms for failures

**NFR4: Error Recovery**
- **Requirement:** Recover from transient failures
- **Criteria:**
  - Automatic retry on network errors
  - Fallback extraction methods
  - Continue batch processing on individual failures

### Usability

**NFR5: Developer Experience**
- **Requirement:** Easy to use and integrate
- **Criteria:**
  - Simple CLI interface
  - Clear error messages
  - Comprehensive documentation
  - Python API for programmatic use

**NFR6: Maintainability**
- **Requirement:** Code should be maintainable
- **Criteria:**
  - Clear code structure
  - Comprehensive tests
  - Good documentation
  - Modular design

### Security

**NFR7: Data Privacy**
- **Requirement:** Respect data privacy
- **Criteria:**
  - Only access public Google Maps data
  - No authentication required
  - No user data collection
  - Respect rate limits

**NFR8: Safe Execution**
- **Requirement:** Safe to run in various environments
- **Criteria:**
  - No system modifications
  - Isolated browser context
  - Clean resource cleanup
  - No external dependencies beyond Python packages

---

## Implementation Planning

### Epic Breakdown Required

Requirements must be decomposed into epics and bite-sized stories for implementation.

**Next Step:** Run `create-epics-and-stories` workflow to create the implementation breakdown.

### Current Implementation Status

**Completed:**
- ✅ Core scraping functionality
- ✅ Consent page handling
- ✅ Directory navigation
- ✅ DOM and text extraction
- ✅ CLI interface
- ✅ Python API
- ✅ Batch processing
- ✅ JSON/CSV output
- ✅ Error handling and retries
- ✅ Resource blocking

**In Progress:**
- 🔄 FSQ-OS-Places integration (scripts available, needs integration)

**Planned:**
- ⏳ Enhanced infinite scroll for large malls
- ⏳ Additional data fields extraction
- ⏳ Parallel batch processing
- ⏳ Web interface (vision)

---

## References

- **Brownfield Documentation:** `docs/index.md` - Comprehensive project documentation
- **Architecture Documentation:** `docs/architecture.md` - System architecture details
- **Development Guide:** `docs/development-guide.md` - Setup and development workflow
- **FSQ Integration Guide:** `docs/FSQ_INTEGRATION.md` - Foursquare OS Places integration

---

## Next Steps

1. **Epic & Story Breakdown** - Run: `create-epics-and-stories` workflow
2. **Architecture Enhancement** - Run: `create-architecture` workflow (if extending functionality)
3. **Solutioning Gate Check** - Run: `solutioning-gate-check` workflow

---

_This PRD captures the essence of Tenant Scraper - transforming manual data collection into automated extraction with intelligent browser automation._

_Created through comprehensive analysis of existing brownfield codebase and documentation._
