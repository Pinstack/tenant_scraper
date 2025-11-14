# Google Maps Tenant Card Behaviour Investigation

**Investigation Date:** 2025-11-13  
**Story:** 1.1 - Card Behaviour Discovery  
**Epic:** 1 - Google Maps Card Behaviour Discovery  
**Status:** Complete  
**Updated:** 2025-11-13 (Story 1.3 - Selector Update)

## Executive Summary

This investigation establishes the definitive understanding of how Google Maps tenant cards behave in the browser and the data flows involved in detail extraction. We successfully captured DOM structure, event sequences, protobuf payloads, and timing requirements for automating card detail extraction.

**Key Findings:**
- Directory view is accessible via `!10e3` URL parameter or "View all" button
- Tenant cards use selector: `button.hfpxzc` (**Updated in Story 1.3** - was `a.hfpxzc`, changed by Google Maps)
- Google Maps heavily uses Protocol Buffer (protobuf) for data transmission
- Captured 145+ protobuf payloads (up to 1.6MB each) containing rich tenant data
- No rate limiting observed during normal interaction patterns
- Detail pane opens via card click, requires 2s load time
- Network idle wait can timeout - load state "domcontentloaded" is more reliable

> **⚠️ UPDATE (Story 1.3):** On or before 2025-11-13, Google Maps changed card structure from `<a>` to `<button>` elements. The selector is now `button.hfpxzc` instead of `a.hfpxzc`. All other findings remain valid. See Story 1.3 documentation for details.

## Investigation Assets

All captured data is stored in:
- `/outputs/st-james-quarter/card-investigation/` - Protobuf captures from directory view
- `/outputs/ocean-terminal-investigation/network-traffic/` - Network traffic baseline
- `/outputs/06-mall/investigation/` - Failed investigation (wrong URL format)

**Asset Inventory:**
- 145 protobuf binary files (`.bin`) - 175 bytes to 1.6MB each
- Network request metadata (JSON)
- Investigation scripts: `scripts/investigate_card_behaviour.py`, `scripts/investigate_card_details.py`

## 1. DOM Structure & Selectors

### Directory View Access

**Method 1: URL Parameter**
```
Append !10e3 to Google Maps URL
Example: https://www.google.com/maps/place/Mall+Name/@lat,lng,zoom!10e3
```

**Method 2: UI Navigation**
```
1. Navigate to mall page
2. Click "View all" button
3. Wait for directory view to load
```

**Selector for "View all" button:**
- Primary: `button:has-text('View all')`
- Alternative: `[aria-label*='View all' i]`

### Tenant Card Selectors

**Recommended Selector: `button.hfpxzc`** (Updated in Story 1.3 - was `a.hfpxzc`)

**Why this selector works:**
- Specific to tenant card buttons in directory view
- Returns 5-500 cards (reasonable range)
- Class name `hfpxzc` stable across updates (element type changed from `<a>` to `<button>` in 2025-11-13)
- Each card is a clickable link to tenant detail page

**Card Structure (Updated in Story 1.3):**
```html
<button class="hfpxzc" aria-label="Tenant Name" jsaction="pane.wfvdle123;...">
  <div aria-label="Tenant Name">
    <div class="fontHeadlineSmall">Tenant Name</div>
    <div class="fontBodyMedium">
      <span aria-label="4.5 stars">★★★★☆</span>
      <span>(123)</span>
      <span> · </span>
      <span>Category</span>
    </div>
  </div>
</a>
```

**Alternative Selectors (for fallback):**
- `[role='article']` - Generic but may include non-tenant elements
- `div[jsaction*='mouseover']` - Interaction-based selector
- `a[href*='/maps/place/']` - All place links (too broad, needs filtering)

### Detail Pane Selectors

