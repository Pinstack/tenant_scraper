# Technical Context

## Technology Stack

### Core Technologies
- **Python 3.9+**: Primary programming language
- **Playwright**: Modern browser automation (replaced Selenium for better reliability)
- **Chromium**: Browser engine for Playwright
- **Chrome MCP**: Network traffic capture and analysis
- **Beautiful Soup**: HTML parsing fallback
- **Pandas**: Data manipulation and CSV output

### Development Tools
- **pytest**: Testing framework
- **black**: Code formatting
- **flake8**: Linting
- **vulture**: Dead code detection
- **uv**: Package management

### Dependencies
```
playwright>=1.40.0
pandas>=2.0.0
requests>=2.31.0
beautifulsoup4>=4.12.0
pytest>=7.4.0
black>=23.0.0
flake8>=6.0.0
vulture>=2.7
# Network analysis tools included in custom modules
```

## Development Setup
1. Create virtual environment: `python -m venv .venv`
2. Activate: `source .venv/bin/activate`
3. Install dependencies: `pip install -r requirements.txt`
4. Install Playwright browsers: `playwright install chromium`
5. Install development tools: `pip install black flake8 vulture pytest`

## Environment Configuration
- Playwright manages browser binaries automatically
- Headless mode configurable via scraper initialization
- Async architecture with proper resource cleanup
- Comprehensive logging with configurable levels
- Output formats: JSON and CSV with extensible design

## Technical Constraints & Challenges

### Browser Automation - INDIVIDUAL TENANT EXTRACTION WORKING ✅
- **Playwright Async API**: Modern async-first design with reliable resource management
- **"View All" Click**: Critical user interaction that unlocks directory view and individual tenants
- **Dynamic Content Loading**: Individual tenant data loads after "View all" click + scrolling
- **Anti-Bot Bypass**: User interaction simulation successfully circumvents detection measures

### Google Maps Directory Structure - FULLY UNDERSTOOD 🎯
- **"View All" Click BREAKTHROUGH**: Transforms category summaries to individual business listings
- **Directory View Detection**: URL `!10e3` parameter indicates successful directory access
- **Text-Based Content**: Individual tenants displayed as structured text, not DOM elements
- **Multi-Line Format**: Business information spans multiple lines (name/rating/category/address)
- **Working Pattern**: URL → Consent → "View all" click → Directory view → Text parsing → Individual tenants
- **Content Loading**: Progressive loading requires interaction simulation + scrolling sequence
- **Parsing Success**: Multi-line regex parsing extracts complete business profiles immediately

### Data Extraction Challenges
- **DOM Structure**: Complex, dynamic DOM that changes based on location and user state
- **Content Loading**: Asynchronous loading of tenant listings requires careful timing
- **Data Parsing**: Extracting structured data from varied HTML element structures

### API-Based Extraction Challenges
- **Protobuf Decoding**: Need to understand Google Maps protobuf schemas and field mappings
- **Authentication**: Determine proper authentication methods for API access
- **Rate Limiting**: Identify and work within Google Maps API rate limits
- **Schema Evolution**: Monitor changes in API data structures over time
- **Request Replication**: Programmatically replicate browser-generated API calls

### Cross-Platform Compatibility
- **Browser Binaries**: Playwright handles Chromium binaries across platforms
- **Async Event Loops**: Python asyncio works consistently across macOS, Linux, Windows
- **File System**: Output file handling works across operating systems

## Architecture Decisions

### Async Design
- **Playwright Requirement**: Playwright's async-first API necessitated full codebase conversion
- **Resource Management**: Async context managers ensure proper browser cleanup
- **Performance**: Non-blocking I/O operations improve scraping efficiency

### Error Handling Strategy
- **Graceful Degradation**: Continue operation when non-critical features fail
- **Comprehensive Logging**: Detailed debugging information for troubleshooting
- **Retry Mechanisms**: Built-in retry logic for transient failures

### Testing Approach - PRODUCTION VALIDATION COMPLETE ✅
- **End-to-End Integration**: Real Google Maps testing extracts 8+ individual businesses
- **Text Extraction Testing**: `DirectoryTextExtractor` validates multi-line parsing accuracy
- **Business Profile Testing**: Complete validation of names, ratings, categories, addresses
- **"View All" Click Testing**: User interaction simulation reliability confirmed
- **Directory Detection Testing**: URL pattern recognition (!10e3 parameter) working
- **Production Data Testing**: Real mall URLs successfully processed with business intelligence output
