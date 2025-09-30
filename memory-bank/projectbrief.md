# Tenant Scraper Project Brief

## Core Purpose
Build a robust web scraper to extract individual brand/tenant names from shopping mall listings on Google Maps, going beyond category summaries to provide specific business names within each category.

## Key Requirements
- Accept Google Maps URLs as input (both short goo.gl links and full map URLs)
- Handle consent pages and redirects automatically
- Access directory view via user interaction simulation
- Infinite scroll directory view to reveal all tenant categories
- **Extract individual tenant/brand names** (McDonald's, Starbucks, H&M, etc.) within categories
- Analyze network traffic to identify Google Maps API endpoints for tenant data
- Extract comprehensive brand information (name, category, rating, location, status)
- Extract detailed contact information (phone, individual map links)
- Output structured data for downstream processing

## Technical Scope
- Web scraping automation using browser automation tools
- Network traffic analysis and API endpoint identification
- Protocol buffer (protobuf) data decoding and analysis
- URL manipulation and parsing
- Data extraction and structuring
- Error handling and validation
- Cross-region compatibility for different mall layouts

## Success Criteria
- Successfully extracts individual tenant names (not just categories) from mall directory
- Identifies and documents Google Maps API endpoints for tenant data extraction
- Handles Google Maps consent flows automatically
- Analyzes network traffic to understand data encoding patterns
- Produces clean, structured output (JSON/CSV)
- Robust error handling with clear failure reporting
- Maintains data integrity across different mall formats

## Constraints
- Must respect website terms of service
- Handle dynamic content loading
- Account for regional differences in UI/layout
- Implement proper rate limiting and delays