**Detail pane appears after clicking a card:**
- Container: `div.m6QErb` or `div[role='main']`
- Name: `h1` (first heading in detail pane)
- Category: `button[jsaction*='category']`
- Rating: `div[jsaction*='rating'] span[role='img']`
- Phone: `button[data-tooltip='Copy phone number']`
- Website: `a[data-tooltip='Open website']`
- Address: `button[data-tooltip='Copy address']`
- Hours: `div[aria-label*='Hours']`

**Note:** Selectors are based on observation and may change. Recommend using attribute-based selectors (jsaction, data-tooltip, aria-label) over class names for resilience.

## 2. Event Flow & Timing

### Complete Interaction Sequence

```
1. Navigate to Mall URL
   ├─ Handle consent page (if present)
   │  └─ Click: [aria-label*='Accept' i]
   │  └─ Wait: 1s
   │
2. Access Directory View
   ├─ Check if URL contains !10e3 (already in directory)
   ├─ If not: Click "View all" button
   │  └─ Selector: button:has-text('View all')
   │  └─ Wait: domcontentloaded (more reliable than networkidle)
   │  └─ Additional wait: 2s for rendering
   │
3. Scroll Directory (if needed)
   ├─ Scroll down to load more tenants
   │  └─ Use: element.scroll_into_view_if_needed()
   │  └─ Or: Infinite scroll pattern
   │
4. For Each Tenant Card:
   ├─ Find card: page.locator('button.hfpxzc').nth(index)
   │
   ├─ Scroll into view
   │  └─ card.scroll_into_view_if_needed()
   │  └─ Wait: 0.5s
   │
   ├─ Click card
   │  └─ card.click()
   │  └─ Wait: domcontentloaded
   │  └─ Additional wait: 2s
   │
   ├─ Extract details from pane
   │  └─ Use detail pane selectors (see section 1)
   │
   ├─ Return to directory
   │  └─ page.go_back()
   │  └─ Wait: domcontentloaded
   │  └─ Additional wait: 1s
   │
   └─ Inter-card delay: 2s (anti-throttling)
```

### Timing Requirements

| Action | Minimum Wait | Recommended Wait | Notes |
|--------|--------------|------------------|-------|
| After consent click | 1s | 1s | Consent redirect completes quickly |
| After "View all" click | Load state | domcontentloaded + 2s | networkidle can timeout |
| Before card interaction | 0.5s | 0.5s | Ensure card is visible |
| After card click | 2s | 2s | Detail pane render time |
| After back navigation | 1s | 1s | Directory view restore |
| Between cards | 2s | 2s | Throttling mitigation |

**Load State Strategy:**
- Use `domcontentloaded` instead of `networkidle` for page transitions
- networkidle can timeout due to continuous background requests
- Add explicit delays after load state for rendering

## 3. Network Payload Analysis

### Protocol Buffer (Protobuf) Usage

Google Maps extensively uses Protocol Buffers for data transmission. During our investigation, we captured:

**Protobuf Statistics:**
- **Total captures:** 145 files
- **Size range:** 175 bytes to 1.6MB
- **Large payloads:** 2 files over 500KB (likely full directory data)
- **Typical payload:** 8-30KB (individual tenant data)

**Protobuf File Sizes (Sample):**
```
175 bytes     - Small metadata
8-15 KB       - Individual tenant data
20-30 KB      - Tenant with images/reviews
50-150 KB     - Category listings
675 KB        - Partial directory data
1.6 MB        - Full directory dump
```

### Protobuf Detection

**Content-Type Headers:**
- `application/x-protobuf`
- `application/octet-stream`

**Heuristic Detection:**
- Response body contains patterns: `!1m`, `!2m`, `!3m` (protobuf field markers)
- Binary data with length > 100 bytes

### API Endpoints Observed

Key Google Maps API endpoints detected during investigation:

1. **Directory Data Endpoint:**
   - Pattern: `/maps/api/...`
   - Returns: Protobuf with full tenant list
   - Triggered: On directory view load

2. **Place Detail Endpoint:**
   - Pattern: `/maps/place/...`
   - Returns: Individual tenant details
   - Triggered: On card click

