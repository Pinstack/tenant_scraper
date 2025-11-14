# Website Extraction Quality Requirement

**Status:** 🔴 **NOT MET** (Current: 5%, Required: 90%+)  
**Priority:** **CRITICAL** - Website is the most important extracted field  
**Last Updated:** 2025-11-13

## Requirement

The tenant scraper must achieve **90%+ website extraction rate** for businesses that have websites listed on Google Maps.

This is a critical quality metric - the website field is the most important of all extracted fields.

## Current Status

**Current Extraction Rate:** 5% (8/140 businesses)  
**Required Rate:** 90%+  
**Gap:** 85 percentage points below requirement

### Current Implementation

The website extraction logic includes:
- ✅ Primary selector: `a[data-tooltip='Open website']`
- ✅ Google redirect URL parsing (`/url?q=https://...`)
- ✅ Direct URL handling (`https://...`)
- ✅ Aria-label fallback extraction
- ✅ Detail pane scrolling to load content
- ✅ Multiple fallback selectors
- ✅ Debug logging for troubleshooting

### Known Issues

1. **Low Extraction Rate:** Only 5% of businesses have websites extracted, despite manual verification showing many businesses have websites listed
2. **Manual Verification:** Boots, LEGO Store, and Rituals all have websites listed on Google Maps but are not being extracted
3. **Possible Causes:**
   - Detail pane structure differs when opened from directory view vs direct navigation
   - Website links may load asynchronously after extraction window
   - Some businesses may not have websites in directory-view detail pane
   - Timing issues with detail pane content loading

## Test Results

**Manual Verification (2025-11-13):**
- ✅ Boots: `https://www.boots.com/...` (direct URL, not extracted)
- ✅ LEGO Store: `https://www.lego.com/en-gb/stores/store/edinburgh/...` (direct URL, not extracted)
- ✅ Rituals: `https://www.rituals.com/...` (direct URL, not extracted)

**Automated Test Results:**
- Total tenants: 140
- With websites extracted: 8 (5%)
- With websites available (manual check): Estimated 50-80+ businesses

## Implementation Details

### Extraction Flow

1. Click tenant card from directory view
2. Wait for detail pane to load (h1 element visible)
3. Wait additional 1 second for content to fully render
4. Scroll detail pane to load all sections
5. Wait up to 2 seconds for website link to appear
6. Extract website using primary selector
7. Fallback to alternative selectors if primary fails
8. Parse redirect URLs or extract direct URLs
9. Fallback to aria-label if href unavailable

### Selectors Used

**Primary:**
- `a[data-tooltip='Open website']`

**Fallbacks:**
- `a[aria-label*='Website']`
- `a[aria-label*='website']`
- `a[data-tooltip*='website']`
- `a[href^='http']:not([href*='google']):not([href*='maps'])`

## Next Steps

1. **Investigate Detail Pane Structure**
   - Compare detail pane when opened from directory view vs direct navigation
   - Check if website links are in different DOM locations
   - Verify if scrolling is sufficient to load all content

2. **Improve Timing**
   - Increase wait times for detail pane content
   - Add explicit waits for website link specifically
   - Consider waiting for network requests to complete

3. **Enhanced Selectors**
   - Add more fallback selectors
   - Try XPath selectors for more flexibility
   - Check for website links in different containers

4. **Debugging**
   - Add screenshots when website extraction fails
   - Log full DOM structure when website not found
   - Compare successful vs failed extractions

## Test Coverage

**Quality Tests:**
- `tests/test_website_extraction_quality.py` - Validates 90%+ requirement
- `tests/test_directory_navigation.py` - Regression tests for navigation

**Manual Verification:**
- Scripts in project root for manual testing
- Browser inspection tools for debugging

## Related Documentation

- Story 1.2: `docs/stories/1-2-card-detail-extraction.md`
- Architecture: `docs/architecture.md#card-detail-extraction-pipeline`
- PRD: `docs/PRD.md` - Website extraction requirement
- Investigation: `docs/card-behaviour-investigation.md`

## Acceptance Criteria

For Story 1.2 to be considered complete:
- ✅ Website extraction implemented with comprehensive fallbacks
- ❌ **90%+ extraction rate NOT MET** (Current: 5%)
- ⚠️ Investigation ongoing to identify root cause

---

**Note:** This requirement must be met before Story 1.2 can be considered production-ready. The current 5% extraction rate is insufficient for production use.

