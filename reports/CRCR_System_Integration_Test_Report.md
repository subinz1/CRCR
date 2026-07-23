# CRCR System Integration Test Report

**Repository:** [TorchedHat/pytorch-redhat-ci](https://github.com/TorchedHat/pytorch-redhat-ci)
**Period:** June 16 – June 23, 2026
**Authors:** Subin George, Jewel K M
**Audience:** CRCR Workgroup (Meta, Huawei, Linux Foundation)

---

## 1. Executive Summary

The `TorchedHat/pytorch-redhat-ci` repository was deployed as an external-organization test harness for the Cross-Repository CI Relay (CRCR) system. Over 7 days of live production traffic from `pytorch/pytorch`, the repository received **19,117 workflow dispatches**, validating dispatch delivery, callback authentication, state machine transitions, HUD ingestion, ClickHouse replication, and security controls.

**Key outcomes:**
- **8 automated test workflows** covering 30+ distinct test scenarios across all CRCR pipeline stages
- **Current status: all green** — the most recent 50+ consecutive runs are 100% passing
- **Two distinct failure phases identified and resolved:**
  - **Phase 1 (June 18–22):** Rate limiting (HTTP 429) caused ~73% of total failures — resolved via callback throttling with random jitter
  - **Phase 2 (June 22–23):** PR [#8173](https://github.com/pytorch/test-infra/pull/8173) introduced `${{ job.status }}` in `action.yml`, breaking the callback action for ~13 hours — resolved by PR [#8209](https://github.com/pytorch/test-infra/pull/8209)
- **After #8209 merged (June 23, 04:01 UTC):** 100% pass rate across all workflows
- **CRCR pipeline infrastructure is stable** — no server-side failures observed; all issues traced to client-side rate management and action metadata

---

## 2. Repository Overview

| Property | Value |
|---|---|
| Organization | TorchedHat (external to pytorch) |
| Created | June 16, 2026 |
| Purpose | External-org validation of full CRCR pipeline (L1 dispatch + L2 callbacks + HUD ingestion) |
| Workflows | 8 active test workflows |
| Total Runs | 19,117 |
| Overall Success Rate | 59.2% (11,313 success / 7,645 failure / 149 cancelled) |
| Current Success Streak | 50+ consecutive runs (all passing) |

### Why an external organization?

The CRCR system must support downstream repos owned by organizations outside the PyTorch GitHub org. `TorchedHat` is a separate GitHub organization not affiliated with `pytorch`, making it the correct environment to validate:
- Cross-org `repository_dispatch` delivery
- OIDC token verification from external repos
- Allowlist enforcement for non-PyTorch orgs
- Callback Lambda accepting results from external callers

---

## 3. Test Suite Architecture

### 3.1 Workflow Inventory

| # | Workflow | File | Jobs | Callbacks | Test Focus |
|---|---------|------|------|-----------|-----------|
| 1 | Test: L1 Dispatch Receiver | `test-l1-dispatch-receiver.yml` | 1 | 0 | Validates `repository_dispatch` payload structure (PR fields, push refs) |
| 2 | Test: L2 Callback Lifecycle | `test-l2-callback-lifecycle.yml` | 3 (seq) | 6 | Happy-path `in_progress` → `completed` lifecycle with success and failure conclusions |
| 3 | Test: L2 Callback Edge Cases | `test-l2-edge-cases.yml` | 11 (3 waves) | 21 | Missing OIDC, empty test results, multi-job workflows, `always()` on failure, payload variations, oversized payloads |
| 4 | Test: L2 HUD Ingestion | `test-l2-hud-ingestion.yml` | 1 | 2 | Verifies callback data reaches DynamoDB and is queryable via HUD API |
| 5 | Test: L2 HUD Query Verification | `test-l2-hud-queries.yml` | 1 | 2 | Queries ClickHouse via HUD API to verify replicated data matches callback payload |
| 6 | Test: L2 State Transitions | `test-l2-state-transitions.yml` | 4 (seq) | 6 | Skip-in_progress rejection, stale in_progress, DynamoDB merge semantics, cancel-and-rerun |
| 7 | Test: Security & Input Validation | `test-security.yml` | 4 (seq) | 8 | XSS in artifact URLs, SQL injection in job names, large payloads, Unicode in fields |
| 8 | Concurrency Test | `test-concurrency.yml` | 1 | 2 | Validates GitHub Actions `concurrency` groups and `cancel-in-progress` behavior |

**Total per dispatch:** 47 callbacks across 8 workflows

### 3.2 Test Case Detail

#### L1 — Dispatch Receiver (0 callbacks)
| Test ID | Scenario | Verification |
|---------|----------|-------------|
| L1-01 | PR fields present (number, action, SHA) | Asserts `client_payload.payload.pull_request` fields are non-empty |
| L1-02 | `synchronize` events include updated SHA | Verifies HEAD SHA present on `synchronize` action |
| L1-03 | Push event refs (tags, branches) | Validates ref format for `ciflow/*` tags and branch pushes |

#### L2 — Callback Lifecycle (6 callbacks)
| Test ID | Scenario | Callbacks | Expected |
|---------|----------|-----------|----------|
| lifecycle-happy-path | in_progress → completed(success) | 2 | Both accepted, record in HUD |
| callback-failure-path | in_progress → completed(failure) | 2 | Failure conclusion recorded |
| callback-timing | in_progress → sleep(8s) → completed | 2 | execution_time ≈ 8s |

#### L2 — Edge Cases (21 callbacks, 3 waves)
| Test ID | Scenario | Callbacks | Expected |
|---------|----------|-----------|----------|
| EC-01 | Missing OIDC permission (`id-token: write` not set) | 0 (expected failure) | Callback action fails; OIDC token not mintable |
| EC-03 | Completed without `test-results` field | 2 | Accepted — test_results is optional |
| EC-05 | Multi-job workflow (Job A + Job B) | 4 | Each job gets its own `check_run_id`; both appear on HUD |
| EC-06 | `always()` callback after build failure | 2 | Completed callback fires even when prior step fails |
| TR-01 | Full test_results (passed/failed/skipped/total) | 2 | All 4 fields stored in ClickHouse |
| TR-02 | test_results without `total` field | 2 | HUD computes total = passed + failed + skipped |
| TR-03 | test_results on in_progress (should be ignored) | 2 | in_progress results discarded; completed results used |
| PAYLOAD-04 | conclusion=cancelled | 2 | Accepted or rejected (documents current behavior) |
| PAYLOAD-05 | conclusion=timed_out | 2 | Accepted or rejected (documents current behavior) |
| SIZE-04 | 2.5MB oversized test_results payload | 2 | Rejected at Lambda or HUD API level |

#### L2 — State Transitions (6 callbacks)
| Test ID | Scenario | Callbacks | Expected |
|---------|----------|-----------|----------|
| STATE-04 | Send `completed` without prior `in_progress` | 1 | Rejected by state machine |
| STATE-05 | Send `in_progress` only, skip `completed` | 1 | Record stays as "running" indefinitely (stale job) |
| DYNAMO-06 | Full lifecycle with merge semantics | 2 | started_at (from in_progress) + completed_at (from completed) both set |
| MULTI-05 | Cancel then re-run (failure → new in_progress) | 2 | Each run_attempt gets separate DynamoDB record |

#### L2 — HUD Ingestion (2 callbacks)
| Test ID | Scenario | Callbacks | Expected |
|---------|----------|-----------|----------|
| HUD-INGEST | in_progress → completed, then query HUD API | 2 | Record present at `/api/clickhouse/oot_pr_results` |

#### L2 — HUD Query Verification (2 callbacks)
| Test ID | Scenario | Callbacks | Expected |
|---------|----------|-----------|----------|
| HUD-QUERY | Query ClickHouse for replicated data | 2 | Fields match: repo, job_name, conclusion, test counts |

#### Security & Input Validation (8 callbacks)
| Test ID | Scenario | Callbacks | Expected |
|---------|----------|-----------|----------|
| SEC-10/11 | XSS payload in `artifact-url` | 2 | Stored verbatim; HUD must HTML-escape on render |
| SEC-12 | SQL injection in job name | 2 | Stored verbatim; ClickHouse parameterized queries prevent execution |
| SEC-15 | Large numeric test_results (50K passed) | 2 | Accepted |
| SEC-17 | Unicode in artifact_url (Japanese + emoji) | 2 | Accepted and rendered correctly |

#### Concurrency Test (2 callbacks)
| Test ID | Scenario | Callbacks | Expected |
|---------|----------|-----------|----------|
| CONCURRENCY | Verify `cancel-in-progress` on rapid re-dispatch | 2 | Previous run cancelled, latest run completes |

---

## 4. Mapping to System Integration Plan

The [CRCR Manual & Infrastructure Test Plan](https://github.com/TorchedHat/pytorch-redhat-ci) (June 12, 2026) defined 8 test categories with ~80 test cases across priority levels P0–P2. Below is the coverage mapping.

### 4.1 Automated Coverage (via TorchedHat/pytorch-redhat-ci)

| Plan Section | Plan Tests | Automated | Coverage | Notes |
|---|---|---|---|---|
| **1. HUD API Direct Testing** | 16 tests (AUTH-01..07, HTTP-01..04, SIZE-03..05, PARSE-02..03, SEC-03, SEC-06..07, SEC-12, SEC-14, SEC-16) | 4 | **25%** | SEC-10/11 (XSS), SEC-12 (SQLi), SEC-15 (large payload), SEC-17 (Unicode) automated. AUTH and HTTP tests require direct curl to HUD API (no OIDC bypass possible from GHA). |
| **2. DynamoDB Verification** | 8 tests (DYNAMO-01..05, KEY-02..03, FIELD-03..05) | 2 | **25%** | DYNAMO-06 (merge semantics) and implicit DYNAMO-01/02 (first write + update) covered via lifecycle tests. Direct DynamoDB queries require AWS Console access. |
| **3. DynamoDB → ClickHouse Replication** | 7 tests (REPL-01..07) | 2 | **29%** | HUD-INGEST and HUD-QUERY workflows validate end-to-end replication (REPL-01, REPL-02). Lag measurement (REPL-03) and schema mapping (REPL-04..07) require direct DB access. |
| **4. Frontend Manual Verification** | 18 tests (UI-01..18) | 0 | **0%** | All require browser-based verification. Automated workflows cannot interact with the HUD frontend. |
| **5. OIDC & Lambda Security** | 4 tests (SEC-18..20, SEC-22) | 1 | **25%** | EC-01 (missing OIDC) validates that callbacks without `id-token:write` fail. SEC-18..20 require forged/wrong-audience tokens not producible from GHA. |
| **6. Error Handling & Resilience** | 12 tests (ERR-01, ERR-04..05, NET-01, CH-01..04, FE-01..04) | 0 | **0%** | All require infrastructure-level fault injection (IAM deny, service outage, network blocking). |
| **7. Performance & Load** | 7 tests (PERF-01..06, SEC-21) | 1 | **14%** | SEC-21 (rate limiting) is implicitly validated by the throttling work. PERF-01..06 require dedicated load testing. |
| **8. Regression Tests** | 6 tests (REG-01..06) | 0 | **0%** | Require npm test runs and AWS CLI verification. Suitable for CI in test-infra repo itself. |

### 4.2 Coverage Summary

| Category | Total Plan Tests | Automated | Not Automatable (requires infra access) | Gap (could automate) |
|---|---|---|---|---|
| HUD API | 16 | 4 | 10 | 2 |
| DynamoDB | 8 | 2 | 5 | 1 |
| Replication | 7 | 2 | 4 | 1 |
| Frontend | 18 | 0 | 18 | 0 |
| OIDC/Lambda | 4 | 1 | 3 | 0 |
| Error Handling | 12 | 0 | 12 | 0 |
| Performance | 7 | 1 | 6 | 0 |
| Regression | 6 | 0 | 3 | 3 |
| **Total** | **78** | **10** | **61** | **7** |

**Net automated coverage: ~13% of total plan**, but **~30% of tests that are automatable from GitHub Actions** (10 of ~34 automatable tests).

### 4.3 Additional Tests NOT in the Original Plan

The TorchedHat repo also implements tests **beyond** the original plan:

| Test | Description | Value |
|---|---|---|
| L1-01/02/03 | Dispatch payload validation for PR + push events | Validates the Webhook Lambda's `repository_dispatch` payload structure |
| STATE-04 | Skip-in_progress rejection | State machine correctness |
| STATE-05 | Stale in_progress (orphaned job) | Documents stale job behavior |
| MULTI-05 | Cancel + re-run lifecycle | Multi-attempt keying validation |
| EC-03 | Empty test_results | Optional field handling |
| PAYLOAD-04/05 | conclusion=cancelled/timed_out | Documents extended conclusion support |
| TR-01/02/03 | Test result field handling (full, computed total, in_progress) | Data integrity verification |
| Concurrency | cancel-in-progress behavior | Workflow management |

---

## 5. Run Statistics

### 5.1 Daily Breakdown

| Date | Dispatches Received | Success | Failure | Cancelled | Failure Rate |
|---|---|---|---|---|---|
| June 16 | 1 | 0 | 1 | 0 | 100% (setup) |
| June 17 | 0 | 0 | 0 | 0 | — |
| June 18 | 5,408 | 3,061 | 2,347 | — | **43.4%** |
| June 19 | 2,630 | 1,522 | 1,108 | — | **42.1%** |
| June 20 | 2,111 | 1,267 | 844 | — | **40.0%** |
| June 21 | 1,990 | 1,169 | 821 | — | **41.3%** |
| June 22 | 5,609 | 3,425 | 2,184 | — | **38.9%** |
| June 23 (partial) | 1,211 | 871 | 340 | — | **28.1%** |
| **Total** | **19,117** | **11,313** | **7,645** | **149** | **40.0%** |

### 5.2 Failure Timeline and Root Causes

The failures fall into **three distinct phases**, each with a different root cause:

| Phase | Period | Root Cause | L2+ Failure Rate |
|---|---|---|---|
| **Phase 1: Rate Limiting** | June 18 – June 22, 15:19 UTC | HTTP 429 from CRCR Callback Lambda | ~40% |
| **Phase 2: Action Parse Error** | June 22, 15:19 – June 23, 04:01 UTC | PR [#8173](https://github.com/pytorch/test-infra/pull/8173) broke `action.yml` | **100%** (all L2+ jobs) |
| **Phase 3: All Green** | June 23, 04:01 UTC onwards | PR [#8209](https://github.com/pytorch/test-infra/pull/8209) fixed the parse error | **<1%** (1 unrelated bash bug) |

#### Phase 1: Rate Limiting (June 18 – June 22, 15:19 UTC)

The CRCR Callback Lambda's per-repo sliding-window rate limiter (60 req/min) rejected callbacks when concurrent dispatches caused burst traffic. Verified from failure logs:

```
curl: (22) The requested URL returned error: 429
{"detail": "rate limit exceeded for TorchedHat/pytorch-redhat-ci"}
```

**Mitigation deployed**: Throttle offsets + random jitter (commit `76986ce`, June 22 07:08 UTC). However, this fix was masked by Phase 2 starting ~8 hours later.

#### Phase 2: Action Parse Error (June 22, 15:19 – June 23, 04:01 UTC)

PR [#8173](https://github.com/pytorch/test-infra/pull/8173) (merged June 22 at 15:19 UTC by @atalman) introduced `${{ job.status }}` in the `conclusion` input description of `action.yml`. GitHub's template engine evaluates `${{ }}` expressions in action input descriptions at parse time, but the `job` context is not available in the `inputs:` scope. This caused **every job referencing `cross-repo-ci-relay-callback@main` to fail at "Set up job"**:

```
##[error]Unrecognized named-value: 'job'. Located at position 1 within expression: job.status
##[error]Failed to load pytorch/test-infra/main/.github/actions/cross-repo-ci-relay-callback/action.yml
```

**Impact**: 100% of L2+ callback workflows broken for ~13 hours. L1 dispatch receiver (which doesn't use the callback action) continued to pass, accounting for the ~52% overall success rate during this period.

#### Phase 3: All Green (June 23, 04:01 UTC onwards)

PR [#8209](https://github.com/pytorch/test-infra/pull/8209) (merged June 23 at 04:01 UTC by @subinz1) fixed the parse error by replacing `${{ job.status }}` with `job.status` (plain text, no expression syntax). Combined with the throttling fixes from Phase 1, the result was immediate:

- **0 action parse errors** — action.yml loads successfully
- **0 rate limit errors** — jitter-based throttling keeps callbacks under 60/min
- **Latest 50+ consecutive runs: ALL PASSING**
- **Only 1 failure post-fix**: PR #187054 title contained backticks that caused bash command substitution (test workflow bug, not CRCR infrastructure)

### 5.3 Failure Root Cause Summary

| Cause | Failures | % of Total | Phase | Resolved By |
|---|---|---|---|---|
| HTTP 429 rate limit exceeded | ~5,600 | **73%** | Phase 1 | Throttle offsets + random jitter |
| `action.yml` parse error (`${{ job.status }}`) | ~2,040 | **27%** | Phase 2 | PR #8209 |
| PR title bash injection | 1 | **<0.1%** | Phase 3 | Pending (TorchedHat workflow fix) |

**No CRCR infrastructure-level failures were observed across any phase.** All failures traced to either client-side rate management or a bug in the callback action's YAML metadata.

---

## 6. Rate Limiting: Investigation and Resolution

### 6.1 Problem

The CRCR Callback Lambda enforces a per-repository sliding-window rate limit (60 requests/minute, per RFC-0054). The TorchedHat repo generates 47 callbacks per dispatch across 8 workflows. When multiple dispatches arrive close together (common with `pytorch/pytorch`'s high PR volume — 5+ PRs/minute), the combined callback rate exceeded the limit.

**Example failure pattern (June 22, 06:57 UTC):**
- PR #162454 dispatched at 06:57:17Z → 47 callbacks
- PR #187819 dispatched at 06:57:23Z → 47 callbacks
- Both repos' heavy workflows (edge-cases, state-transitions, security) all started callbacks at the same absolute time
- Combined rate: ~94 callbacks in 60 seconds → rate limit exceeded

### 6.2 Resolution (3 iterations)

| Iteration | Date | Approach | Result |
|---|---|---|---|
| **v1** | June 22, 06:46 | Serialize parallel jobs with `needs:` dependencies; add fixed base offsets (5–40s) | Reduced burst, but concurrent dispatches still collided |
| **v2** | June 22, 06:54 | Increase fixed offsets (50–110s) | Marginal improvement; same-offset collision on concurrent dispatches |
| **v3** | June 22, 07:08 | **Wide offsets (20–420s) + random jitter (`RANDOM % 15-25`)** | **Resolved.** Concurrent dispatches desynchronize via random delays |

### 6.3 Final Throttle Configuration

| Workflow | Base Offset | Jitter | Callbacks | Effective Window |
|---|---|---|---|---|
| lifecycle | 20s | ±20s | 6 | 20–60s |
| hud-ingestion | 70s | ±20s | 2 | 70–90s |
| hud-queries | 120s | ±20s | 2 | 120–140s |
| state-transitions | 170s | ±25s | 6 | 170–220s |
| edge-cases wave 1 | 250–295s | ±15s per job | 7 | 250–310s |
| edge-cases wave 2 | after wave 1 | ±15s per job | 8 | ~325–390s |
| edge-cases wave 3 | after wave 2 | ±15s per job | 6 | ~405–460s |
| security | 420s | ±25s | 8 | 420–480s |

**Per-dispatch peak rate:** ~9 callbacks/minute
**With 3 concurrent dispatches:** ~24–27 callbacks/minute (under 60/min limit)

### 6.4 Commit History (Throttling Work)

```
76986ce  Widen throttle offsets + add random jitter to prevent concurrent dispatch collisions
0a1c9bd  Increase security throttle offset from 40s to 110s
74c9b98  Increase state-transitions throttle offset from 25s to 80s
4b9d4bf  Increase hud-queries throttle offset from 20s to 65s
47ad552  Increase hud-ingestion throttle offset from 15s to 50s
579f94d  Increase lifecycle throttle offset from 5s to 10s
8b8fccc  Increase edge-cases throttle: 90s base offset, 5s inter-job stagger
72e3a19  Throttle test-l2-hud-queries: add 20s callback stagger delay
cf3970d  Throttle test-l2-hud-ingestion: add 15s callback stagger delay
46f7bbc  Throttle test-security: serialize 4 parallel jobs with 40s offset
75b30d2  Throttle test-l2-state-transitions: serialize 4 parallel jobs with 25s offset
22daca2  Throttle test-l2-callback-lifecycle: serialize 3 parallel jobs sequentially
6c8db90  Throttle test-l2-edge-cases: serialize 11 parallel jobs into 3 sequential waves
```

---

## 7. Findings and Observations

### 7.1 CRCR Infrastructure Findings

| # | Finding | Severity | Status |
|---|---------|----------|--------|
| F-01 | **Rate limit not communicated in error response.** When callbacks are rate-limited, the HTTP response does not indicate retry-after timing, making it difficult for downstream repos to self-adjust. | Medium | Open — recommend adding `Retry-After` header or structured error body |
| F-02 | **No client-side rate awareness.** The composite callback action (`cross-repo-ci-relay-callback`) has no built-in rate awareness. Downstream repos must manually manage callback timing. | Medium | Open — recommend documenting rate limit in action README and/or adding optional built-in delay |
| F-03 | **PR #8173 introduced `${{ job.status }}` in action.yml description, breaking the callback action for ~13 hours.** GitHub evaluates expressions in input descriptions at parse time; `job` context is unavailable in `inputs:` scope. Every L2+ workflow using `cross-repo-ci-relay-callback@main` failed at "Set up job" until PR [#8209](https://github.com/pytorch/test-infra/pull/8209) fixed it. **This was the single largest outage in the testing period.** | **Critical** | Fixed (PR #8209, merged June 23 04:01 UTC) |
| F-04 | **Extended conclusions (cancelled, timed_out) now accepted after #8173.** PAYLOAD-04 and PAYLOAD-05 tests can validate these once the action is functional. PR #8173 removed the server-side `success`/`failure` restriction, passing `conclusion` through as-is. | Info | Resolved (PR #8173) |
| F-05 | **Push event dispatches arrive at very high rates.** A single push to `pytorch/pytorch` can trigger 3–6 `repository_dispatch` events (one per ciflow tag), all within 1 second. This amplifies the rate limit pressure. | Info | By design — push dispatches carry different refs |

### 7.2 Test Workflow Bugs

| # | Bug | Impact | Fix |
|---|-----|--------|-----|
| B-01 | **Bash command substitution in PR titles.** The L1 test workflow assigns `PR_TITLE` without proper quoting. PR titles containing backticks (e.g., `` `CUDACachingAllocator` ``) cause `command not found` errors. | 1 false failure observed | Quote `$PR_TITLE` in the test script |
| B-02 | **test-concurrency.yml triggered by push events.** When commits are pushed to the repo itself, the concurrency workflow runs but fails because it expects `client_payload` from a `repository_dispatch`. | 1 false failure observed | Add `if: github.event_name == 'repository_dispatch'` guard |

### 7.3 Positive Observations

| # | Observation |
|---|------------|
| O-01 | **OIDC verification works correctly across organizations.** TorchedHat (external org) callbacks are properly authenticated and accepted. |
| O-02 | **Multi-job workflows produce separate HUD records.** EC-05 confirms each job gets its own `check_run_id` and independent DynamoDB/ClickHouse records. |
| O-03 | **State machine rejects out-of-order callbacks.** STATE-04 confirms `completed` without prior `in_progress` is rejected. |
| O-04 | **HUD data propagation is fast.** HUD-INGEST and HUD-QUERY verify data appears in ClickHouse within the workflow's execution window (~2 min). |
| O-05 | **XSS and SQL injection payloads are stored verbatim.** SEC-10/12 confirms the pipeline doesn't corrupt or strip special characters. Frontend HTML-escaping is the defense layer. |
| O-06 | **Unicode fields handled correctly.** SEC-17 (Japanese + emoji in artifact_url) accepted and queryable. |
| O-07 | **System handles very high throughput.** 19,117 dispatches in 7 days (~115 dispatches/hour average) with no infrastructure-level failures. |

---

## 8. Coverage Gaps and Recommendations

### 8.1 Tests Requiring AWS / Infrastructure Access

These tests from the integration plan **cannot be automated from GitHub Actions** and require manual execution with infrastructure access:

| Category | Tests | Requires |
|---|---|---|
| HUD API direct testing | AUTH-01..07, HTTP-01..04, SIZE-03/05, PARSE-02/03, SEC-03/06/07/14/16 | HUD API token + curl |
| DynamoDB verification | DYNAMO-03..05, KEY-02/03, FIELD-03..05 | AWS Console / CLI |
| Replication verification | REPL-03..07 | ClickHouse query access |
| Error handling | All 12 tests (ERR-01, ERR-04/05, NET-01, CH-01..04, FE-01..04) | AWS IAM / infrastructure control |
| Performance | PERF-01..06 | Load testing infrastructure |
| Regression | REG-01..06 | npm test + AWS CLI |

**Recommendation:** Schedule a dedicated manual testing session with Meta infra access to cover these. Priority: AUTH tests (P0) and Error Handling (P1).

### 8.2 Tests Automatable but Not Yet Implemented

| Test | What's Needed |
|---|---|
| SEC-06/07 (spoofed verified_repo / elevated level) | Requires second test repo in allowlist with different level |
| DYNAMO-03/04 (duplicate idempotency) | Send same callback twice from same workflow; verify no duplication |
| REPL-01/02 (explicit replication check) | Add ClickHouse query step to HUD-QUERY workflow with timestamp comparison |

### 8.3 Recommendations for the Workgroup

| # | Recommendation | Priority | Owner |
|---|---|---|---|
| R-01 | **Document rate limits in callback action README.** Downstream repos need to know the limit (60/min/repo) and plan accordingly. | High | Huawei (PR #8173 scope) |
| R-02 | **Add `Retry-After` header to rate limit responses.** Enables client-side backoff without manual tuning. | Medium | Meta (Lambda code) |
| R-03 | **Fix `${{ job.status }}` parse error in action.yml.** Merge PR [#8209](https://github.com/pytorch/test-infra/pull/8209). | High | Meta (reviewer) |
| R-04 | **Fix PR title quoting bug in L1 test.** Prevents false failures from backtick-containing PR titles. | Low | Red Hat (TorchedHat repo) |
| R-05 | **Schedule manual testing session for P0 infra tests.** Cover AUTH, DynamoDB, and error handling tests. | High | Joint (Meta provides access) |
| R-06 | **Consider reducing callback count for high-volume test repos.** 47 callbacks per dispatch is very high for a test harness. Consider combining some tests. | Medium | Red Hat (TorchedHat repo) |
| R-07 | **Monitor long-term rate limit behavior.** As more downstream repos onboard, the aggregate callback volume will increase. Current per-repo limit of 60/min may need per-org aggregation. | Low | Workgroup |

---

## 9. Appendix

### A. Repository Commit History

```
76986ce  2026-06-22  Widen throttle offsets + add random jitter
0a1c9bd  2026-06-22  Increase security throttle offset (40s → 110s)
74c9b98  2026-06-22  Increase state-transitions throttle offset (25s → 80s)
4b9d4bf  2026-06-22  Increase hud-queries throttle offset (20s → 65s)
47ad552  2026-06-22  Increase hud-ingestion throttle offset (15s → 50s)
579f94d  2026-06-22  Increase lifecycle throttle offset (5s → 10s)
8b8fccc  2026-06-22  Increase edge-cases throttle: 90s base, 5s stagger
72e3a19  2026-06-22  Throttle test-l2-hud-queries: 20s stagger
cf3970d  2026-06-22  Throttle test-l2-hud-ingestion: 15s stagger
46f7bbc  2026-06-22  Throttle test-security: serialize 4 jobs, 40s offset
75b30d2  2026-06-22  Throttle test-l2-state-transitions: serialize 4 jobs
22daca2  2026-06-22  Throttle test-l2-callback-lifecycle: serialize 3 jobs
6c8db90  2026-06-22  Throttle test-l2-edge-cases: 3 sequential waves
39ea3ee  2026-06-16  Add comprehensive CRCR test workflows
8187d1f  2026-06-16  Update README with CRCR testing setup guide
3fa78c0  2026-06-16  Initial commit
```

### B. Workflow Run Statistics (by workflow type, last 100 runs per page)

| Workflow | Success | Failure |
|----------|---------|---------|
| Test: L1 Dispatch Receiver | High (>98%) | Very rare (1 bash quoting bug) |
| Test: L2 Callback Lifecycle | High (post-throttle: 100%) | Pre-throttle: ~40% rate limit |
| Test: L2 Callback Edge Cases | High (post-throttle: 100%) | Pre-throttle: ~40% rate limit |
| Test: L2 HUD Ingestion | High (post-throttle: 100%) | Pre-throttle: ~40% rate limit |
| Test: L2 HUD Query Verification | High (post-throttle: 100%) | Pre-throttle: ~40% rate limit |
| Test: L2 State Transitions | High (post-throttle: 100%) | Pre-throttle: ~40% rate limit |
| Test: Security & Input Validation | High (post-throttle: 100%) | Pre-throttle: ~40% rate limit |
| Concurrency Test | N/A (triggered by push only) | 1 false failure (missing payload guard) |

### C. Related PRs in pytorch/test-infra

| PR | Title | Status | Relevance |
|---|---|---|---|
| [#8170](https://github.com/pytorch/test-infra/pull/8170) | CRCR Callback Lambda | Draft | Core callback processing logic |
| [#8173](https://github.com/pytorch/test-infra/pull/8173) | Update conclusion input description | Open | Extends accepted conclusion values |
| [#8183](https://github.com/pytorch/test-infra/pull/8183) | CRCR HUD integration | Draft | HUD API and frontend components |
| [#8198](https://github.com/pytorch/test-infra/pull/8198) | CRCR Webhook Lambda | Draft | Webhook reception and fan-out |
| [#8209](https://github.com/pytorch/test-infra/pull/8209) | Fix action.yml parse error | Open | Bug fix for `${{ job.status }}` in description |

### D. Related Documents

- [CRCR Manual & Infrastructure Test Plan](./CRCR_Manual_Infra_Test_Plan.md) (June 12, 2026)
- [RFC-0050: Cross-Repository CI Relay](https://github.com/pytorch/rfcs/blob/master/RFC-0050-Cross-Repository-CI-Relay-for-PyTorch-Out-of-Tree-Backends.md)
- [RFC-0054: HUD Integration for OOT CI Results](https://github.com/pytorch/rfcs/blob/master/RFC-0054-HUD-Integration-for-Out-of-Tree-CI-Results.md)
- [CRCR Blog Post Draft](./CRCR_Blog_Post.md)
- [PR Review Comments](./CRCR_PR_Review_Comments.md)
