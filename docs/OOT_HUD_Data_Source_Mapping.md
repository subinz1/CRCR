# OOT HUD — Data Source Mapping

Where every piece of data shown in the mockup comes from, and how it flows through the pipeline.

---

## Pipeline Overview

```
Downstream Repo (GHA workflow)
  │
  ▼  ① OIDC-authenticated POST
Callback Lambda (AWS)
  │  - Validates OIDC token
  │  - Checks allowlist → sets downstream_repo_level (L2/L3/L4)
  │  - Measures ci_metrics (queue_time, execution_time)
  │  - Splits payload into trusted{} + untrusted{}
  │
  ▼  ② POST /api/oot/results (x-hud-internal-bot header)
HUD API (Vercel — pages/api/oot/results.ts)
  │  - Auth check (checkAuthWithApiToken)
  │  - Payload size check (≤ 2MB)
  │  - extractDynamoRecord() → OotWorkflowJobRecord
  │  - writeToDynamo() → UpdateItem
  │
  ▼  ③ DynamoDB UpdateItem
DynamoDB Table: torchci-oot-workflow-job
  │  Key: dynamoKey = "{verified_repo}/{delivery_id}/{workflow_name}/{job_name}/{check_run_id}"
  │
  ▼  ④ DynamoDB Streams → Replicator Lambda
ClickHouse Table: default.oot_workflow_job (SharedReplacingMergeTree)
  │  Mapping in: aws/lambda/clickhouse-replicator-dynamo/lambda_function.py
  │  "torchci-oot-workflow-job" → "default.oot_workflow_job"
  │
  ▼  ⑤ ClickHouse SQL queries via /api/clickhouse/{query_name}
Frontend Pages (Next.js + SWR polling every 60s)
```

---

## Page 1: CRCR Summary (`/oot` → `oot-hud-mockup-crcr-summary.html`)

### Source: `oot_summary` query
**File:** `torchci/clickhouse_queries/oot_summary/query.sql`
**API:** `/api/clickhouse/oot_summary?parameters={"days":"7"}`
**Frontend:** `torchci/pages/oot/index.tsx` → `OotSummaryTable` component

| Mockup Element | ClickHouse Column / Derivation | Origin in Pipeline |
|---|---|---|
| **Backend Repository** (row name) | `downstream_repo` (GROUP BY) | `trusted.verified_repo` — set by Lambda from OIDC-verified repo identity |
| **Level** chip (L2/L3/L4) | `anyLast(downstream_repo_level)` | `trusted.downstream_repo_level` — set by Lambda after allowlist lookup |
| **Pass Rate** | `countIf(conclusion='success') / count()` | Computed from `conclusion` field across all `completed` jobs in time window |
| **Success** count | `countIf(conclusion = 'success')` | Count of jobs where `wf.conclusion = 'success'` |
| **Failures** count | `countIf(conclusion = 'failure')` | Count of jobs where `wf.conclusion = 'failure'` |
| **Total** count | `count()` | All `completed` jobs in time window (`WHERE status = 'completed'`) |
| **Avg Duration** | `avg(duration_seconds)` | ALIAS column: `dateDiff(second, started_at, completed_at)` — from downstream-reported timestamps |
| **Last Run** | `max(started_at)` | `wf.started_at` — downstream-reported timestamp |
| **Time Range** dropdown | `{days: UInt64}` parameter | User-selected: 1, 7, or 30 days |

### Stat Cards (not yet in ClickHouse query — need aggregation on frontend or new query)

| Stat Card | How to Compute |
|---|---|
| **Registered Repos** | `COUNT(DISTINCT downstream_repo)` from `oot_summary` result set |
| **Overall Pass Rate** | `SUM(successes) / SUM(total)` across all rows |
| **Total CI Runs** | `SUM(total)` across all rows |
| **Avg Duration** | `AVG(avg_duration_s)` across all rows (weighted avg would be better) |

### L1 Integrations Section
| Element | Source |
|---|---|
| L1 repo names | **Not in ClickHouse** — L1 repos only receive webhook dispatch, no callbacks. Source: hardcoded list from CRCR allowlist config, or a new metadata endpoint. Callback Lambda knows these from the allowlist but they never appear in `oot_workflow_job` since they don't report back. |

