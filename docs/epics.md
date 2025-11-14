# Tenant Scraper - Epic Backlog

## Epic 1: Google Maps Card Behaviour Discovery
- **Objective:** Produce an authoritative reference of the Google Maps tenant card DOM, events, and network payloads so detailed extraction can be implemented with confidence.
- **Key Outcomes:**
  - Documented selector map for directory cards and sub-elements
  - Step-by-step event flow (scroll, hover, click, wait) with required delays
  - Captured network traces (HAR + protobuf) annotated with payload structure
  - Recommendations for automation-safe interaction timing and throttling mitigation
- **Status:** in-progress
- **Dependencies:** Access to Chrome DevTools/Playwright instrumentation, updated capture tooling

### Story 1.1: Instrument Directory Cards in Chrome
- **Goal:** Use Chrome DevTools + Playwright to capture DOM structure, event listeners, and network/protobuf payloads triggered when opening tenant cards.
- **Description:**
  1. Launch representative malls (small + large) in Chrome DevTools protocol sessions
  2. Record DOM snapshots, event listeners, and relevant JS entry points
  3. Capture HAR/protobuf traffic for card expansion, annotating payload fields
  4. Catalogue selectors, waits, retries, and failure scenarios; produce engineering memo with screenshots/code snippets
- **Acceptance Criteria:**
  - Document lists all selectors/locators required for stable automation, with screenshots
  - Event flow diagram showing required scroll → click → wait sequence, including required delays or heuristics
  - HAR/protobuf files stored under `outputs/` with accompanying schema notes (field names, indices, meaning)
  - Risk assessment covering throttling, rate limits, or CAPTCHA triggers
  - Recommended implementation approach added to architecture/PRD references
- **Status:** done
- **Notes:** Investigation outputs gate future detail-extraction epics/stories.

### Story 1.2: Build Deterministic Card Detail Extraction Pipeline
- **Goal:** Implement the `--details` scraping path using the selectors, timing, and protobuf insights from Story 1.1 so that tenant contact data can be harvested reliably.
- **Description:**
  1. Update `TenantScraper.scrape_tenants(..., fetch_details=True)` to iterate directory cards using the `a.hfpxzc` selector and documented timing heuristics.
  2. Extract detail-pane fields (name, category, rating, phone, website, hours, maps link) using selectors recorded in the investigation memo.
  3. Parse protobuf payloads where available to enrich data (e.g., canonical phone, website) and fall back to DOM parsing otherwise.
  4. Integrate throttling mitigation (inter-card delay, retries) and configurable limits for large malls.
  5. Produce automated tests or fixtures exercising the new path against captured HTML/protobuf samples.
- **Acceptance Criteria:**
  - `--details` flag surfaces enriched tenant data for at least two sample malls using stored snapshots/captures.
  - Implementation reuses investigation outputs (selectors, waits) without hard-coded magic numbers beyond documented heuristics.
  - Retry/backoff behaviour documented and covered by tests.
  - README / docs updated to describe detail-extraction capability and prerequisites (Playwright, network capture assets).
  - No regression to baseline directory extraction when `--details` is disabled.
- **Status:** backlog
- **Notes:** Requires assets from Story 1.1; may spawn additional stories for protobuf schema tooling.

### Story 1.3: Fix Google Maps Directory View Navigation
- **Goal:** Restore reliable access to tenant cards after the "View all" navigation step so that directory scraping and detail extraction can proceed end-to-end.
- **Description:**
  1. Reproduce the failure documented in `docs/KNOWN_ISSUES.md` where no cards render after clicking "View all".
  2. Investigate DOM/network changes (URL parameters, lazy-loading containers, feature flags) to identify the new directory access pattern.
  3. Update `_scrape_tenants_from_directory()` to guarantee directory population (scroll/JS injection as needed) and confirm selectors like `a.hfpxzc` return results.
  4. Provide diagnostic logging and optional fallback strategies (e.g., manual URL rewriting) for future regressions.
  5. Document findings in `docs/card-behaviour-investigation.md` and update Known Issues once resolved.
- **Acceptance Criteria:**
  - Reproduction steps documented along with root cause analysis.
  - Scraper reliably loads directory view (verified via automated test or capture) and finds tenant cards using the established selector.
  - Known Issues entry updated to reflect resolution and mitigation steps.
  - Regression test or script added (e.g., `quick_directory_check.py`) to CI/dev workflow to detect navigation breakages early.
  - README / troubleshooting section updated with the new navigation strategy.
- **Status:** backlog
- **Notes:** Blocks verification of Story 1.2 and all downstream detail-extraction work.
