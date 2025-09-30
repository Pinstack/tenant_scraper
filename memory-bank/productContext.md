# Product Context

## Problem Solved
Shopping mall directories on Google Maps contain valuable tenant information that is not easily accessible in bulk. While category summaries (e.g., "Food & Drink: 40 businesses") are available, individual tenant names (e.g., "McDonald's", "Starbucks") require deeper analysis of Google Maps' internal APIs and network traffic patterns.

## User Experience Goals
- Simple input: Just provide a Google Maps URL
- Automated execution: No manual intervention required
- Comprehensive output: Individual tenant names (not just categories) extracted
- API insights: Detailed analysis of Google Maps data structures
- Error transparency: Clear reporting when issues occur
- Flexible output: Support multiple formats (JSON, CSV)

## How It Should Work
1. User provides Google Maps URL (short or full)
2. Scraper handles any consent redirects automatically
3. User interaction simulation accesses directory view
4. Directory view is infinitely scrolled to reveal all tenant categories
5. Network traffic is captured and analyzed when interacting with tenants
6. Google Maps API endpoints and data structures are identified
7. Individual tenant data is extracted via identified APIs
8. Structured data is output for further processing

## Value Proposition
- Saves hours of manual data collection
- Provides individual tenant names (not just category summaries)
- Reveals Google Maps API patterns for automated data extraction
- Enables precise analysis of mall composition and trends
- Supports detailed market research and competitive analysis
- Automates what was previously a tedious manual process
