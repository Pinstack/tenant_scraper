# Known Issues - Tenant Scraper

**Last Updated:** 2025-11-13

This document tracks known issues, limitations, and blockers in the tenant scraper project.

## ✅ RESOLVED: Directory Navigation Broken (2025-11-13)

**Status:** RESOLVED  
**Discovered:** 2025-11-13 during Story 1.2 testing  
**Resolved:** 2025-11-13 in Story 1.3  
**Impact:** Previously prevented detail extraction from working end-to-end  
**Severity:** High - core functionality affected

### Problem Description

The base scraper could not successfully navigate to the Google Maps directory view where tenant cards are located. When attempting to scrape, the scraper:

1. Successfully handled consent page ✅
2. Successfully clicked "View all" button ✅  
3. **FAILED to load directory with tenant cards** ❌

**Result:** Zero tenant cards found with `a.hfpxzc` selector (or any alternative selectors tested)

### Root Cause (IDENTIFIED)

**Google Maps changed their card structure from `<a>` tags to `<button>` tags.**

- **Previous selector:** `a.hfpxzc` (link elements)
- **New selector:** `button.hfpxzc` (button elements)

Investigation revealed:
- 10 `button.hfpxzc` elements were present in the DOM
- 0 `a.hfpxzc` elements were present
- The cards have `aria-label` attributes containing tenant names
- The `jsaction` attribute handles click interactions

### Resolution (Story 1.3)

**Changes Made:**

1. **Updated DIRECTORY_SELECTORS in `src/tenant_scraper/scraper.py`:**
   - Changed primary selector from `a.hfpxzc` to `button.hfpxzc`
   - Added `tenant_card_legacy: "a.hfpxzc"` as fallback for potential reversions

2. **Added Fallback Logic:**
   - Detail extraction now tries primary selector first
   - Falls back to legacy selector if no cards found
   - Logs which selector is being used

3. **Enhanced Logging:**
   - Added validation step after directory navigation
   - Logs card counts for both selectors
   - Provides actionable error messages with remediation steps
   - Warns if zero cards found with diagnostic information

4. **Created Regression Tests:**
   - New file: `tests/test_directory_navigation.py`
   - Tests directory access for St James Quarter
   - Validates selector structure (primary vs legacy)
   - Checks card attributes (aria-label, etc.)
   - Detects future Google Maps structure changes

### Verification

✅ **Test Results (2025-11-13):**
- St James Quarter: 140 tenants found (up from 0)
- Detail extraction: Successfully extracted phone numbers for 84/140 tenants
- Regression tests: All passing with primary selector (buttons)

### Files Modified

- `src/tenant_scraper/scraper.py` - Updated selectors and added fallback logic
- `tests/test_directory_navigation.py` - New regression test suite
- `investigate_new_structure.py` - Investigation script (can be kept for future debugging)

### Related Documentation

- Resolution story: `docs/stories/1-3-fix-directory-navigation.md`
- Investigation findings: `docs/card-behaviour-investigation.md`
- Story 1.2 completion: `docs/stories/1-2-card-detail-extraction.md`
- Story 1.1 (original investigation): `docs/stories/1-1-card-behaviour-discovery.md`

---

## ⚠️ Other Known Limitations

### Selector Stability

**Status:** ONGOING RISK  
**Impact:** Medium  
**Mitigation:** Use attribute-based selectors, monitor for failures

Google Maps is a dynamic application that receives frequent updates. Selectors may break without warning.

**Current Strategy:**
- Prefer attribute-based selectors (`aria-label`, `data-tooltip`, `jsaction`)
- Avoid relying solely on class names
- Implement graceful fallbacks

### Network Idle Timeouts

**Status:** DOCUMENTED  
**Impact:** Low  
**Mitigation:** Use `domcontentloaded` wait strategy

The `networkidle` wait strategy times out on Google Maps due to continuous background requests.

**Solution:** Investigation (Story 1.1) recommends using `domcontentloaded` + explicit delays.

### Rate Limiting (Potential)

**Status:** NOT OBSERVED  
**Impact:** High (if it occurs)  
**Mitigation:** 2-second delays, retry logic

During investigation with 3+ card clicks, no rate limiting was detected. However, this could change with:
- Higher request volumes
- Different Google Maps accounts/regions
- Google policy changes

**Monitoring:** Watch for HTTP 429, Captcha challenges, or consecutive failures.

---

## 📝 Issue Tracking

### How to Report Issues

1. Add issue to this document with:
   - Status (🔴 Critical, ⚠️ Warning, ℹ️ Info)
   - Discovery date
   - Impact assessment
   - Reproduction steps
   - Workarounds (if any)
   - Recommended fix

2. Reference in relevant story/epic documents

3. Create investigation scripts in project root (e.g., `investigate_*.py`)

### Issue Lifecycle

- **BLOCKING** - Prevents core functionality
- **ONGOING RISK** - Known limitation requiring monitoring
- **DOCUMENTED** - Known issue with workaround
- **RESOLVED** - Fixed and verified

---

## 🔄 Resolution History

### Story 1.3: Directory Navigation Fix (2025-11-13)

**Issue:** Zero tenant cards found with `a.hfpxzc` selector  
**Root Cause:** Google Maps changed card structure from `<a>` to `<button>` elements  
**Solution:** Updated primary selector to `button.hfpxzc` with fallback to legacy `a.hfpxzc`  
**Result:** 140 tenants now found successfully, detail extraction working end-to-end  
**See:** Resolution details in "RESOLVED: Directory Navigation Broken" section above

---

**Note:** This document should be reviewed and updated:
- After each sprint
- When new issues are discovered
- After major Google Maps updates
- When issues are resolved
