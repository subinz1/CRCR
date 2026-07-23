# OOT HUD Mockup: Variable-to-Source Mapping

> Maps every data value displayed in the hosted HTML mockup (`oot_hud_mockup.html`) back to its ClickHouse column, the SQL query that fetches it, the relay payload field that populates it, and the exact file + function in our PR that writes it.

---

## How to Read This Document

Each mockup view has a table where:
- **HTML column** = what appears as a column header or UI element in the mockup
- **Example value** = a sample value shown in the mockup
- **ClickHouse column** = the column name in `default.oot_workflow_job`
- **SQL query** = which query file fetches this data
- **SQL expression** = how the value is computed or selected
- **Relay → HUD** = the path from the relay payload to our extraction function
- **Write function** = the function in our PR that writes this to DynamoDB

---

## View 3: OOT Summary (`/oot`) — `pages/oot/index.tsx`

**Query file:** `clickhouse_queries/oot_summary/query.sql`
**Frontend file:** `torchci/pages/oot/index.tsx` → `OotSummaryTable()` (line 46)
**React interface:** `OotSummaryRow` (line 28)

| HTML Column | Example Value | CH Column | SQL Expression | Relay Payload Path | `extractDynamoRecord()` Line | `writeToDynamo()` → DynamoDB Column |
|---|---|---|---|---|---|---|
| **Backend Repository** | `<company-b>/pytorch-<hardware-b>` | `downstream_repo` | `downstream_repo AS repo` | `trusted.verified_repo` (OIDC-proven) | line 109 | `downstream_repo` |
| **Level** | `L2` | `downstream_repo_level` | `anyLast(downstream_repo_level)` | `trusted.downstream_repo_level` (relay allowlist) | line 123 | `downstream_repo_level` |
| **Pass Rate** | `65.0%` (red chip) | *derived* | `if(total > 0, successes / total, 0) AS pass_rate` | Not a stored field — computed from `conclusion` at query time | — | — |
| **Success** | `26` | *derived* | `countIf(conclusion = 'success') AS successes` | Computed from per-job `conclusion` values | — | — |
| **Failures** | `14` | *derived* | `countIf(conclusion = 'failure') AS failures` | Computed from per-job `conclusion` values | — | — |
| **Total** | `40` | *derived* | `count() AS total` | Count of all completed jobs for this repo | — | — |
| **Avg Duration** | `31m 5s` | `duration_seconds` | `avg(duration_seconds) AS avg_duration_s` | `untrusted.callback_payload.workflow.completed_at` minus `started_at` (computed by ClickHouse or stored by downstream) | line 145 (`completed_at`), 139 (`started_at`) | `completed_at`, `started_at` |
| **Last Run** | `5/12/2026, 1:10 PM` | `started_at` | `max(started_at) AS last_run` | `untrusted.callback_payload.workflow.started_at` | line 139 | `started_at` |

**Derived fields explained:**
- `pass_rate`, `successes`, `failures`, `total` are all **computed at query time** by ClickHouse aggregation functions. No one sends these values — they are derived from individual job rows where each row has `conclusion = 'success'` or `'failure'` (written on the completed callback).
- The `WHERE status = 'completed'` filter ensures only finished jobs are counted.
- `GROUP BY repo` aggregates per downstream repository.
- The `FINAL` keyword on the table read ensures ClickHouse deduplicates by `dynamoKey` (ReplacingMergeTree).

**What feeds the individual `conclusion` values:**
```
Downstream CI finishes
  → L2 relay receives completed callback with conclusion: "success"/"failure"
    → Relay forwards {trusted, untrusted} to HUD API
      → results.ts handler() [line 17]
        → extractDynamoRecord() [line 142-143]
          if (wf.status === "completed") record.conclusion = wf.conclusion
        → writeToDynamo() [line 162]
          DynamoDB UpdateItem: SET #n_conclusion = :v_conclusion
            → DynamoDB Streams → clickhouse-replicator-dynamo
              → INSERT INTO default.oot_workflow_job (conclusion = 'success')
```

---

## View 4: Per-Backend Dashboard (`/oot/[org]/[repo]`) — `pages/oot/[org]/[repo].tsx`

**Query file:** `clickhouse_queries/oot_backend_dashboard/query.sql`
**Frontend file:** `torchci/pages/oot/[org]/[repo].tsx` → `OotMatrix()` (line 169)
**React interface:** `OotJobRow` (line 30)

