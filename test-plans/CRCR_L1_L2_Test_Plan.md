# CRCR L1/L2 Comprehensive Test Plan

## Overview

End-to-end test coverage for the Cross-Repository CI Relay (CRCR) pipeline covering L1 (dispatch) and L2 (callback + HUD ingestion) flows. Tests are implemented as GitHub Actions workflows in a fork of `pytorch/crcr-test` and triggered via `repository_dispatch` (production path) and `workflow_dispatch` (manual testing).

## Architecture Under Test

```
pytorch/pytorch (PR / push)
      │
      ▼
  Webhook Lambda (L1)
  ├── HMAC signature verification
  ├── Upstream repo + PR action filter
  ├── Allowlist resolution (L1–L4)
  ├── repository_dispatch to downstream repos
  └── Redis DISPATCHED state write
      │
      ▼
  Downstream Workflow (crcr-test)
  ├── Receive repository_dispatch
  ├── Concurrency + cancel-in-progress
  ├── Build / test (simulated)
  └── Callback via cross-repo-ci-relay-callback action (L2)
      │
      ▼
  Callback Lambda (L2)
  ├── OIDC token verification
  ├── Allowlist L2+ check + rate limit
  ├── Redis state machine (DISPATCHED → IN_PROGRESS → COMPLETED)
  ├── CI timing metrics (queue_time, execution_time)
  └── Forward to HUD API
      │
      ▼
  HUD Ingestion
  ├── /api/oot/results (auth + extract + DynamoDB UpdateItem)
  ├── DynamoDB Streams → ClickHouse replicator
  └── HUD pages query ClickHouse (oot_summary, oot_pr_results, oot_backend_dashboard)
```

---

## Category 1: L1 Dispatch Receiver Tests

**Workflow:** `test-l1-dispatch-receiver.yml`
**Purpose:** Validate that dispatches arrive correctly and payloads are well-formed.

| ID | Scenario | Assertion |
|----|----------|-----------|
| L1-01 | PR `opened` dispatch | `event_type == pull_request`, `delivery_id` non-empty, `payload.pull_request.number` exists |
| L1-02 | PR `synchronize` dispatch | Head SHA is present and non-empty |
| L1-03 | PR `closed` dispatch | `cancel-workflow` job runs, `inspect` job is skipped |
| L1-04 | Push event dispatch | `event_type == push`, `payload.ref` and `payload.after` present |
| L1-05 | Upstream repo validation | `payload.repository.full_name == pytorch/pytorch` |
| L1-06 | Payload completeness | All fields in Key Fields Reference table are accessible |

**Trigger:** `repository_dispatch` types `[pull_request, push]` + `workflow_dispatch` for manual runs.

---

## Category 2: L2 Callback Lifecycle Tests

**Workflow:** `test-l2-callback-lifecycle.yml`
**Purpose:** Validate the full callback round-trip from in_progress to completed.

| ID | Scenario | Assertion |
|----|----------|-----------|
| L2-01 | `in_progress` callback | HTTP 200, step succeeds |
| L2-02 | `completed` with `conclusion=success` | HTTP 200, step succeeds |
| L2-03 | `completed` with `conclusion=failure` | HTTP 200, step succeeds (non-zero exit only if callback itself fails) |
| L2-04 | `check_run_id` populated | `job.check_run_id` context is non-empty in callback payload |
| L2-05 | `started_at` / `completed_at` timestamps | `in_progress` sets `started_at`, `completed` sets `completed_at` |
| L2-06 | `test_results` included | JSON with passed/failed/skipped/total is sent |
| L2-07 | `artifact_url` included | URL points to current workflow run |
| L2-08 | Callback timing | Both callbacks complete within 10s (`max-time` default) |

**Trigger:** `repository_dispatch` type `pull_request` + `workflow_dispatch`.

---

## Category 3: L2 Callback Edge Cases

**Workflow:** `test-l2-edge-cases.yml`
**Purpose:** Validate error handling and boundary conditions.

