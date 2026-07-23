# OOT HUD: Complete Data Flow — Function-to-Function, File-to-File

> This document traces every hop of data through the OOT HUD pipeline, mapping each step to the **exact file, function, line number, and field** in our implementation (test-infra fork PR) and RFC.

---

## Ownership Boundary

Our work covers two artifacts with different scopes:

| Artifact | Scope | What it covers |
|----------|-------|---------------|
| **RFC** (`OOT_HUD_RFC_V3.md`) | **Full pipeline end-to-end** | L1 dispatch → L2 relay (OIDC, rate limiting, `{trusted, untrusted}` split, security design, signed callback token proposal) → HUD API → DynamoDB → ClickHouse → Frontend pages. The RFC describes the complete architecture including components we don't implement ourselves. |
| **test-infra fork PR** (code) | **HUD API onward only** | Starts at `POST /api/oot/results` (Step 4 below). Everything before that — L1 dispatch, downstream CI, L2 relay — is implemented by other PRs (#7847 for L1, #7967 for L2). Our code receives the `{trusted, untrusted}` envelope from the relay and handles: validation, DynamoDB write, ClickHouse queries, and all three frontend pages. |

In the write path below, **Steps 1-3 are described in the RFC but NOT in our PR code**. **Steps 4-6 are both in the RFC and implemented in our PR**.

---

## Table of Contents

- [Overview Diagram](#overview-diagram)
- [Part 1: Write Path — How Data Gets Into the System](#part-1-write-path--how-data-gets-into-the-system)
  - [Step 1: PR Opened → L1 Dispatch](#step-1-pr-opened--l1-dispatch)
  - [Step 2: Downstream CI Runs Tests](#step-2-downstream-ci-runs-tests)
  - [Step 3: Downstream → L2 Relay (Result Lambda)](#step-3-downstream--l2-relay-result-lambda)
  - [Step 4: L2 Relay → HUD API](#step-4-l2-relay--hud-api)
  - [Step 5: HUD API → DynamoDB](#step-5-hud-api--dynamodb)
  - [Step 6: DynamoDB → ClickHouse (Automatic)](#step-6-dynamodb--clickhouse-automatic)
- [Part 2: Read Path — How Data Reaches the Frontend](#part-2-read-path--how-data-reaches-the-frontend)
  - [Page A: OOT Summary (`/oot`)](#page-a-oot-summary-oot)
  - [Page B: Per-Backend Dashboard (`/oot/[org]/[repo]`)](#page-b-per-backend-dashboard-ootorgrepo)
  - [Page C: PR View — OOT Section (`/pytorch/pytorch/pull/[N]`)](#page-c-pr-view--oot-section-pytorchpytorchpulln)
- [Part 3: Complete Field Lineage](#part-3-complete-field-lineage)
- [Part 4: File Inventory](#part-4-file-inventory)

---

## Overview Diagram

```
WRITE PATH (data in):
═══════════════════

  PR opened in pytorch/pytorch
        │
        ▼
  ┌─────────────────┐     ┌─────────────────────────┐
  │ webhook_handler  │────▶│  Downstream CI (OOT)    │
  │ (L1 dispatch)    │     │  runs tests, produces   │
  │                  │     │  artifacts, GHA OIDC     │
  └─────────────────┘     └────────┬────────────────┘
                                   │
                     Callback 1: in_progress
                     Callback 2: completed
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │ result_handler (L2 Relay) │
                    │ - Verify OIDC JWT         │
                    │ - Check allowlist (Redis)  │
                    │ - Rate limit (Redis)       │
                    │ - Split: trusted/untrusted │
                    └────────────┬───────────────┘
                                 │
                        POST /api/oot/results
                     Header: X-OOT-Relay-Token
                     Body: {trusted, untrusted}
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ HUD API (results.ts)      │
                    │ - Auth: X-OOT-Relay-Token │
                    │ - Size: validatePayloadSz │
                    │ - Extract: extractDynamo  │
                    │ - Write: writeToDynamo    │
                    └────────────┬───────────────┘
                                 │
                       DynamoDB UpdateItem
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ DynamoDB                  │
                    │ torchci-oot-workflow-job   │
                    └────────────┬───────────────┘
                                 │
                      DynamoDB Streams (auto)
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ clickhouse-replicator-    │
                    │ dynamo Lambda             │
                    │ - unmarshal DDB format    │
                    │ - INSERT INTO CH          │
                    └────────────┬───────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────┐
                    │ ClickHouse                │
                    │ default.oot_workflow_job   │
                    └──────────────────────────┘


READ PATH (data out):
═══════════════════

                    ┌──────────────────────────┐
                    │ ClickHouse                │
                    │ default.oot_workflow_job   │
                    └──────┬─────┬─────┬────────┘
                           │     │     │
              ┌────────────┘     │     └────────────┐
              ▼                  ▼                   ▼
    oot_summary/query.sql  oot_backend_dashboard/  oot_pr_results/
              │            query.sql                query.sql
              ▼                  ▼                   ▼
    /api/clickhouse/       /api/clickhouse/     /api/clickhouse/
    oot_summary            oot_backend_dashboard oot_pr_results
              │                  │                   │
              ▼                  ▼                   ▼
    pages/oot/index.tsx    pages/oot/[org]/     components/oot/
    (OOT Summary)          [repo].tsx            OotPrSection.tsx
                           (Per-Backend)         (PR page section)
```

---

## Part 1: Write Path — How Data Gets Into the System

### Step 1: PR Opened → L1 Dispatch

> **RFC coverage:** Described in `OOT_HUD_RFC_V3.md` → "Architecture Overview" diagrams, "Data Flow Summary Table" (phase: Trigger), "Status of Related Work" (L1 PRs).
> **PR coverage:** Not in our PR. L1 is upstream infrastructure.

| Aspect | Detail |
|--------|--------|
| **Trigger** | A PR is opened/updated in `pytorch/pytorch` |
| **Who handles it** | `webhook_handler` Lambda (L1) — implemented by @can-gaa-hou's PR [test-infra#7847](https://github.com/pytorch/test-infra/pull/7847) |
| **What it does** | Checks the PR against the `allowlist.yml`, then fires a `repository_dispatch` event to each authorized downstream repo |
| **What it sends** | `client_payload` containing: PR number, head SHA, upstream repo, callback token (JWT signed by L1) |
| **Our RFC describes** | The callback token minted at this step (see "Our Proposal: Signed One-Shot Callback Token"), which provides dispatch provenance and replay prevention |
| **Our PR implements** | Nothing at this step |

### Step 2: Downstream CI Runs Tests

> **RFC coverage:** Described in `OOT_HUD_RFC_V3.md` → "Artifact Storage (Downstream-Owned)", "Status Callbacks (Two-Callback Model)", detailed sequence diagram.
> **PR coverage:** Not in our PR. Downstream CI is external.

| Aspect | Detail |
|--------|--------|
| **Trigger** | `repository_dispatch` event arrives at downstream repo |
| **Who handles it** | Downstream's own GHA workflow (e.g., `intel/torch-xpu-ops/.github/workflows/ci.yml`) |
| **What happens** | Tests run, artifacts are uploaded to downstream-owned storage (S3, GCS, etc.) |
| **OIDC token** | Downstream workflow calls `actions/github-script` with `core.getIDToken()` to get a signed JWT from GitHub's OIDC provider |
| **Two-callback model** | Callback 1 (`in_progress`) when first job starts; Callback 2 (`completed`) when last job finishes — described in RFC "Status Callbacks" |
| **Our RFC describes** | The downstream artifact ownership model, the two-callback sequence, sample payload structures for both in-progress and completed callbacks |
| **Our PR implements** | Nothing at this step |

### Step 3: Downstream → L2 Relay (Result Lambda)

> **RFC coverage:** This step is fully described in `OOT_HUD_RFC_V3.md` — sections "Hop 1: Downstream to Result Lambda", "Hop 2: Result Lambda to HUD API", "Authentication Flow", "Security Design" (OIDC, allowlist, rate limiting, `{trusted, untrusted}` split, signed callback token proposal), and "DB Protection Layer".
>
> **PR coverage:** This step is NOT in our test-infra fork PR. The relay is implemented by [test-infra#7967](https://github.com/pytorch/test-infra/pull/7967). Our RFC documents how the relay works and what it outputs because our HUD API depends on its exact output format.

| Aspect | Detail |
|--------|--------|
| **Trigger** | Downstream workflow POSTs to the relay endpoint |
| **Who handles it** | `result_handler` Lambda (L2 relay) — implemented in [test-infra#7967](https://github.com/pytorch/test-infra/pull/7967) |
| **Auth** | OIDC token verified against GitHub JWKS → extracts `repository` claim as `verified_repo` |
| **What it does** | 1) Verify OIDC signature (GitHub JWKS), 2) Check `repository` claim against Redis-cached allowlist (TTL 20min), 3) Verify repo is L2+, 4) Per-repo rate limit (Redis, 10 req/min), 5) Construct `{trusted, untrusted}` envelope, 6) Forward to HUD API with `X-OOT-Relay-Token` header |
| **RFC sections** | "Hop 1" (OIDC + allowlist + rate limit), "Hop 2" (forwarding to HUD API), "Authentication Flow" (all 4 hops), "Security Design" (OIDC, L2 PR measures, signed callback token proposal), "DB Protection Layer" (rate limiting + payload caps) |
| **Output payload** | The relay constructs a **two-namespace** JSON envelope: |

```json
{
  "trusted": {
    "verified_repo": "intel/torch-xpu-ops",
    "downstream_repo_level": "L2",
    "ci_metrics": {
      "queue_time": 12.3,
      "execution_time": null
    }
  },
  "untrusted": {
    "callback_payload": {
      "event_type": "ci_result",
      "delivery_id": "abc-123-def",
      "payload": {
        "pull_request": { "number": 183512, "head": { "sha": "a1b2c3d" } },
        "repository": { "full_name": "pytorch/pytorch" }
      },
      "workflow": {
        "schema_version": "1",
        "status": "in_progress",
        "name": "xpu-ci",
        "url": "https://github.com/intel/torch-xpu-ops/actions/runs/12345",
        "job_name": "test-float32",
        "check_run_id": "67890",
        "run_id": "12345",
        "run_attempt": 1,
        "started_at": "2026-05-13T10:00:00Z"
      }
    }
  }
}
```

| **Key trust boundary** | `trusted.verified_repo` comes from OIDC (cryptographic). Everything in `untrusted` is self-reported by downstream. |
| **Our RFC describes** | The full relay behavior: OIDC verification, allowlist check, rate limiting, `{trusted, untrusted}` split, error asymmetry (4xx propagated, 5xx swallowed), CI timing metrics, and the signed callback token proposal for L3/L4 readiness. See RFC sections: "Security Design" → "OIDC Authentication", "L2 PR Security Measures", "Our Proposal: Signed One-Shot Callback Token". |
| **Our PR implements** | Nothing at this step. The relay is a separate PR (#7967). Our HUD API (Step 4) expects the exact envelope format shown above as input. |

### Step 4: L2 Relay → HUD API

**This is where OUR PR code begins.** Everything from here through Step 6 is both described in the RFC and implemented in our test-infra fork PR.

| Aspect | Detail |
|--------|--------|
| **Entry point** | `POST /api/oot/results` |
| **File** | `torchci/pages/api/oot/results.ts` |
| **Auth mechanism** | `X-OOT-Relay-Token` header checked against `process.env.OOT_RELAY_TOKEN` |

**Function-by-function walkthrough of `results.ts`:**

```
results.ts:handler(req, res)                         [line 17]
│
├── 1. Method check: only POST allowed                [line 21-23]
│
├── 2. Auth check: X-OOT-Relay-Token header           [line 27-30]
│       reads: req.headers["x-oot-relay-token"]
│       compares: process.env.OOT_RELAY_TOKEN
│       fails: → 401 Unauthorized
│
├── 3. Payload size check                              [line 33-35]
│       calls: validatePayloadSize(rawBody)            → ootUtils.ts:83
│       checks: Buffer.byteLength(bodyString) > 2MB
│       fails: → 413 "Payload exceeds 2MB limit"
│
├── 4. Extract DynamoDB record                         [line 39-40]
│       calls: extractDynamoRecord(body)               → ootUtils.ts:91
│       input:  RelayPayload {trusted, untrusted}
│       output: OotWorkflowJobRecord (flat record)
│       (detailed breakdown below)
│
├── 5. Write to DynamoDB                               [line 41]
│       calls: writeToDynamo(record)                   → ootUtils.ts:162
│       (detailed breakdown below)
│
└── 6. Return success                                  [line 43-47]
        returns: { ok: true, status, dynamoKey }
```

### Step 5: HUD API → DynamoDB

> **RFC coverage:** `OOT_HUD_RFC_V3.md` → "Hop 3: HUD API to DynamoDB", "DynamoDB Table" (full schema), "Status Callbacks (Two-Callback Model)" (why UpdateItem).
> **PR coverage:** `torchci/lib/oot/ootUtils.ts` — `extractDynamoRecord()` and `writeToDynamo()`.

This step has two critical functions in `torchci/lib/oot/ootUtils.ts`:

#### Function A: `extractDynamoRecord()` — Lines 91-158

**Purpose:** Flatten the nested `{trusted, untrusted}` relay envelope into a flat `OotWorkflowJobRecord` suitable for DynamoDB.

```
extractDynamoRecord(payload: RelayPayload)            [line 91]
│
├── Destructure payload                                [line 94]
│     const { trusted, untrusted } = payload
│
├── Navigate to nested objects                         [line 95-99]
│     cb = untrusted.callback_payload     (RelayCallbackPayload)
│     wf = cb.workflow                    (RelayWorkflow)
│     pr = cb.payload?.pull_request       (PR info)
│     upstreamRepo = cb.payload?.repository?.full_name
│
├── Build composite key                                [line 101-104]
│     jobName     = wf.job_name ?? "default"
│     checkRunId  = wf.check_run_id ?? "unknown"
│     runAttempt  = wf.run_attempt ?? 1
│     dynamoKey   = "{verified_repo}/{delivery_id}/{workflow_name}/{jobName}/{checkRunId}"
│
├── Build base record (always set)                     [line 106-120]
│     record = {
│       dynamoKey,
│       status:           wf.status,                   ← from untrusted.workflow
│       downstream_repo:  trusted.verified_repo,       ← from OIDC (trusted!)
│       upstream_repo:    upstreamRepo,                ← from untrusted
│       pr_number:        pr?.number ?? 0,             ← from untrusted
│       pytorch_head_sha: pr?.head?.sha ?? "",         ← from untrusted
│       delivery_id:      cb.delivery_id,              ← from untrusted
│       workflow_run_url: wf.url ?? "",                ← from untrusted
│       workflow_name:    wf.name,                     ← from untrusted
│       job_name:         jobName,                     ← from untrusted
│       check_run_id:     checkRunId,                  ← from untrusted
│       run_id:           wf.run_id ?? "",             ← from untrusted
│       run_attempt:      runAttempt,                  ← from untrusted
│     }
│
├── Conditional: downstream_repo_level                 [line 122-124]
│     if (trusted.downstream_repo_level)
│       record.downstream_repo_level = trusted.downstream_repo_level
│     Source: relay-determined from allowlist YAML (trusted!)
│
├── Conditional: timing metrics                        [line 130-135]
│     if (trusted.ci_metrics?.queue_time != null)
│       record.queue_time = trusted.ci_metrics.queue_time
│     if (trusted.ci_metrics?.execution_time != null)
│       record.execution_time = trusted.ci_metrics.execution_time
│     Source: relay-measured timestamps (trusted!)
│     Why conditional: in_progress sets queue_time, completed sets execution_time
│
├── Conditional: timestamps                            [line 138-140]
│     if (wf.started_at) record.started_at = wf.started_at
│
├── Conditional: completed-only fields                 [line 142-155]
│     if (wf.status === "completed") {
│       record.conclusion   = wf.conclusion           ← "success"/"failure"
│       record.completed_at = wf.completed_at
│       if (wf.test_results) {
│         record.total_tests   = tr.total
│         record.passed_tests  = tr.passed
│         record.failed_tests  = tr.failed
│         record.skipped_tests = tr.skipped
│       }
│     }
│
└── Return: OotWorkflowJobRecord                       [line 157]
```

#### Function B: `writeToDynamo()` — Lines 162-190

**Purpose:** Write the flat record to DynamoDB using `UpdateItem` (not `PutItem`) to prevent field clobbering between callbacks.

```
writeToDynamo(record: OotWorkflowJobRecord)            [line 162]
│
├── Get DynamoDB client                                 [line 165]
│     client = getDynamoClient()
│     Source: lib/dynamo (shared HUD utility)
│
├── Build dynamic SET expression                        [line 170-181]
│     For each field in record:
│       Skip "dynamoKey" (it's the key, not a value)
│       Skip undefined values (prevents clobbering!)
│       Build: "#n_status = :v_status, #n_conclusion = :v_conclusion, ..."
│
│     WHY UpdateItem not PutItem:
│     - Callback 1 (in_progress) sets: status, queue_time, started_at
│     - Callback 2 (completed)   sets: status, conclusion, execution_time, test counts
│     - PutItem would OVERWRITE the entire item, erasing queue_time
│     - UpdateItem only touches the fields present in THIS callback
│
└── Execute DynamoDB UpdateItem                         [line 183-189]
      client.update({
        TableName: "torchci-oot-workflow-job",
        Key: { dynamoKey: record.dynamoKey },
        UpdateExpression: "SET #n_status = :v_status, #n_downstream_repo = :v_downstream_repo, ...",
        ExpressionAttributeValues: { ":v_status": "in_progress", ... },
        ExpressionAttributeNames: { "#n_status": "status", ... },
      })
```

**After this call, DynamoDB has one row per job:**

| dynamoKey | status | downstream_repo | pr_number | conclusion | queue_time | ... |
|-----------|--------|-----------------|-----------|------------|------------|-----|
| `intel/torch-xpu-ops/abc-123/xpu-ci/test-float32/67890` | `in_progress` | `intel/torch-xpu-ops` | 183512 | *(null)* | 12.3 | ... |

When callback 2 arrives, `UpdateItem` sets `status=completed`, `conclusion=success`, `execution_time=1092.5` — but leaves `queue_time=12.3` untouched.

### Step 6: DynamoDB → ClickHouse (Automatic)

> **RFC coverage:** `OOT_HUD_RFC_V3.md` → "Hop 4: DynamoDB to ClickHouse (Automatic)", "ClickHouse Table" (schema design), "Implementation Plan" Phase 1 item 3.
> **PR coverage:** Single line added to `lambda_function.py` (table mapping). The replicator Lambda itself is existing infrastructure.

| Aspect | Detail |
|--------|--------|
| **Trigger** | DynamoDB Streams (enabled with `NEW_AND_OLD_IMAGES`) |
| **Latency** | ~2-5 seconds (event-driven, not polled) |
| **File** | `aws/lambda/clickhouse-replicator-dynamo/lambda_function.py` |

**Function chain:**

```
lambda_handler(event, context)                          [line 56]
│
└── handle_event(event, dry_run=False)                  [line 61]
    │
    ├── For each record in event["Records"]:            [line 64]
    │   │
    │   ├── If INSERT or MODIFY:                        [line 67-72]
    │   │     get_doc_for_upsert(record)
    │   │     │
    │   │     ├── extract_dynamodb_table(record)        [line 88]
    │   │     │     Parses ARN → "torchci-oot-workflow-job"
    │   │     │     Looks up SUPPORTED_TABLES mapping:
    │   │     │       "torchci-oot-workflow-job" → "default.oot_workflow_job"   [line 36]
    │   │     │
    │   │     ├── unmarshal(record.dynamodb.NewImage)    [line 124]
    │   │     │     Converts DynamoDB wire format:
    │   │     │       {"S": "in_progress"} → "in_progress"
    │   │     │       {"N": "183512"} → 183512
    │   │     │       {"M": {...}} → {...} (recursive)
    │   │     │
    │   │     └── Returns (table, id, doc)
    │   │
    │   └── Collects into docs_to_upsert[table]
    │
    └── upsert_documents(table, documents, dry_run)     [line 187]
          │
          ├── Serialize documents as JSON lines          [line 197-198]
          │     body = json.dumps(doc1) + "\n" + json.dumps(doc2) + "\n"
          │
          └── Execute ClickHouse INSERT                  [line 200-205]
                query = "INSERT INTO default.oot_workflow_job
                         SETTINGS async_insert=1, wait_for_async_insert=1
                         FORMAT JSONEachRow {body}"
                get_clickhouse_client().query(query)
```

**Key detail:** The `SUPPORTED_TABLES` mapping (line 19-37) is the ONLY change needed in this file:

```python
SUPPORTED_TABLES = {
    "torchci-workflow-job": "default.workflow_job",
    "torchci-workflow-run": "default.workflow_run",
    # ... existing tables ...
    "torchci-oot-workflow-job": "default.oot_workflow_job",  # ← OUR ADDITION (line 36)
}
```

**After this step, ClickHouse has the row.** The table uses `SharedReplacingMergeTree`, so when the same `dynamoKey` appears again (callback 2), ClickHouse keeps the latest version.

---

## Part 2: Read Path — How Data Reaches the Frontend

> **RFC coverage:** `OOT_HUD_RFC_V3.md` → "Read Path: How HUD Displays Results", "HUD Page Designs" (all 3 pages with sample SQL queries and layout descriptions).
> **PR coverage:** All frontend pages and ClickHouse queries are fully implemented in the test-infra fork PR.

All three pages follow the same pattern:

```
React component (useSWR)
    → GET /api/clickhouse/{queryName}?parameters={...}
        → Next.js generic handler reads clickhouse_queries/{queryName}/query.sql
            → Substitutes parameters from params.json
                → Sends SQL to ClickHouse
                    → Returns JSON rows
                        → React renders
```

### Page A: OOT Summary (`/oot`)

**Purpose:** Cross-repo health overview. Shows all downstream backends sorted by pass rate.

```
User visits /oot
│
└── pages/oot/index.tsx                                 [line 141]
    │  OotSummaryPage() renders:
    │    - Title: "Out-of-Tree CI Summary"
    │    - Time range selector (1d / 7d / 30d)
    │    - <OotSummaryTable days={7} />
    │
    └── OotSummaryTable({ days })                       [line 46]
        │
        ├── Build URL:                                  [line 47-49]
        │     /api/clickhouse/oot_summary?parameters={"days":"7"}
        │
        ├── useSWR<OotSummaryRow[]>(url, fetcher)       [line 50-52]
        │     refreshInterval: 60_000 (1 minute)
        │
        │   ── Next.js handles /api/clickhouse/[query] ──
        │   │
        │   ├── Reads: clickhouse_queries/oot_summary/query.sql
        │   │     SELECT
        │   │       downstream_repo AS repo,
        │   │       anyLast(downstream_repo_level) AS downstream_repo_level,
        │   │       countIf(conclusion = 'success') AS successes,
        │   │       countIf(conclusion = 'failure') AS failures,
        │   │       count() AS total,
        │   │       if(total > 0, successes / total, 0) AS pass_rate,
        │   │       avg(duration_seconds) AS avg_duration_s,
        │   │       max(started_at) AS last_run
        │   │     FROM default.oot_workflow_job FINAL
        │   │     WHERE started_at > now() - INTERVAL 7 DAY
        │   │       AND status = 'completed'
        │   │     GROUP BY repo
        │   │     ORDER BY pass_rate ASC
        │   │
        │   ├── Reads: clickhouse_queries/oot_summary/params.json
        │   │     { "params": { "days": "UInt64" } }
        │   │
        │   └── Returns JSON array of OotSummaryRow
        │
        └── Renders table                               [line 72-138]
            │
            ├── For each row:                           [line 104]
            │     const [org, repo] = row.repo.split("/")
            │
            ├── Backend Repository                      [line 108-111]
            │     <NextLink href="/oot/{org}/{repo}">
            │       {row.repo}  ← downstream_repo from ClickHouse
            │     </NextLink>
            │
            ├── Level                                   [line 113-118]
            │     <Chip label={row.downstream_repo_level || "–"} />
            │
            ├── Pass Rate                               [line 120-121]
            │     <PassRateChip rate={row.pass_rate} />
            │     rate >= 0.95 → green "success"        [line 41]
            │     rate >= 0.8  → orange "warning"       [line 42]
            │     rate < 0.8   → red "error"            [line 43]
            │
            ├── Success / Failures / Total              [line 123-125]
            │     Direct numeric display
            │
            ├── Avg Duration                            [line 126-128]
            │     durationDisplay(Math.round(row.avg_duration_s))
            │     Uses: components/common/TimeUtils.ts
            │
            └── Last Run                                [line 129-131]
                  new Date(row.last_run).toLocaleString()
```

### Page B: Per-Backend Dashboard (`/oot/[org]/[repo]`)

**Purpose:** Job-level matrix for a single downstream repo. Rows = PyTorch PRs, columns = job names.

```
User clicks "intel/torch-xpu-ops" in summary → /oot/intel/torch-xpu-ops
│
└── pages/oot/[org]/[repo].tsx                          [line 259]
    │  OotBackendPage() renders:
    │    - Title: "intel/torch-xpu-ops"
    │    - Back link to /oot
    │    - Time range selector
    │    - <OotMatrix repoFullName="intel/torch-xpu-ops" days={7} />
    │
    └── OotMatrix({ repoFullName, days })               [line 169]
        │
        ├── Build URL:                                  [line 176-178]
        │     /api/clickhouse/oot_backend_dashboard?parameters={"repo":"intel/torch-xpu-ops","days":"7"}
        │
        ├── useSWR<OotJobRow[]>(url, fetcher)           [line 179-181]
        │     refreshInterval: 60_000
        │
        │   ── ClickHouse query ──
        │   │
        │   ├── Reads: clickhouse_queries/oot_backend_dashboard/query.sql
        │   │     SELECT pr_number, pytorch_head_sha, workflow_name, job_name,
        │   │            check_run_id, run_id, run_attempt, status, conclusion,
        │   │            started_at, completed_at, duration_seconds,
        │   │            total_tests, passed_tests, failed_tests, skipped_tests,
        │   │            workflow_run_url, artifact_url, queue_time, execution_time
        │   │     FROM default.oot_workflow_job FINAL
        │   │     WHERE downstream_repo = 'intel/torch-xpu-ops'
        │   │       AND started_at > now() - INTERVAL 7 DAY
        │   │     ORDER BY started_at DESC
        │   │     LIMIT 500
        │   │
        │   └── Returns JSON array of OotJobRow
        │
        ├── buildMatrix(data)                           [line 116]
        │     Purpose: Transform flat job rows into a PR × job matrix
        │     │
        │     ├── Collect unique job names               [line 120-126]
        │     │     jobNamesSet.add(job.job_name)
        │     │
        │     ├── Group by PR number                    [line 127-141]
        │     │     prMap.get(job.pr_number) → MatrixRow
        │     │     Keep latest attempt per job_name
        │     │     (highest run_attempt wins)
        │     │
        │     └── Return { jobNames: string[], rows: MatrixRow[] }
        │           rows sorted by PR number (newest first)
        │
        ├── <HealthSummary data={data} />               [line 150]
        │     completed = data.filter(j => j.status === "completed")
        │     rate = success / total
        │     Shows: <Chip "Pass rate: 78.3%"> "47/60 jobs passed"
        │
        └── Render matrix table                         [line 207-254]
            │
            ├── Header row: PR | SHA | {job_name_1} | {job_name_2} | ...
            │     Job names from buildMatrix().jobNames
            │
            └── For each MatrixRow:
                ├── PR: <Link>#{prNumber}</Link>        [line 227-235]
                ├── SHA: {sha.slice(0,7)}               [line 237-240]
                └── For each job_name:                  [line 242-248]
                      job = row.jobs.get(name)
                      job ? <JobChip job={job} /> : "–"

                      JobChip({ job })                  [line 76-108]
                      │
                      ├── color = conclusionColor(status, conclusion)
                      │     in_progress → "info" (blue)
                      │     success     → "success" (green)
                      │     failure     → "error" (red)
                      │     cancelled   → "warning" (yellow)
                      │
                      ├── label = conclusionLabel(status, conclusion)
                      │     in_progress → "running"
                      │     else        → conclusion
                      │
                      ├── Tooltip shows:
                      │     "Job: test-float32"
                      │     "Attempt: 2" (if >1)
                      │     "Duration: 18m 32s"
                      │     "Tests: 1240/1240 passed"
                      │     "Queue: 12.3s"
                      │
                      └── Chip links to job.workflow_run_url (opens GHA run)
```

### Page C: PR View — OOT Section (`/pytorch/pytorch/pull/[N]`)

**Purpose:** Collapsible accordion showing all OOT backend results for a specific PR, embedded below the existing in-tree CI results.

```
User visits /pytorch/pytorch/pull/183512
│
└── pages/[repoOwner]/[repoName]/pull/[prNumber].tsx   (existing page)
    │  Existing PR page renders all in-tree CI results
    │  At the bottom, conditionally renders:
    │
    └── <OotPrSection prNumber={183512} />
        │
        └── components/oot/OotPrSection.tsx             [line 62]
            │
            ├── Build URL:                              [line 63-65]
            │     /api/clickhouse/oot_pr_results?parameters={"pr":"183512"}
            │
            ├── useSWR<OotPrResult[]>(url, fetcher)     [line 66-68]
            │     refreshInterval: 60_000
            │
            │   ── ClickHouse query ──
            │   │
            │   ├── Reads: clickhouse_queries/oot_pr_results/query.sql
            │   │     SELECT downstream_repo, workflow_name, job_name,
            │   │            check_run_id, run_id, run_attempt, status,
            │   │            conclusion, duration_seconds, workflow_run_url,
            │   │            artifact_url, started_at, queue_time, execution_time
            │   │     FROM default.oot_workflow_job FINAL
            │   │     WHERE pr_number = 183512
            │   │     ORDER BY downstream_repo, started_at DESC
            │   │
            │   └── Returns JSON array of OotPrResult
            │
            ├── If no data or error → return null       [line 70]
            │     (OOT section not rendered at all)
            │
            ├── Compute summary stats                   [line 72-89]
            │     successCount = filter(completed + success).length
            │     totalCompleted = filter(completed).length
            │     inProgress = filter(in_progress).length
            │     summaryText = "3/5 passed, 1 running"
            │
            └── Render Accordion                        [line 91-173]
                │
                ├── AccordionSummary:
                │     "Out-of-Tree Backends (3/5 passed, 1 running)"
                │
                └── AccordionDetails → Table:
                    Columns: Backend | Job | Status | Duration | Links

                    For each row:                       [line 126-167]
                    ├── Backend: row.downstream_repo
                    │     Shows: "intel/torch-xpu-ops"
                    │     NOTE: Multiple different companies appear here
                    │     because this is a cross-backend view of one PR
                    │
                    ├── Job: row.job_name
                    │     Shows: "test-float32"
                    │
                    ├── Status: <Chip label="success" color="success" />
                    │     Uses: conclusionColor() and conclusionLabel()
                    │
                    ├── Duration: durationDisplay(row.duration_seconds)
                    │     Or "–" if null (still running)
                    │
                    └── Links:
                          "Run"       → row.workflow_run_url (GHA run page)
                          "Artifacts" → row.artifact_url (downstream storage)
```

---

## Part 3: Complete Field Lineage

This table traces each field from its origin all the way to the frontend.

| Field | Origin | Relay namespace | `extractDynamoRecord()` line | DynamoDB column | ClickHouse column | Used in query | Frontend component |
|-------|--------|-----------------|-----|----------|--------|------|---------|
| `downstream_repo` | OIDC `repository` claim | `trusted.verified_repo` | 109 | `downstream_repo` | `downstream_repo` | All 3 queries (filter or select) | Summary: repo name, link. Dashboard: header. PR: "Backend" column |
| `downstream_repo_level` | Relay allowlist YAML | `trusted.downstream_repo_level` | 123 | `downstream_repo_level` | `downstream_repo_level` | `oot_summary` (anyLast) | Summary: Level chip |
| `status` | Downstream GHA | `untrusted.workflow.status` | 108 | `status` | `status` | All 3 queries (filter `WHERE status='completed'` or select) | PR: `conclusionLabel()`, Dashboard: `conclusionLabel()` |
| `conclusion` | Downstream GHA | `untrusted.workflow.conclusion` | 143 | `conclusion` | `conclusion` | `oot_summary` (countIf), Dashboard (select), PR (select) | Summary: pass_rate. Dashboard: chip color. PR: chip color |
| `pr_number` | Downstream body | `untrusted.callback_payload.payload.pull_request.number` | 111 | `pr_number` | `pr_number` | `oot_pr_results` (WHERE), `oot_backend_dashboard` (SELECT) | Dashboard: PR link. PR: query filter |
| `pytorch_head_sha` | Downstream body | `untrusted.callback_payload.payload.pull_request.head.sha` | 112 | `pytorch_head_sha` | `pytorch_head_sha` | `oot_backend_dashboard` (SELECT) | Dashboard: SHA column |
| `delivery_id` | L1 dispatch | `untrusted.callback_payload.delivery_id` | 113 | `delivery_id` | `delivery_id` | Part of dynamoKey | Not directly displayed |
| `workflow_name` | Downstream body | `untrusted.workflow.name` | 115 | `workflow_name` | `workflow_name` | `oot_backend_dashboard`, `oot_pr_results` (SELECT) | Dashboard/PR: display |
| `job_name` | Downstream body | `untrusted.workflow.job_name` | 116 | `job_name` | `job_name` | `oot_backend_dashboard`, `oot_pr_results` (SELECT) | Dashboard: column header. PR: "Job" column |
| `check_run_id` | Downstream GHA | `untrusted.workflow.check_run_id` | 117 | `check_run_id` | `check_run_id` | Part of dynamoKey, SELECT | Part of uniqueness key |
| `run_id` | Downstream GHA | `untrusted.workflow.run_id` | 118 | `run_id` | `run_id` | `oot_backend_dashboard`, `oot_pr_results` (SELECT) | Dashboard: group key for dedup |
| `run_attempt` | Downstream GHA | `untrusted.workflow.run_attempt` | 119 | `run_attempt` | `run_attempt` | `oot_backend_dashboard` (SELECT) | Dashboard: "Attempt: N" tooltip, latest-attempt logic |
| `workflow_run_url` | Downstream body | `untrusted.workflow.url` | 114 | `workflow_run_url` | `workflow_run_url` | `oot_backend_dashboard`, `oot_pr_results` (SELECT) | Dashboard: chip link. PR: "Run" link |
| `queue_time` | Relay Redis timestamps | `trusted.ci_metrics.queue_time` | 131 | `queue_time` | `queue_time` | `oot_backend_dashboard`, `oot_pr_results` (SELECT) | Dashboard: "Queue: 12.3s" tooltip |
| `execution_time` | Relay Redis timestamps | `trusted.ci_metrics.execution_time` | 134 | `execution_time` | `execution_time` | `oot_backend_dashboard`, `oot_pr_results` (SELECT) | Available for display |
| `started_at` | Downstream body | `untrusted.workflow.started_at` | 139 | `started_at` | `started_at` | All 3 queries (WHERE time filter, ORDER BY, max()) | Summary: "Last Run" |
| `completed_at` | Downstream body | `untrusted.workflow.completed_at` | 145 | `completed_at` | `completed_at` | `oot_backend_dashboard` (SELECT) | Available for display |
| `total_tests` | Downstream body | `untrusted.workflow.test_results.total` | 150 | `total_tests` | `total_tests` | `oot_backend_dashboard` (SELECT) | Dashboard: "Tests: N/N" tooltip |
| `passed_tests` | Downstream body | `untrusted.workflow.test_results.passed` | 151 | `passed_tests` | `passed_tests` | `oot_backend_dashboard` (SELECT) | Dashboard: tooltip |
| `failed_tests` | Downstream body | `untrusted.workflow.test_results.failed` | 152 | `failed_tests` | `failed_tests` | `oot_backend_dashboard` (SELECT) | Dashboard: tooltip |
| `skipped_tests` | Downstream body | `untrusted.workflow.test_results.skipped` | 153 | `skipped_tests` | `skipped_tests` | `oot_backend_dashboard` (SELECT) | Dashboard: tooltip |
| `artifact_url` | Downstream body | `untrusted.workflow.artifact_url` (or body-level) | — (not yet extracted) | `artifact_url` | `artifact_url` | `oot_backend_dashboard`, `oot_pr_results` (SELECT) | PR: "Artifacts" link |
| `upstream_repo` | Downstream body | `untrusted.callback_payload.payload.repository.full_name` | 110 | `upstream_repo` | `upstream_repo` | — | Not directly displayed (always `pytorch/pytorch`) |
| `dynamoKey` | Computed | Computed from: `verified_repo/delivery_id/workflow_name/job_name/check_run_id` | 104 | Hash key (PK) | `dynamoKey` | ReplacingMergeTree dedup | Not displayed |

---

## Part 4: File Inventory

### Our Code (test-infra fork PR)

| # | File | Role | Key functions/exports |
|---|------|------|----------------------|
| 1 | `torchci/pages/api/oot/results.ts` | API route — entry point for relay callbacks | `handler()` — auth, validate, extract, write |
| 2 | `torchci/lib/oot/ootUtils.ts` | Shared library — types, validation, extraction, DB write | `RelayPayload`, `RelayTrusted`, `RelayUntrusted`, `RelayCallbackPayload`, `RelayWorkflow`, `OotWorkflowJobRecord`, `validatePayloadSize()`, `extractDynamoRecord()`, `writeToDynamo()`, `ApiError` |
| 3 | `torchci/clickhouse_queries/oot_summary/query.sql` | ClickHouse query — aggregated summary per repo | Groups by `downstream_repo`, computes `pass_rate`, `avg_duration_s`, `last_run` |
| 4 | `torchci/clickhouse_queries/oot_summary/params.json` | Parameter definition | `{ days: UInt64 }` |
| 5 | `torchci/clickhouse_queries/oot_backend_dashboard/query.sql` | ClickHouse query — all jobs for one repo | Filters by `downstream_repo`, returns per-job rows |
| 6 | `torchci/clickhouse_queries/oot_backend_dashboard/params.json` | Parameter definition | `{ repo: String, days: UInt64 }` |
| 7 | `torchci/clickhouse_queries/oot_pr_results/query.sql` | ClickHouse query — all OOT jobs for one PR | Filters by `pr_number`, returns per-job rows across all backends |
| 8 | `torchci/clickhouse_queries/oot_pr_results/params.json` | Parameter definition | `{ pr: UInt64 }` |
| 9 | `torchci/pages/oot/index.tsx` | Frontend — OOT Summary page | `OotSummaryPage()`, `OotSummaryTable()`, `PassRateChip()` |
| 10 | `torchci/pages/oot/[org]/[repo].tsx` | Frontend — Per-backend dashboard | `OotBackendPage()`, `OotMatrix()`, `buildMatrix()`, `HealthSummary()`, `JobChip()`, `conclusionColor()`, `conclusionLabel()` |
| 11 | `torchci/components/oot/OotPrSection.tsx` | Frontend — PR page OOT section | `OotPrSection()`, `conclusionColor()`, `conclusionLabel()` |

### Infrastructure (1-line change each)

| # | File | Change |
|---|------|--------|
| 12 | `aws/lambda/clickhouse-replicator-dynamo/lambda_function.py` line 36 | Added: `"torchci-oot-workflow-job": "default.oot_workflow_job"` |

### Existing infra we reuse (NOT our code, no changes needed)

| # | File/Service | What it does for us |
|---|-------------|---------------------|
| — | DynamoDB table `torchci-oot-workflow-job` | Created by @ZainRizvi's Terraform PR |
| — | DynamoDB Streams | Automatically captures every write |
| — | `clickhouse-replicator-dynamo` Lambda | Replicates DynamoDB → ClickHouse (we just added mapping) |
| — | ClickHouse `default.oot_workflow_job` table | SharedReplacingMergeTree (schema TBD, based on `workflow_job`) |
| — | `/api/clickhouse/[query]` generic handler | Reads our SQL files, substitutes params, sends to ClickHouse |
| — | `lib/dynamo.ts` → `getDynamoClient()` | Shared DynamoDB client |
| — | `lib/GeneralUtils.ts` → `fetcher` | SWR fetcher for API calls |
| — | `components/common/TimeUtils.ts` → `durationDisplay()` | Formats seconds into "18m 32s" |

### RFC Document

| # | File | What it covers |
|---|------|---------------|
| 13 | `OOT_HUD_RFC_V3.md` | Full architecture: write path (4 hops), read path (3 pages), storage design (DynamoDB + ClickHouse schemas), DB protection (rate limits, payload caps), authentication (OIDC → relay token → IAM), security (signed callback token proposal), comparison with in-tree pipeline |

### RFC ↔ PR Cross-Reference

This table maps each RFC section to whether it's also implemented in the test-infra fork PR:

| RFC Section | Covered in RFC | Implemented in our PR | Implemented by others |
|-------------|:-:|:-:|:-:|
| Architecture Overview (diagrams) | ✅ | — | — |
| Hop 1: Downstream → Result Lambda (OIDC, allowlist, rate limit) | ✅ | — | PR #7967 (L2 relay) |
| Hop 2: Result Lambda → HUD API (forwarding, auth header) | ✅ | — | PR #7967 (L2 relay) |
| Hop 3: HUD API → DynamoDB (`results.ts`, `ootUtils.ts`) | ✅ | ✅ `results.ts`, `ootUtils.ts` | — |
| Hop 4: DynamoDB → ClickHouse (replicator mapping) | ✅ | ✅ 1 line in `lambda_function.py` | Existing replicator infra |
| DynamoDB Table Schema | ✅ | ✅ Types in `ootUtils.ts` | Terraform by @ZainRizvi |
| ClickHouse Table Schema | ✅ | Pending (schema.sql not yet created) | — |
| Read Path: OOT Summary page | ✅ | ✅ `pages/oot/index.tsx` + `oot_summary/query.sql` | — |
| Read Path: Per-Backend Dashboard | ✅ | ✅ `pages/oot/[org]/[repo].tsx` + `oot_backend_dashboard/query.sql` | — |
| Read Path: PR View Integration | ✅ | ✅ `components/oot/OotPrSection.tsx` + `oot_pr_results/query.sql` | — |
| DB Protection (rate limits, payload caps) | ✅ | ✅ Payload cap in `ootUtils.ts` | Rate limit at relay (PR #7967) |
| Authentication Flow (all 4 hops) | ✅ | ✅ Hop 3 auth in `results.ts` | Hops 1-2 by relay, Hop 4 by IAM |
| Security Design (OIDC, callback token) | ✅ | — | OIDC by relay; callback token is a proposal |
| Two-Callback Model | ✅ | ✅ `UpdateItem` in `writeToDynamo()` | Relay sends both callbacks |
| Artifact Storage (downstream-owned) | ✅ | ✅ `artifact_url` field + UI links | Downstream manages storage |
| Comparison: In-Tree vs OOT | ✅ | — | Reference only |
| Implementation Plan | ✅ | Partially (Phases 1+3 done) | Phases 2+4 pending |