### Health Summary Bar

| HTML Element | Example Value | Source |
|---|---|---|
| **Pass rate chip** | `Pass rate: 78.3%` (orange) | Computed client-side in `HealthSummary()` (line 150): `success / completed.length` — not from ClickHouse |
| **Jobs count** | `47/60 jobs passed` | Computed client-side: `completed.filter(j => j.conclusion === "success").length` / `completed.length` |

### Matrix Header Row (Column Names = Job Names)

| HTML Column | Example Values | Source |
|---|---|---|
| **PR** | `#183512` | Static column |
| **SHA** | `a1b2c3d` | Static column |
| **Job name columns** | `build`, `test-float32`, `test-float16`, etc. | `job_name` column from ClickHouse, collected by `buildMatrix()` → `jobNamesSet` (line 120-126) |

### Matrix Data Rows

| HTML Element | Example Value | CH Column | SQL Expression | Relay Payload Path | `extractDynamoRecord()` Line |
|---|---|---|---|---|---|
| **PR** | `#183512` | `pr_number` | `pr_number` (SELECT) | `untrusted.callback_payload.payload.pull_request.number` | line 111 |
| **SHA** | `a1b2c3d` | `pytorch_head_sha` | `pytorch_head_sha` (SELECT) | `untrusted.callback_payload.payload.pull_request.head.sha` | line 112 |
| **Cell character** (O/X/?/C/F) | `O` (green) = success | `status` + `conclusion` | `status`, `conclusion` (SELECT) | `untrusted.callback_payload.workflow.status` / `.conclusion` | line 108, 143 |

### Cell Tooltip Content

| Tooltip Line | Example | CH Column | SQL Expression | Relay Payload Path | `extractDynamoRecord()` Line |
|---|---|---|---|---|---|
| **Job name** | `Job: test-float32` | `job_name` | `job_name` (SELECT) | `untrusted.callback_payload.workflow.job_name` | line 116 |
| **Attempt** | `Attempt: 2` | `run_attempt` | `run_attempt` (SELECT) | `untrusted.callback_payload.workflow.run_attempt` | line 119 |
| **Duration** | `Duration: 18m 32s` | `duration_seconds` | `duration_seconds` (SELECT) | Computed from `started_at` / `completed_at` | line 139, 145 |
| **Tests** | `Tests: 1240/1240 passed` | `passed_tests`, `total_tests` | `passed_tests`, `total_tests` (SELECT) | `untrusted.callback_payload.workflow.test_results.passed` / `.total` | line 150-151 |
| **Queue time** | `Queue: 12.3s` | `queue_time` | `queue_time` (SELECT) | `trusted.ci_metrics.queue_time` (relay-measured) | line 131 |

### Cell Click → Link

| Action | Destination | CH Column | Relay Payload Path | `extractDynamoRecord()` Line |
|---|---|---|---|---|
| Click chip | Opens GHA workflow run | `workflow_run_url` | `untrusted.callback_payload.workflow.url` | line 114 |

### Job deduplication logic (`buildMatrix()` line 116-148)

When multiple rows exist for the same PR + job_name (e.g., retries):
- `run_attempt` is compared: `if (!existing || job.run_attempt > existing.run_attempt)` (line 138)
- The latest attempt wins and is displayed in the matrix cell.

---

## View 2: PR Page — OOT Section — `components/oot/OotPrSection.tsx`

**Query file:** `clickhouse_queries/oot_pr_results/query.sql`
**Frontend file:** `torchci/components/oot/OotPrSection.tsx` → `OotPrSection()` (line 62)
**React interface:** `OotPrResult` (line 22)

### Accordion Header

| HTML Element | Example Value | Source |
|---|---|---|
| **Title** | `Out-of-Tree Backends` | Static text (line 96) |
| **Summary** | `(3/5 passed, 1 running)` | Computed client-side (lines 72-89): `successCount`/`totalCompleted`, `inProgress` count |

### Table Rows