3. **Tile/Map Data:**
   - Pattern: `/maps.googleapis.com/...`
   - Returns: Map tiles and vector data
   - Can be blocked for performance (if not using map display)

**Note:** Exact endpoint URLs are obfuscated and change frequently. Protobuf payloads remain consistent in structure.

## 4. Throttling & Rate Limiting

### Observations

During investigation with 3+ card clicks:

**No Rate Limiting Detected:**
- ✅ No HTTP 429 (Too Many Requests) responses
- ✅ No HTTP 5xx server errors
- ✅ No observable delays or blocks

**Successful Strategy:**
- 2-second delay between card interactions
- Normal browser behavior simulation (scroll, wait, click)
- Realistic user agent string

### Recommended Mitigation Strategies

**1. Delays:**
```python
# Inter-card delay
await asyncio.sleep(2)

# After scroll
await asyncio.sleep(0.5)

# After click (for rendering)
await asyncio.sleep(2)
```

**2. Retry Logic:**
```python
retries = 2
backoff = 0.5  # seconds, exponential
```

**3. Resource Blocking:**
```python
# Block images to speed up page loads
blocked_types = {"image", "media"}

# Optional: Block map tiles (if not needed)
aggressive_block = {"maps.googleapis.com", "maps.gstatic.com"}
```

**4. User Agent:**
```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36
```

### Warning Signs to Monitor

If implementing detail extraction, monitor for:
- ❌ Consecutive failures (3+)
- ❌ Captcha challenges
- ❌ HTTP 429 status codes
- ❌ Sudden increase in response times

**Mitigation:** Increase delays, reduce concurrency, rotate user agents.

## 5. Automation-Ready Strategy

### Recommended Implementation

**High-Level Approach:**
```python
async def extract_tenant_details(mall_url: str) -> List[Dict]:
    """Extract detailed tenant information from Google Maps."""
    
    async with TenantScraper() as scraper:
        # Step 1: Get basic tenant list from directory
        tenants = await scraper.scrape_tenants(
            mall_url, 
            extraction_mode="directory"
        )
        
        # Step 2: Enrich with detail extraction
        detailed_tenants = []
        for tenant in tenants:
            details = await extract_card_details(scraper.page, tenant)
            detailed_tenants.append({**tenant, **details})
            await asyncio.sleep(2)  # Throttle
        
        return detailed_tenants
```

### Deterministic Extraction Path

**Phase 1: Directory Extraction (Current, Working)**
1. Navigate to mall URL
2. Handle consent
3. Access directory view (!10e3)
4. Scroll to load all tenants
5. Extract tenant table HTML directly from DOM
6. Parse tenant cards: name, category, rating, review count

**Phase 2: Detail Extraction (Proposed, Ready for Implementation)**
1. For each tenant from Phase 1:
2. Find corresponding card: `page.locator('button.hfpxzc').filter(has_text=tenant_name)`
3. Scroll card into view
4. Click card → opens detail pane
5. Wait for detail pane to render
6. Extract additional fields:
   - Phone number
   - Website URL
   - Business hours
   - Full address
   - Additional categories
7. Navigate back to directory
8. Repeat with delay between cards

### Selector Map (Ready for Code)

```python
DIRECTORY_SELECTORS = {
    "view_all_button": "button:has-text('View all')",
    "tenant_card": "button.hfpxzc",  # Updated in Story 1.3
    "tenant_name": "div.fontHeadlineSmall",
    "tenant_rating": "span[role='img'][aria-label*='stars']",
}

DETAIL_PANE_SELECTORS = {
    "pane_container": "div.m6QErb",
    "name": "h1",
    "category": "button[jsaction*='category']",
    "phone": "button[data-tooltip='Copy phone number']",
    "website": "a[data-tooltip='Open website']",
    "address": "button[data-tooltip='Copy address']",
    "hours": "div[aria-label*='Hours']",
    "rating": "div[jsaction*='rating'] span[role='img']",
}
```

