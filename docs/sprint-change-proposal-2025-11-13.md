# Sprint Change Proposal – Google Maps Card Investigation

**Date:** 2025-11-13  
**Prepared by:** Scrum Master (Raed)  
**Change Trigger:** Need to reverse-engineer Google Maps tenant cards before implementing detail extraction and backlog items.

## 1. Issue Summary
- During CLI/API refactors we discovered the "click each tenant card" detail path is only partially implemented and lacks a verified understanding of the Google Maps DOM/network behaviour.
- Existing documentation (PRD, architecture) assumes card-level extraction but does not specify the events, selectors, or protobuf payloads required, making further development speculative.
- Without validated knowledge, generating epics/stories would be guesswork and risks rework when Google changes its UI.

## 2. Impact Analysis
### Epic Impact
- Planned epics/stories cannot be authored because their acceptance criteria depend on unknown card-behaviour details.
- A new discovery epic is required before any implementation-focused epics.

### Story Impact
- Any story referencing `--details` mode or detailed tenant extraction must wait for investigation results.
- Backlog currently empty; this proposal seeds the first epic/story to unblock planning.

### Artifact Conflicts
- **PRD:** Section “Growth Features / Additional Data Fields” references card clicks but lacks actionable steps – needs clarification once findings exist.
- **Architecture:** `docs/architecture.md` references deterministic scrolling but not card instrumentation; add findings later.
- **UI/UX specs:** none yet; create only if investigation uncovers UI constraints.

### Technical Impact
- Requires controlled Chrome/Playwright sessions with DevTools, HAR/protobuf capture, and documentation of DOM locators, JS hooks, and rate-limiting behaviour.
- May require new tooling scripts (eg. enhanced `capture_network_traffic.py`).

## 3. Recommended Approach
**Chosen Path:** Option 1 – Direct Adjustment via discovery epic + investigation stories.
- Effort: Medium (dedicated DEV/analyst time).  
- Risk: Low once investigation complete; continuing without data would be High risk.
- Rationale: No completed work to roll back; PRD scope still valid but needs concrete technical guidance.

## 4. Detailed Change Proposals
### Epics & Stories
1. **Epic 1: Google Maps Card Behaviour Discovery**  
   - **Goal:** Produce authoritative reference on card DOM, events, and network payloads.  
   - **Acceptance Criteria:** Document selector map, click/hover sequences, async timing, protobuf/JSON payload formats, throttling/rate-limit observations, and recommended automation strategy.
2. **Story 1.1: Instrument Directory Cards in Chrome**  
   - Tasks:  
     - Use Chrome DevTools protocol (Playwright/Chrome) to capture DOM snapshots and event listeners.  
     - Record request/response traffic (HAR + protobuf) when opening cards.  
     - Catalogue selectors, required waits, failure states.  
     - Produce engineering memo with screenshots + code snippets.

### PRD Update (post-investigation placeholder)
- Add subsection under “Growth Features → Additional Data Fields” describing the investigation deliverable and how its outputs will convert into implementation stories.

### Architecture Update (future)
- Reserve section in `docs/architecture.md` “Card Detail Extraction Pipeline” to be populated with findings.

## 5. Implementation Handoff
- **Scope Classification:** Moderate (requires backlog creation and coordination before development).  
- **Recipients:** Product Owner / Scrum Master to seed epics; DEV/Analyst to execute discovery story.  
- **Success Criteria:** Signed-off discovery memo, updated PRD/architecture sections, and unblock story generation workflows (`*create-story`, `*sprint-planning`).

## Next Steps
1. Approve this proposal.  
2. Author Epic 1 + Story 1.1 using PM/SM workflows with investigation as the objective.  
3. Assign DEV/analyst to perform Chrome/Playwright study and capture outputs into docs + tooling scripts.  
4. Once discovery deliverables are in docs, rerun `*sprint-planning` and `*create-story` for implementation epics.