| HTML Column | Example Value | CH Column | SQL Expression | Relay Payload Path | `extractDynamoRecord()` Line |
|---|---|---|---|---|---|
| **Backend** | `<company-a>/<hardware-a>-ops` | `downstream_repo` | `downstream_repo` (SELECT) | `trusted.verified_repo` (OIDC-proven) | line 109 |
| **Job** | `test-float32` | `job_name` | `job_name` (SELECT) | `untrusted.callback_payload.workflow.job_name` | line 116 |
| **Status** | `success` (green chip) | `status` + `conclusion` | `status`, `conclusion` (SELECT) | `untrusted.callback_payload.workflow.status` / `.conclusion` | line 108, 143 |
| **Duration** | `18m 32s` | `duration_seconds` | `duration_seconds` (SELECT) | Computed from timestamps | line 139, 145 |
| **Run link** | `Run` → GHA page | `workflow_run_url` | `workflow_run_url` (SELECT) | `untrusted.callback_payload.workflow.url` | line 114 |
| **Artifacts link** | `Artifacts` → downstream storage | `artifact_url` | `artifact_url` (SELECT) | Downstream-reported URL | — (not yet extracted in current code) |

### Status chip coloring logic (`conclusionColor()` line 39-55)

| `status` | `conclusion` | Chip color | Chip label | HTML class in mockup |
|---|---|---|---|---|
| `in_progress` | *(any)* | `info` (blue) | `running` | `chip-info` |
| `completed` | `success` | `success` (green) | `success` | `chip-success` |
| `completed` | `failure` | `error` (red) | `failure` | `chip-error` |
| `completed` | `cancelled` | `warning` (orange) | `cancelled` | `chip-warning` |
| `completed` | `timed_out` | `warning` (orange) | `timed_out` | `chip-warning` |

---

## Complete Write Pipeline: From Relay to ClickHouse

This traces every field from the moment it arrives at our HUD API to when it's available in ClickHouse for the frontend to query.

### Step-by-step for each field