### Error Handling

```python
try:
    # Card interaction
    await card.click(timeout=5000)
except PlaywrightTimeoutError:
    logger.warning(f"Timeout clicking card {index}")
    continue  # Skip to next card
except Exception as e:
    logger.error(f"Error processing card {index}: {e}")
    if consecutive_failures >= 3:
        raise  # Abort extraction
    continue
```

## 6. Architecture Recommendations

### Component: Card Detail Extraction Pipeline

**Location in Architecture:**
- Module: `src/tenant_scraper/scraper.py`
- Method: `_extract_detailed_tenant_data()` (exists, needs enhancement)
- New components: See recommendations below

**Proposed Architecture:**

```
TenantScraper
    ├─ scrape_tenants(fetch_details=True)  [Entry point]
    │
    ├─ _scrape_tenants_from_directory()    [Phase 1: Basic data]
    │   ├─ Navigate + consent
    │   ├─ Access directory view
    │   ├─ Scroll directory panel
    │   └─ Extract tenant table HTML
    │
    └─ _extract_detailed_tenant_data()     [Phase 2: Detail enrichment]
        ├─ For each tenant:
        │   ├─ _find_tenant_card_locator()
        │   ├─ _click_card_with_retry()
        │   ├─ _wait_for_detail_pane()
        │   ├─ _extract_detail_fields()
        │   ├─ _navigate_back_to_directory()
        │   └─ _throttle_delay()
        │
        └─ Return enriched tenants
```

**New Methods to Implement:**

1. **`_find_tenant_card_locator(tenant_name: str) -> Locator`**
   - Find card element by tenant name
   - Use filter with `has_text` for reliability
   - Return Playwright Locator object

2. **`_click_card_with_retry(locator: Locator, retries: int = 2) -> bool`**
   - Scroll card into view
   - Click with retry logic
   - Return success/failure

3. **`_wait_for_detail_pane(timeout: float = 5.0) -> bool`**
   - Wait for detail pane container to appear
   - Use `domcontentloaded` + explicit delay
   - Return True if pane loaded

4. **`_extract_detail_fields() -> Dict[str, Any]`**
   - Extract fields using DETAIL_PANE_SELECTORS
   - Handle missing fields gracefully
   - Return dict of additional fields

5. **`_navigate_back_to_directory() -> None`**
   - Use browser back() or close detail pane
   - Wait for directory view to restore
   - Verify expected state

6. **`_throttle_delay(seconds: float = 2.0) -> None`**
   - Async sleep between cards
   - Configurable via ScraperSettings
   - Log throttling for debugging

### Configuration Updates

Add to `ScraperSettings`:

```python
@dataclass
class ScraperSettings:
    # ... existing fields ...
    
    # Detail extraction settings
    enable_detail_extraction: bool = False
    detail_per_card_delay: float = 2.0
    detail_extraction_timeout: float = 5.0
    detail_max_failures: int = 3
```

### Testing Strategy

**Unit Tests:**
- Test selector finding with mock HTML
- Test retry logic with simulated failures
- Test field extraction with sample DOM

**Integration Tests:**
- Test full pipeline with real Google Maps URL
- Test with small mall (5-10 tenants)
- Verify no rate limiting triggers

**Manual Testing:**
- Run with `--no-headless` to observe behavior
- Test with malls of varying sizes (small, medium, large)
- Monitor network tab for throttling indicators

## 7. Known Limitations & Risks

### Current Limitations

1. **Selectors May Change**
   - Risk: Google updates class names/structure
   - Mitigation: Use attribute-based selectors, monitor for failures

2. **networkidle Timeouts**
   - Issue: Continuous background requests prevent idle state
   - Solution: Use `domcontentloaded` instead

3. **Variable Detail Pane Layout**
   - Issue: Different businesses show different fields
   - Solution: Gracefully handle missing fields