### What Exists vs What's Needed

| Component | Status |
|---|---|
| ClickHouse query `oot_summary` | ✅ Exists |
| Frontend `pages/oot/index.tsx` | ✅ Exists — renders table with repo, level, pass rate, success, failures, total, avg duration, last run |
| Stat cards | ❌ Not implemented — needs frontend-side aggregation from `oot_summary` response |
| L1 links section | ❌ Not implemented — needs either hardcoded config or a new allowlist metadata endpoint |
| Separate L2/L3/L4 table sections | ❌ Current query returns flat list sorted by pass_rate — frontend groups them into one table. Splitting by level needs `GROUP BY downstream_repo, downstream_repo_level` or frontend-side grouping |

---

## Page 2: PR Page — OOT Section (`OotPrSection` → `oot-hud-mockup-pr.html`)

### Source: `oot_pr_results` query
**File:** `torchci/clickhouse_queries/oot_pr_results/query.sql`
**API:** `/api/clickhouse/oot_pr_results?parameters={"pr":"183512"}`
**Frontend:** `torchci/components/oot/OotPrSection.tsx`

| Mockup Element | ClickHouse Column | Origin in Pipeline |
|---|---|---|
| **Backend** name (e.g. `intel/intel-extension-for-pytorch`) | `downstream_repo` | `trusted.verified_repo` |
| **Level** chip (L3/L4) | Not in current query | `trusted.downstream_repo_level` — **needs adding to `oot_pr_results` query** |
| **Job** name (e.g. `build-and-test`) | `job_name` | `untrusted.callback_payload.workflow.job_name` |
| **Status** chip (success/failure/running) | `status` + `conclusion` | `wf.status` and `wf.conclusion` — via `conclusionLabel()` / `conclusionColor()` |
| **Duration** | `duration_seconds` | ALIAS: `dateDiff(second, started_at, completed_at)` |
| **Run link** | `workflow_run_url` | `untrusted.callback_payload.workflow.url` |
| **Artifacts link** | `artifact_url` | `untrusted.callback_payload.workflow.artifact_url` |
| Accordion summary text ("3/4 passed, 1 running") | Computed on frontend | `data.filter(r => r.status === 'completed' && r.conclusion === 'success').length` / `data.filter(r => r.status === 'completed').length` |

### What Exists vs What's Needed

| Component | Status |
|---|---|
| ClickHouse query `oot_pr_results` | ✅ Exists |
| Frontend `OotPrSection.tsx` | ✅ Exists |
| Level chip per row | ❌ Not in query — add `downstream_repo_level` to SELECT |
| PR filtering by SHA (latest commit only) | ❌ Current query filters by `pr_number` only, not SHA. Mockup implies showing results for the latest SHA on the PR |

---

## Page 3: Per-Backend Dashboard (`/oot/[org]/[repo]` → `oot-hud-mockup-crcr-backend.html`)

### Source: `oot_backend_dashboard` query
**File:** `torchci/clickhouse_queries/oot_backend_dashboard/query.sql`
**API:** `/api/clickhouse/oot_backend_dashboard?parameters={"repo":"intel/intel-extension-for-pytorch","days":"7"}`
**Frontend:** `torchci/pages/oot/[org]/[repo].tsx` → `OotMatrix` + `buildMatrix()`

| Mockup Element | ClickHouse Column | Origin in Pipeline |
|---|---|---|
| **Page title** (repo name) | From URL `[org]/[repo]` | Router param |
| **Level** chip (L2) | Not in current query | `trusted.downstream_repo_level` — **needs adding** |
| **PR** number (row identifier) | `pr_number` | `untrusted.callback_payload.payload.pull_request.number` |
| **SHA** | `pytorch_head_sha` | `untrusted.callback_payload.payload.pull_request.head.sha` |
| **Commit message** | Not in ClickHouse | **Not available** — would need GitHub API lookup or cross-join with `push` table |
| **Author** | Not in ClickHouse | **Not available** — would need GitHub API or cross-join with `pull_request` table |
| **Time** (relative, e.g. "12m ago") | `started_at` | Downstream-reported timestamp, formatted as relative time |
| **Job columns** (build, test-float32, etc.) | `job_name` per cell | Dynamic columns built from `buildMatrix()` — pivots `job_name` values as columns |
| **Job status chip** (success/failure/running) | `status` + `conclusion` per job | `conclusionLabel()` + `conclusionColor()` |
| **Chip tooltip** (duration, tests, queue time) | `duration_seconds`, `total_tests`, `passed_tests`, `queue_time` | All from ClickHouse row, formatted in `JobChip` component |
| **Health summary** ("Pass rate: 91.7%, 44/48 passed") | Computed on frontend | `HealthSummary` component aggregates `completed` jobs |
| **Workflow run link** (chip href) | `workflow_run_url` | `untrusted.callback_payload.workflow.url` |
| **Artifact link** | `artifact_url` | `untrusted.callback_payload.workflow.artifact_url` |