```
┌──────────────────────────────────────────────────────────────────────────────┐
│  RELAY sends POST /api/oot/results                                          │
│  Body: { trusted: {...}, untrusted: {...} }                                 │
│  Header: X-OOT-Relay-Token: <token>                                        │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  results.ts : handler()                    [pages/api/oot/results.ts:17]    │
│                                                                              │
│  1. Auth: req.headers["x-oot-relay-token"] === process.env.OOT_RELAY_TOKEN  │
│  2. Size: validatePayloadSize(rawBody)     [lib/oot/ootUtils.ts:83]         │
│  3. Parse: body = JSON.parse(req.body)                                       │
│  4. Extract: record = extractDynamoRecord(body)                              │
│  5. Write: writeToDynamo(record)                                             │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  extractDynamoRecord()                     [lib/oot/ootUtils.ts:91]         │
│                                                                              │
│  INPUT payload = {                                                           │
│    trusted: {                                                                │
│      verified_repo ─────────────────────→ record.downstream_repo   [109]    │
│      downstream_repo_level ─────────────→ record.downstream_repo_level[123] │
│      ci_metrics.queue_time ─────────────→ record.queue_time        [131]    │
│      ci_metrics.execution_time ─────────→ record.execution_time    [134]    │
│    },                                                                        │
│    untrusted: {                                                              │
│      callback_payload: {                                                     │
│        delivery_id ─────────────────────→ record.delivery_id       [113]    │
│        payload.pull_request.number ─────→ record.pr_number         [111]    │
│        payload.pull_request.head.sha ───→ record.pytorch_head_sha  [112]    │
│        payload.repository.full_name ────→ record.upstream_repo     [110]    │
│        workflow: {                                                            │
│          status ────────────────────────→ record.status             [108]    │
│          conclusion (if completed) ─────→ record.conclusion        [143]    │
│          name ──────────────────────────→ record.workflow_name      [115]    │
│          url ───────────────────────────→ record.workflow_run_url   [114]    │
│          job_name ──────────────────────→ record.job_name           [116]    │
│          check_run_id ──────────────────→ record.check_run_id      [117]    │
│          run_id ────────────────────────→ record.run_id             [118]    │
│          run_attempt ───────────────────→ record.run_attempt        [119]    │
│          started_at ────────────────────→ record.started_at         [139]    │
│          completed_at (if completed) ───→ record.completed_at      [145]    │
│          test_results.total ────────────→ record.total_tests       [150]    │
│          test_results.passed ───────────→ record.passed_tests      [151]    │
│          test_results.failed ───────────→ record.failed_tests      [152]    │
│          test_results.skipped ──────────→ record.skipped_tests     [153]    │
│        }                                                                     │
│      }                                                                       │
│    }                                                                         │
│  }                                                                           │
│                                                                              │
│  COMPUTED:                                                                   │
│  dynamoKey = "{verified_repo}/{delivery_id}/{wf.name}/{job_name}/{check_run_id}" [104] │
│                                                                              │
│  OUTPUT: OotWorkflowJobRecord (flat object with all fields above)            │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  writeToDynamo()                           [lib/oot/ootUtils.ts:162]        │
│                                                                              │
│  For each field in record (skip dynamoKey, skip undefined):                  │
│    Build: SET #n_status = :v_status, #n_conclusion = :v_conclusion, ...      │
│                                                                              │
│  DynamoDB UpdateItem:                                                        │
│    TableName: "torchci-oot-workflow-job"                                      │
│    Key: { dynamoKey: record.dynamoKey }                                      │
│    UpdateExpression: "SET #n_status = :v_status, ..."                        │
│                                                                              │
│  WHY UpdateItem (not PutItem):                                               │
│    Callback 1 (in_progress): sets status, queue_time, started_at             │
│    Callback 2 (completed):   sets status, conclusion, execution_time, tests  │
│    UpdateItem only touches fields present → queue_time is NOT overwritten    │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  DynamoDB Streams → clickhouse-replicator-dynamo Lambda                      │
│  [aws/lambda/clickhouse-replicator-dynamo/lambda_function.py]                │
│                                                                              │
│  SUPPORTED_TABLES line 36:                                                   │
│    "torchci-oot-workflow-job" → "default.oot_workflow_job"                    │
│                                                                              │
│  unmarshal() [line 124]: Converts DynamoDB wire format to plain JSON         │
│  upsert_documents() [line 187]:                                              │
│    INSERT INTO default.oot_workflow_job                                       │
│    SETTINGS async_insert=1, wait_for_async_insert=1                          │
│    FORMAT JSONEachRow {...}                                                   │
│                                                                              │
│  Latency: ~2-5 seconds (event-driven, not polled)                            │
└─────────────────────────────┬────────────────────────────────────────────────┘
                              │
                              ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│  ClickHouse: default.oot_workflow_job (SharedReplacingMergeTree)              │
│                                                                              │
│  All fields from DynamoDB are now available as CH columns.                    │
│  FINAL keyword deduplicates by dynamoKey (keeps latest version).             │
│                                                                              │
│  Frontend queries read from here:                                            │
│    oot_summary/query.sql         → aggregates per repo                       │
│    oot_backend_dashboard/query.sql → per-job rows for one repo               │
│    oot_pr_results/query.sql      → per-job rows for one PR                   │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## ClickHouse Column → HTML Mockup Cross-Reference

This is the reverse lookup: given a ClickHouse column, where does it appear in the mockup?

| CH Column | Type | View 3: OOT Summary | View 4: Per-Backend Dashboard | View 2: PR OOT Section |
|---|---|---|---|---|
| `downstream_repo` | String | ✅ "Backend Repository" column | ✅ Page header (`<company-a>/<hardware-a>-ops`) | ✅ "Backend" column |
| `downstream_repo_level` | String | ✅ "Level" column (L2/L3/L4 chip) | — | — |
| `status` | String | ✅ `WHERE status='completed'` filter | ✅ Cell char (? for in_progress) | ✅ Status chip ("running") |
| `conclusion` | String | ✅ `countIf(conclusion='success')` for pass rate | ✅ Cell char (O/X/C) + color | ✅ Status chip color + label |
| `pr_number` | UInt64 | — | ✅ "PR" column (`#183512`) | ✅ Query filter (`WHERE pr_number = N`) |
| `pytorch_head_sha` | String | — | ✅ "SHA" column (`a1b2c3d`) | — |
| `job_name` | String | — | ✅ Column headers (`test-float32`, `build`, etc.) | ✅ "Job" column |
| `duration_seconds` | Float64 | ✅ `avg(duration_seconds)` → "Avg Duration" | ✅ Tooltip: "Duration: 18m 32s" | ✅ "Duration" column |
| `started_at` | DateTime | ✅ `max(started_at)` → "Last Run" | ✅ `ORDER BY started_at DESC` | ✅ `ORDER BY started_at DESC` |
| `completed_at` | DateTime | — | ✅ Available (not shown in mockup) | — |
| `total_tests` | UInt32 | — | ✅ Tooltip: "Tests: 1240/1240 passed" | — |
| `passed_tests` | UInt32 | — | ✅ Tooltip: "Tests: 1240/1240 passed" | — |
| `failed_tests` | UInt32 | — | ✅ Available (not shown in mockup) | — |
| `skipped_tests` | UInt32 | — | ✅ Available (not shown in mockup) | — |
| `workflow_run_url` | String | — | ✅ Chip click → opens GHA run | ✅ "Run" link |
| `artifact_url` | String | — | — | ✅ "Artifacts" link |
| `queue_time` | Float64 | — | ✅ Tooltip: "Queue: 12.3s" | — |
| `execution_time` | Float64 | — | ✅ Available (not shown in mockup) | — |
| `run_attempt` | UInt32 | — | ✅ Tooltip: "Attempt: 2" + dedup logic | — |
| `run_id` | String | — | ✅ Used in `buildMatrix()` grouping | — |
| `check_run_id` | String | — | Part of `dynamoKey` uniqueness | — |
| `workflow_name` | String | — | ✅ Available (not shown separately) | ✅ Available |
| `upstream_repo` | String | — | — | — (always `pytorch/pytorch`) |
| `delivery_id` | String | — | — | — (internal) |
| `dynamoKey` | String (PK) | — | — | — (ReplacingMergeTree dedup key) |

