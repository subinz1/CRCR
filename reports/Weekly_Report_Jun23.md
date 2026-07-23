# CRCR (Cross-Repository CI Relay) — Weekly Report

**Period:** June 16 – June 25, 2026

## Summary

Focused on CRCR system integration testing, HUD mockup refinement, rate limiting resolution, and upstream contributions. Major wins include identifying and fixing a critical `action.yml` parse error (PR #8209), resolving persistent rate limiting in test workflows via randomized jitter, delivering a pixel-accurate HUD mockup with L3/L4 filtering, and compiling a comprehensive system integration test report for the CRCR Workgroup.

## Key Accomplishments

### CRCR System Integration Testing (TorchedHat/pytorch-redhat-ci)

- Deployed **8 automated test workflows** (30+ test scenarios) covering L1 dispatch, L2 callbacks, HUD ingestion, ClickHouse replication, state transitions, and security controls
- Processed **19,117 workflow dispatches** over 7 days of live production traffic from `pytorch/pytorch`
- Identified and resolved **two distinct failure phases:**
  - **Phase 1 (Rate Limiting):** HTTP 429 errors from CRCR Callback Lambda — resolved by implementing throttle offsets (20–420s) with randomized jitter (`RANDOM % 15-25`) across all 6 callback workflows, keeping peak rate at ~9 callbacks/min per dispatch
  - **Phase 2 (Action Parse Error):** PR [#8173](https://github.com/pytorch/test-infra/pull/8173) introduced `${{ job.status }}` in `action.yml` description field, breaking all L2+ callback workflows for ~13 hours — fixed by PR [#8209](https://github.com/pytorch/test-infra/pull/8209)
- **Current status: 50+ consecutive runs ALL PASSING** after both fixes merged

### Upstream Contributions (pytorch/test-infra)

- Reviewed and merged PR [#8209](https://github.com/pytorch/test-infra/pull/8209) — one-line fix replacing `${{ job.status }}` with plain text `"job.status"` in `action.yml` to prevent GitHub Actions parse error
- Reviewed CRCR PRs [#8170](https://github.com/pytorch/test-infra/pull/8170), [#8183](https://github.com/pytorch/test-infra/pull/8183), [#8198](https://github.com/pytorch/test-infra/pull/8198) for logic, flow, and unused variables — provided structured review comments

### HUD Mockup (RFC-0054)

- Built pixel-accurate [HUD mockup](https://subinz1.github.io/rfcs/RFC-0054-assets/oot-hud-mockup.html) matching the real `hud.pytorch.org` — dark mode default, correct colors, compact rows, SEV banner, HUD/Autorevert toggle
- Implemented **L3/L4 CRCR column filtering** — "Hide non-viable-strict jobs" checkbox (checked by default) hides L3 backends, showing only L4 (blocking) in CRCR expanded columns
- Added full Settings dropdown (floating overlay) with View Options and Filter Options matching the real HUD
- Set dark mode as default on [CRCR Summary page](https://subinz1.github.io/rfcs/RFC-0054-assets/oot-hud-mockup-crcr-summary.html)

### Architecture Diagrams

- Created **in-tree CI architecture diagram** (Excalidraw) showing PR events → GitHub Actions → self-hosted runners → S3 → Data Pipeline → ClickHouse → CI HUD flow
- Maintained consistent styling (sans-serif fonts, cylindrical DB shapes, color palette) across CRCR and in-tree diagrams

### Documentation & Reports

- Compiled **CRCR System Integration Test Report** for the CRCR Workgroup (Meta, Huawei, Linux Foundation) — includes test suite architecture, coverage mapping against the integration plan, daily run statistics, failure root cause analysis (3 phases), rate limiting resolution details, and 7 actionable recommendations
- Created **OOT → CRCR Rename Plan** — identified ~21 files and ~30 unique string patterns across `pytorch/test-infra` that need renaming (file paths, Redis keys, ClickHouse tables, API endpoints, TS/React components, env variables)

### RFC Work

- Updated RFC-0054 assets and mockup pages on `oot-hud-integration-rfc` branch of `subinz1/rfcs`
- Addressed review comments on [RFC PR #96](https://github.com/pytorch/rfcs/pull/96)

## Open Items

- **OOT → CRCR rename** across `pytorch/test-infra` — 21 files, 9 path renames, ~30 string patterns identified; plan documented, execution pending coordination with Huawei PRs
- **PR title quoting bug** in TorchedHat L1 test — backticks in PR titles cause bash command substitution; fix pending
- **Manual testing session** for P0 infra tests (AUTH, DynamoDB, error handling) — requires Meta infrastructure access
- **Rate limit UX improvements** — recommend adding `Retry-After` header to Lambda 429 responses and documenting the 60 req/min/repo limit in the callback action README
- CRCR PRs [#8170](https://github.com/pytorch/test-infra/pull/8170), [#8183](https://github.com/pytorch/test-infra/pull/8183), [#8198](https://github.com/pytorch/test-infra/pull/8198) remain in draft — awaiting Huawei updates

## Pipelines / Test Status

- **TorchedHat/pytorch-redhat-ci:** All green — 50+ consecutive passing runs across all 8 workflows
- **HUD Mockup pages:** Live and updated at `subinz1.github.io/rfcs/RFC-0054-assets/`
- **RFC-0054 branch:** Up to date with latest mockup and diagram changes