| ID | Scenario | Assertion |
|----|----------|-----------|
| EC-01 | Missing OIDC permission | Job without `id-token: write` fails at OIDC token mint step |
| EC-02 | Invalid conclusion value | Action rejects `cancelled` / `timed_out` with `::error::` (tracks issue #6) |
| EC-03 | Empty `test-results` | Callback succeeds without test data |
| EC-04 | Callback on cancellation | `if: cancelled()` step attempts `conclusion=failure` callback |
| EC-05 | Multiple jobs reporting | Two parallel jobs send independent callbacks with distinct `check_run_id` |
| EC-06 | `always()` callback on failure | When build step fails, `if: always()` callback still fires with `conclusion=failure` |

**Trigger:** `repository_dispatch` type `pull_request` + `workflow_dispatch`.

---

## Category 4: HUD Ingestion Verification

**Workflow:** `test-l2-hud-ingestion.yml`
**Purpose:** Validate that callback data reaches HUD and is queryable in ClickHouse.

| ID | Scenario | Assertion |
|----|----------|-----------|
| HUD-01 | Record exists after callback | Query `oot_pr_results` via HUD API returns record for the dispatched PR |
| HUD-02 | Field accuracy | `downstream_repo`, `pr_number`, `pytorch_head_sha` match dispatched values |
| HUD-03 | Conclusion correctness | ClickHouse `conclusion` matches what was sent in callback |
| HUD-04 | Timing metrics populated | `queue_time` and `execution_time` are non-null for completed records |
| HUD-05 | Workflow URL correctness | `workflow_run_url` points to the actual Actions run |
| HUD-06 | UpdateItem merge | `completed` callback does not clobber `started_at` or `queue_time` from `in_progress` callback |

**Trigger:** `repository_dispatch` type `pull_request` + `workflow_dispatch`.
**Note:** HUD queries require propagation delay (DynamoDB → ClickHouse). Tests include a polling step with timeout.

---

## Category 5: Concurrency and Cancellation Tests

**Workflow:** `test-concurrency.yml`
**Purpose:** Validate cancel-in-progress behavior and PR lifecycle edge cases.

| ID | Scenario | Assertion |
|----|----------|-----------|
| CC-01 | Newer dispatch cancels older | Second `synchronize` dispatch cancels first run via concurrency group |
| CC-02 | PR `closed` cancels in-flight | `closed` dispatch triggers `cancel-workflow` and terminates running CI |
| CC-03 | Cancelled run leaves stale record | Cancelled run's `in_progress` record remains in HUD as "running" (documents issue #5) |
| CC-04 | Concurrency group isolation | Different PR numbers use different concurrency groups |

**Trigger:** `repository_dispatch` type `pull_request` + `workflow_dispatch`.

---

## Workflow Structure Convention

All test workflows follow this pattern:

```yaml
on:
  repository_dispatch:
    types: [pull_request]      # or [pull_request, push]
  workflow_dispatch:            # manual trigger for testing
    inputs:
      pr_number:
        description: "PR number (for manual testing)"
        required: false
        default: "0"

concurrency:
  group: test-{category}-{pr_number || run_id}
  cancel-in-progress: true

permissions:
  actions: write
  id-token: write              # L2 workflows only

jobs:
  # Test assertions use step outputs + if: conditions
  # Results written to step summary
```

---

## Implementation

- **Repository:** Fork of `pytorch/crcr-test` at `subinz1/crcr-test`
- **Branch:** `test/comprehensive-l1-l2-tests`
- **PR:** Against fork's `main` branch (not upstream)
- **Workflows:** 5 files in `.github/workflows/`

## References

- [Callback Action](https://github.com/pytorch/test-infra/blob/main/.github/actions/cross-repo-ci-relay-callback/action.yml)
- [Callback Lambda](https://github.com/pytorch/test-infra/blob/main/aws/lambda/cross_repo_ci_relay/callback/callback_handler.py)
- [HUD ootUtils](https://github.com/pytorch/test-infra/blob/main/torchci/lib/oot/ootUtils.ts)
- [ClickHouse Schema](https://github.com/pytorch/test-infra/blob/main/clickhouse_db_schema/default.oot_workflow_job/schema.sql)
- [Issue #5 — Stale in_progress cleanup](https://github.com/pytorch/crcr-test/issues/5)
- [Issue #6 — Conclusion value alignment](https://github.com/pytorch/crcr-test/issues/6)