---

## Files Summary

| File | Role | Fields it handles |
|---|---|---|
| `pages/api/oot/results.ts` | API entry point — receives relay POST, orchestrates validate→extract→write | All fields (passthrough) |
| `lib/oot/ootUtils.ts` : `extractDynamoRecord()` | Flattens nested `{trusted, untrusted}` → flat `OotWorkflowJobRecord` | All fields — this is where the relay envelope is destructured |
| `lib/oot/ootUtils.ts` : `writeToDynamo()` | Writes flat record to DynamoDB via `UpdateItem` | All non-undefined fields — builds dynamic SET expression |
| `lib/oot/ootUtils.ts` : `validatePayloadSize()` | Enforces 2MB body limit | No specific fields — validates raw body size |
| `aws/lambda/clickhouse-replicator-dynamo/lambda_function.py` | Replicates DynamoDB → ClickHouse (1 line added) | All fields — transparent passthrough |
| `clickhouse_queries/oot_summary/query.sql` | Aggregation query for Summary page | `downstream_repo`, `downstream_repo_level`, `conclusion`, `duration_seconds`, `started_at`, `status` |
| `clickhouse_queries/oot_backend_dashboard/query.sql` | Per-repo detail query for Dashboard page | `pr_number`, `pytorch_head_sha`, `workflow_name`, `job_name`, `check_run_id`, `run_id`, `run_attempt`, `status`, `conclusion`, `started_at`, `completed_at`, `duration_seconds`, `total_tests`, `passed_tests`, `failed_tests`, `skipped_tests`, `workflow_run_url`, `artifact_url`, `queue_time`, `execution_time` |
| `clickhouse_queries/oot_pr_results/query.sql` | Per-PR detail query for PR page section | `downstream_repo`, `workflow_name`, `job_name`, `check_run_id`, `run_id`, `run_attempt`, `status`, `conclusion`, `duration_seconds`, `workflow_run_url`, `artifact_url`, `started_at`, `queue_time`, `execution_time` |
| `pages/oot/index.tsx` | Renders OOT Summary table | Reads: `repo`, `downstream_repo_level`, `pass_rate`, `successes`, `failures`, `total`, `avg_duration_s`, `last_run` |
| `pages/oot/[org]/[repo].tsx` | Renders per-backend job matrix | Reads: `pr_number`, `pytorch_head_sha`, `job_name`, `status`, `conclusion`, `duration_seconds`, `passed_tests`, `total_tests`, `queue_time`, `run_attempt`, `workflow_run_url` |
| `components/oot/OotPrSection.tsx` | Renders PR page OOT accordion | Reads: `downstream_repo`, `job_name`, `status`, `conclusion`, `duration_seconds`, `workflow_run_url`, `artifact_url` |
