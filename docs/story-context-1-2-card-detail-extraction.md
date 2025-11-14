# Story Context – 1-2 Card Detail Extraction

**Story:** 1-2-card-detail-extraction (Epic 1)
**Source Documents:**
1. `docs/card-behaviour-investigation.md` – DOM selectors, event flow, timing heuristics, protobuf inventory.
2. `docs/architecture.md#pending-component-card-detail-extraction-pipeline` – outlines expected component responsibilities once implemented.
3. `docs/stories/1-1-card-behaviour-discovery.md` – completion notes + asset list from investigation.
4. Assets under `outputs/st-james-quarter/card-investigation/` and `outputs/ocean-terminal-investigation/network-traffic/` – protobuf/HAR captures.

## Implementation Notes
- Use `a.hfpxzc` locator for tenant cards in directory view (`!10e3` URLs) with `scroll_into_view_if_needed()` plus documented waits.
- Load state strategy: rely on `domcontentloaded` with explicit `asyncio.sleep` delays (0.5 s settle after scroll; 2 s after click/back).
- Detail pane selectors:
  - Name: `h1`
  - Category: `button[jsaction*='category']`
  - Rating: `div[jsaction*='rating'] span[role='img']`
  - Phone: `button[data-tooltip='Copy phone number']`
  - Website: `a[data-tooltip='Open website']`
  - Hours: `div[aria-label*='Hours']`
  - Maps Link: use card `href` or normalized place ID
- Protobuf payloads (application/x-protobuf) contain canonical contact data; reuse captured `.bin` files to craft parser (consider `blackboxprotobuf`).
- Throttling guidance: default 2 s between cards, configurable via CLI / settings.

## Risks & Considerations
- Google Maps DOM may mutate; prefer attribute-based selectors (`aria-label`, `data-tooltip`, `jsaction`).
- Large malls may have hundreds of cards; add optional cap + progress logging.
- Ensure fallback path remains (text extraction) when detail pane fails.

## Acceptance Checkpoints
- CLI flag `--details` produces enriched JSON/CSV fields without regressions to baseline.
- Tests leverage stored fixtures to avoid live Google requests in CI.
- Documentation updated (README, architecture) describing the detail extraction workflow.