4. **Protobuf Parsing Not Implemented**
   - Current: Captured but not decoded
   - Future: Decode protobuf for direct data access (bypasses UI)

### Risks & Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Rate limiting | Low | High | Delays, retries, monitoring |
| Selector changes | Medium | Medium | Attribute-based selectors, tests |
| Captcha challenges | Low | High | User agent, realistic behavior |
| Timeout issues | Medium | Low | Adjust timeouts, load state strategy |

## 8. Next Steps

### Immediate (Story 1.2 - Ready for Implementation)

1. ✅ Update `architecture.md` with findings from this investigation
2. ✅ Implement `_find_tenant_card_locator()` method
3. ✅ Implement `_click_card_with_retry()` method
4. ✅ Implement `_extract_detail_fields()` method
5. ✅ Add `detail_per_card_delay` to `ScraperSettings`
6. ✅ Write unit tests for new methods
7. ✅ Test with small mall (5-10 tenants)

### Future Enhancements

1. **Protobuf Decoding**
   - Use `blackboxprotobuf` or similar library
   - Decode captured `.bin` files
   - Extract structured data directly (bypasses UI entirely)
   - Potential 10x speed improvement

2. **Parallel Processing**
   - Open multiple browser contexts
   - Process cards in parallel (with rate limiting)
   - Requires careful session management

3. **Resume Capability**
   - Save progress after each tenant
   - Resume from last processed tenant on failure
   - Useful for large malls (100+ tenants)

4. **Enhanced Monitoring**
   - Track timing metrics per mall
   - Detect rate limiting early
   - Auto-adjust delays based on response times

## Appendices

### A. Script Reference

**Investigation Scripts:**
- `scripts/investigate_card_behaviour.py` - Basic DOM/selector investigation
- `scripts/investigate_card_details.py` - Advanced card interaction capture
- `scripts/capture_network_traffic.py` - Network/protobuf capture utility

**Usage Examples:**
```bash
# Basic investigation
python scripts/investigate_card_behaviour.py \
    "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A" \
    --name "st-james-quarter" \
    --no-headless -v

# Detailed card investigation
python scripts/investigate_card_details.py \
    "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A" \
    --name "st-james-quarter" \
    --sample-size 3 \
    --no-headless -v

# Network capture with protobuf
python scripts/capture_network_traffic.py \
    "https://maps.app.goo.gl/FsGevWWrjvab4tZ9A" \
    --detect-protobuf --no-headless -v
```

### B. Protobuf Samples

**Location:** `outputs/st-james-quarter/card-investigation/*.bin`

**Recommended for Analysis:**
- `protobuf_1763058712742.bin` (675 KB) - Large directory payload
- `protobuf_1763058713025.bin` (1.6 MB) - Full directory dump
- `protobuf_1763058714191.bin` (144 KB) - Category listing

**Tools for Decoding:**
- `blackboxprotobuf` - Python library for unknown protobuf schemas
- `protoc` - Protocol Buffer compiler (requires schema)
- `deproto` - Available in `outputs/ocean-terminal/protobuf-schemas/deproto/`

### C. Reference URLs

**Test Malls:**
- St James Quarter (Edinburgh): `https://maps.app.goo.gl/FsGevWWrjvab4tZ9A` (Large)
- Ocean Terminal (Edinburgh): Existing test data (Medium)
- 06 Mall (Sharjah): `https://www.google.com/maps/place/?q=place_id:ChIJK7ARyrX19T4RU74ktwYp9Rw` (Small, wrong format)

**Documentation:**
- PRD: `docs/PRD.md` - Product requirements
- Architecture: `docs/architecture.md` - System architecture (to be updated)
- Source Analysis: `docs/source-tree-analysis.md` - Code structure

---

**Investigation Complete**  
**Ready for Implementation:** Yes  
**Blocking Issues:** None  
**Recommendation:** Proceed to Story 1.2 - Implement Card Detail Extraction