### What Exists vs What's Needed

| Component | Status |
|---|---|
| ClickHouse query `oot_backend_dashboard` | ✅ Exists |
| Frontend `pages/oot/[org]/[repo].tsx` | ✅ Exists — matrix view with PR rows × job columns |
| Level chip on page header | ❌ Not shown — could use first row's `downstream_repo_level` or a separate query |
| Commit message column | ❌ Not in `oot_workflow_job` — needs cross-table join or GitHub API |
| Author column | ❌ Not in `oot_workflow_job` — needs cross-table join or GitHub API |
| Test results detail in tooltip | ✅ In query (`total_tests`, `passed_tests`, `failed_tests`, `skipped_tests`) |

---

## Page 4: HUD Main Page — CRCR Columns (`oot-hud-mockup.html`)

### Source: **Not yet implemented**

The main HUD homepage (`/[repoOwner]/[repoName]/[branch]`) currently shows pytorch-native CI job columns. The mockup adds collapsible CRCR group columns (e.g. "intel", "ascend", "cambricon") showing O/X/? per commit row.

| Mockup Element | How to Get Data |
|---|---|
| CRCR column group headers (e.g. "intel ▸") | Derived from `DISTINCT downstream_repo` from `oot_workflow_job` |
| Sub-column headers (e.g. "build", "test-xpu") | Derived from `DISTINCT job_name` per `downstream_repo` |
| Per-cell O/X/? conclusion | Join `oot_workflow_job` on `pytorch_head_sha` matching the commit SHA for that row. Aggregate: all jobs success → O, any failure → X, any in_progress → ? |
| Tooltip (e.g. "2/4 passed, 2 running\nbuild: O, test-xpu: ?") | Per-job breakdown from `oot_workflow_job WHERE pytorch_head_sha = {sha}` |

### What's Needed

This is the **biggest gap**. The existing HUD main page queries (`workflow_job` table) don't include OOT data. Options:

1. **New ClickHouse query** (e.g. `oot_hud_columns`): query `oot_workflow_job` grouped by `pytorch_head_sha`, `downstream_repo`, `job_name` — return one row per SHA-repo-job combination with `conclusion`
2. **Frontend integration**: The HUD main page (`components/hud/HudTable.tsx` or equivalent) needs to merge OOT column data alongside native CI columns
3. **Performance**: Need to efficiently load OOT data for ~50 commits × N repos × M jobs — likely a batch query by SHA list

---

## Full Field Mapping: Relay → DynamoDB → ClickHouse

| DynamoDB / ClickHouse Field | Type | Source (trusted vs untrusted) | Extracted By |
|---|---|---|---|
| `dynamoKey` | String (PK) | Composite: `{verified_repo}/{delivery_id}/{workflow_name}/{job_name}/{check_run_id}` | `extractDynamoRecord()` |
| `status` | String | `untrusted.callback_payload.workflow.status` | `extractDynamoRecord()` |
| `downstream_repo` | String | `trusted.verified_repo` ✅ relay-verified | `extractDynamoRecord()` |
| `upstream_repo` | String | `untrusted.callback_payload.payload.repository.full_name` (default: `pytorch/pytorch`) | `extractDynamoRecord()` |
| `pr_number` | UInt64 | `untrusted.callback_payload.payload.pull_request.number` (default: 0) | `extractDynamoRecord()` |
| `pytorch_head_sha` | String | `untrusted.callback_payload.payload.pull_request.head.sha` (default: "") | `extractDynamoRecord()` |
| `delivery_id` | String | `untrusted.callback_payload.delivery_id` | `extractDynamoRecord()` |
| `workflow_run_url` | String | `untrusted.callback_payload.workflow.url` | `extractDynamoRecord()` |
| `workflow_name` | String | `untrusted.callback_payload.workflow.name` | `extractDynamoRecord()` |
| `job_name` | String | `untrusted.callback_payload.workflow.job_name` (**required**) | `extractDynamoRecord()` |
| `check_run_id` | String | `untrusted.callback_payload.workflow.check_run_id` (**required**) | `extractDynamoRecord()` |
| `run_id` | String | `untrusted.callback_payload.workflow.run_id` | `extractDynamoRecord()` |
| `run_attempt` | UInt32 | `untrusted.callback_payload.workflow.run_attempt` (default: 1) | `extractDynamoRecord()` |
| `conclusion` | String | `untrusted.callback_payload.workflow.conclusion` (only on `completed`) | `extractDynamoRecord()` |
| `queue_time` | Float64? | `trusted.ci_metrics.queue_time` ✅ relay-measured | `extractDynamoRecord()` |
| `execution_time` | Float64? | `trusted.ci_metrics.execution_time` ✅ relay-measured | `extractDynamoRecord()` |
| `started_at` | DateTime64 | `untrusted.callback_payload.workflow.started_at` | `extractDynamoRecord()` |
| `completed_at` | DateTime64 | `untrusted.callback_payload.workflow.completed_at` (only on `completed`) | `extractDynamoRecord()` |
| `total_tests` | UInt64 | Computed: `test_results.total` or `passed + failed + skipped` (only on `completed`) | `extractDynamoRecord()` |
| `passed_tests` | UInt64 | `untrusted.callback_payload.workflow.test_results.passed` | `extractDynamoRecord()` |
| `failed_tests` | UInt64 | `untrusted.callback_payload.workflow.test_results.failed` | `extractDynamoRecord()` |
| `skipped_tests` | UInt64 | `untrusted.callback_payload.workflow.test_results.skipped` | `extractDynamoRecord()` |
| `artifact_url` | String | `untrusted.callback_payload.workflow.artifact_url` | `extractDynamoRecord()` |
| `downstream_repo_level` | String | `trusted.downstream_repo_level` ✅ relay-determined from allowlist | `extractDynamoRecord()` |
| `environment` | String | Not currently extracted (placeholder in schema) | — |
| `failed_tests_json` | String | Not currently extracted (placeholder in schema) | — |
| `repository_full_name` | ALIAS | `= downstream_repo` | ClickHouse ALIAS |
| `duration_seconds` | ALIAS | `= dateDiff(second, started_at, completed_at)` | ClickHouse ALIAS |

---

## Gaps & Missing Pieces

| # | Gap | Impact | Fix |
|---|---|---|---|
| 1 | **L1 repos not in ClickHouse** | CRCR Summary L1 section can't be dynamically populated | Expose allowlist metadata from Lambda config, or maintain a static config in HUD |
| 2 | **`downstream_repo_level` missing from `oot_pr_results` query** | PR page can't show L2/L3/L4 chip per backend | Add column to SELECT in `oot_pr_results/query.sql` |
| 3 | **No HUD main page integration** | CRCR columns on homepage are mockup-only | New ClickHouse query + frontend component for OOT columns merged into HudTable |
| 4 | **Commit message / author not in `oot_workflow_job`** | Backend dashboard can't show these columns | Cross-join with `push` or `pull_request` ClickHouse tables using `pytorch_head_sha` |
| 5 | **Stat cards not computed** | CRCR Summary stat cards are static in mockup | Aggregate from `oot_summary` response on frontend, or add a summary row to the query |
| 6 | **No SHA-scoped PR results** | PR page might show stale results for old SHAs | Add `pytorch_head_sha` parameter to `oot_pr_results` query |
| 7 | **Separate L2/L3/L4 table sections** | Current summary query returns flat list | Frontend-side grouping by `downstream_repo_level`, or three separate queries |
