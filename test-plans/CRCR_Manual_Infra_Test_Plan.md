# CRCR Pipeline — Manual & Infrastructure Test Plan

Tests that **cannot** be automated via GitHub Actions workflows in `crcr-test` because they require AWS console access, direct API calls, infrastructure changes, or manual browser verification.

**Date:** June 12, 2026
**Authors:** Subin George, Jewel K M

---

## 1. HUD API Direct Testing (curl/Postman)

These tests require direct HTTP calls to the HUD API (`/api/oot/results`) with crafted payloads, bypassing the composite callback action.

| ID | Test | How to Execute | Expected |
|----|------|----------------|----------|
| AUTH-01..04 | Valid/missing/wrong/length-mismatch token | `curl -X POST` with varying `X-OOT-Relay-Token` headers | 200 / 401 / 401 / 401 |
| AUTH-05 | Server misconfigured (OOT_RELAY_TOKEN env unset) | Temporarily remove env var from Vercel deployment | 500 |
| AUTH-06 | Empty token header | `curl -H "X-OOT-Relay-Token: "` | 401 |
| AUTH-07 | Token with extra whitespace | `curl -H "X-OOT-Relay-Token:  <token> "` | 401 |
| HTTP-01..04 | Wrong HTTP method (GET, PUT, DELETE, OPTIONS) | `curl -X GET /api/oot/results` etc. | 405 |
| SIZE-03 | Payload exactly at 2MB boundary | `curl` with 2MB JSON body | 200 |
| SIZE-04 | Payload over 2MB | `curl` with 2MB+1 body | 413 |
| SIZE-05 | Empty body `{}` | `curl -d '{}'` | 400 |
| PARSE-02 | Double-stringified JSON body | `curl -d '"{\\"foo\\":1}"'` | 200 (HUD does `JSON.parse`) |
| PARSE-03 | Invalid JSON string body | `curl -d '"not{json"'` | 500 |
| SEC-03 | Timing attack resistance | Many requests with incrementally correct token prefix; measure response times | `timingSafeEqual` yields constant-time response |
| SEC-06 | Spoofed verified_repo in untrusted block | POST with `trusted.verified_repo ≠ untrusted...repository.full_name` | Record uses trusted value |
| SEC-07 | Elevated downstream_repo_level | Set `untrusted` level to "L4" while `trusted` is "L2" | Level from trusted block used |
| SEC-12 | SQL injection in job_name | `job_name: "'; DROP TABLE oot_workflow_job;--"` | Stored verbatim; ClickHouse parameterized queries prevent execution |
| SEC-14 | Deeply nested JSON | 1000-level nested object | Accept (no depth limit); monitor memory |
| SEC-16 | Null bytes in fields | `job_name: "test\x00malicious"` | Accepted by API; verify DynamoDB & ClickHouse handling |

### Execution Template

```bash
# Example: AUTH-02 — Missing token
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "https://hud.pytorch.org/api/oot/results" \
  -H "Content-Type: application/json" \
  -d '{"trusted":{},"untrusted":{}}'
# Expected: 401

# Example: SEC-12 — SQL injection
curl -s -w "\n%{http_code}" \
  -X POST "https://hud.pytorch.org/api/oot/results" \
  -H "X-OOT-Relay-Token: $OOT_RELAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"trusted":{"verified_repo":"test/repo"},"untrusted":{"callback_payload":{"workflow":{"job_name":"'\''; DROP TABLE--","check_run_id":"123","name":"test"},"delivery_id":"d1","status":"completed","conclusion":"success","payload":{"repository":{"full_name":"test/repo"}}}}}'
# Expected: 200, value stored as literal string
```

---

## 2. DynamoDB Verification (AWS Console / CLI)

| ID | Test | How to Execute | Expected |
|----|------|----------------|----------|
| DYNAMO-01 | First write creates record | Run workflow, then `aws dynamodb get-item` | Record exists with `in_progress` fields |
| DYNAMO-02 | Update sets completed fields | Run workflow to completion, query item | `status=completed`, `conclusion`, `completed_at` all set |
| DYNAMO-03 | Duplicate in_progress idempotent | Send same `in_progress` callback twice, compare items | Identical records |
| DYNAMO-04 | Duplicate completed idempotent | Send same `completed` callback twice | Identical records |
| DYNAMO-05 | Out-of-order: completed before in_progress | Send completed first, then in_progress | Both writes succeed; all fields present |
| KEY-02 | Special chars in repo name | Trigger from a repo like `org-name/repo.name` | Key includes special chars verbatim |
| KEY-03 | Long workflow name (200+ chars) | Create a workflow file with a very long name | DynamoDB accepts (key limit 2048 bytes) |
| FIELD-03..05 | Missing delivery_id / workflow.name / verified_repo | Direct API call with missing fields | `dynamoKey` contains "undefined" — data corruption signal |

### Execution Template

```bash
# Query a specific DynamoDB item
aws dynamodb get-item \
  --table-name torchci-oot-workflow-job \
  --key '{"dynamoKey":{"S":"subinz1/crcr-test/<delivery_id>/Test: L2 Callback Lifecycle/lifecycle-happy-path/<check_run_id>"}}' \
  --region us-east-1 | python3 -m json.tool
```

---

## 3. DynamoDB → ClickHouse Replication

| ID | Test | How to Execute | Expected |
|----|------|----------------|----------|
| REPL-01 | New record replicated | Insert via callback, query ClickHouse after ~2min | Row appears in `default.oot_workflow_job` |
| REPL-02 | Updated record replicated | Update from in_progress → completed, query ClickHouse | Row shows completed state |
| REPL-03 | Replication lag measurement | Record timestamp at DynamoDB write; poll ClickHouse until appears | Expected < 5 min |
| REPL-04 | Schema field mapping | Record with all fields set; compare DynamoDB item vs ClickHouse row | All fields mapped correctly |
| REPL-05 | ClickHouse ALIAS columns | `SELECT repository_full_name, duration_seconds FROM ...` | ALIAS columns resolve from base columns |
| REPL-06 | Replicator table mapping | Check Lambda replicator config | `torchci-oot-workflow-job` → `default.oot_workflow_job` |
| REPL-07 | FINAL keyword deduplication | Multiple updates to same record, then `SELECT ... FINAL` | Single latest row returned |

### Execution Template

```sql
-- Verify record in ClickHouse
SELECT *
FROM default.oot_workflow_job FINAL
WHERE dynamoKey = 'subinz1/crcr-test/<delivery_id>/<workflow>/<job>/<check_run_id>'
FORMAT Vertical;

-- Measure replication lag
SELECT
  dynamoKey,
  completed_at,
  now() - toDateTime(completed_at) AS lag_seconds
FROM default.oot_workflow_job FINAL
WHERE downstream_repo = 'subinz1/crcr-test'
ORDER BY completed_at DESC
LIMIT 5;
```

---

## 4. Frontend Manual Verification (Browser)

| ID | Test | How to Verify | Expected |
|----|------|---------------|----------|
| UI-01 | /oot page loads with data | Browse `https://hud.pytorch.org/oot` | Table with repos, pass rates, durations |
| UI-02 | Loading state | Throttle network in DevTools, reload /oot | Loading skeleton/spinner visible |
| UI-03 | Error state | Temporarily break ClickHouse connection | Error message displayed, not blank page |
| UI-04 | Empty state | Use a time window with no data (days=0) | "No data" message |
| UI-05 | Pass rate coloring | Mix of 100% and 0% repos | Green for 100%, red for 0% |
| UI-06 | Click-through to backend dashboard | Click a repo row | Navigates to `/oot/[org]/[repo]` |
| UI-07 | Days filter | Change time window dropdown | Data refreshes with new range |
| UI-08 | Backend dashboard loads | Browse `/oot/subinz1/crcr-test` | Job matrix with status chips |
| UI-09 | Status chip colors | Trigger success/failure/in_progress/cancelled | Green/red/yellow/grey chips respectively |
| UI-10 | Status chip labels | Various conclusions | Correct text labels |
| UI-11 | Workflow URL link | Click a job's URL | Opens downstream GHA run |
| UI-12 | Artifact URL link | Job with artifact_url set | Link opens artifact |
| UI-13 | Invalid org/repo | Browse `/oot/nonexistent/repo` | Empty state, no crash |
| UI-15 | PR with OOT results | Open a PR page that has OOT jobs | OotPrSection renders |
| UI-16 | PR without OOT results | Open a PR with no OOT jobs | Section hidden or "No OOT results" |
| UI-17 | Multiple backends on PR | PR dispatched to 3+ backends | All shown as separate rows |
| UI-18 | In-progress job on PR | Backend still running | "running" chip with yellow |
| SEC-10/11 | XSS verification | After security workflow runs, inspect HUD | XSS payloads rendered as text, not executed |

---

## 5. OIDC & Lambda Security (Callback Lambda Side)

| ID | Test | How to Execute | Expected |
|----|------|----------------|----------|
| SEC-18 | Invalid OIDC token | `curl` with forged JWT to callback Lambda URL | Lambda rejects |
| SEC-19 | OIDC wrong audience | Valid GitHub OIDC token but audience ≠ `pytorch-cross-repo-ci-relay` | Lambda rejects |
| SEC-20 | OIDC from non-allowlisted repo | Run callback from a repo not in the CRCR allowlist | Lambda rejects at allowlist check |
| SEC-22 | Callback URL publicly accessible | `curl -X POST <Lambda Function URL>` without OIDC | Lambda rejects (no valid token) |

### Execution Template

```bash
# SEC-22: Direct POST without OIDC
curl -s -o /dev/null -w "%{http_code}" \
  -X POST "$CRCR_CALLBACK_URL" \
  -H "Content-Type: application/json" \
  -d '{"status":"completed","conclusion":"success"}'
# Expected: 401 or 403
```

---

## 6. Error Handling & Resilience

| ID | Test | How to Execute | Expected |
|----|------|----------------|----------|
| ERR-01 | DynamoDB write failure | Introduce IAM deny policy on `PutItem` temporarily | HUD API returns 500; Lambda receives error |
| ERR-04 | HUD API down | Point Lambda to non-existent URL | Callback Lambda gets 502/503 |
| ERR-05 | HUD API slow response | Add artificial delay to API handler | Composite action `max-time: 10` timeout; retries 3x |
| NET-01 | Network failure | Block HUD URL at security group level | curl fails; composite action retries |
| CH-01 | ClickHouse down | Stop ClickHouse or block port | Replicator Lambda fails; DynamoDB Streams auto-retries |
| CH-02 | ClickHouse schema mismatch | Add new field to DynamoDB record not in CH schema | Replicator skips unknown fields or errors |
| CH-03 | Replicator Lambda error | Inject crash in replicator code | DynamoDB Streams retries with backoff |
| CH-04 | ClickHouse query timeout | Query with no time filter on large dataset | HUD API returns timeout; frontend shows error |
| FE-01 | ClickHouse API returns 500 | Break ClickHouse proxy | Frontend shows error, not blank page |
| FE-02 | ClickHouse API returns invalid JSON | Proxy returns HTML | Frontend shows "Failed to load" |
| FE-03 | Network timeout on frontend | Throttle network to HUD API | Loading spinner, then timeout |
| FE-04 | Partial data | Some fields null/missing | Frontend handles gracefully (no undefined crashes) |

---

## 7. Performance & Load

| ID | Test | How to Execute | Expected |
|----|------|----------------|----------|
| PERF-01 | High callback volume | Script 5000 `curl` calls to callback Lambda | Lambda and HUD API handle without throttling |
| PERF-02 | ClickHouse query performance | With 100K+ rows, run summary query | Completes < 2s |
| PERF-03 | Frontend render with many repos | 50+ downstream repos in summary | Page renders without lag |
| PERF-04 | Backend dashboard with many jobs | Dashboard with 1000+ jobs | Pagination or virtual scroll works |
| PERF-05 | DynamoDB UpdateItem latency | Measure p99 of single writes | < 100ms |
| PERF-06 | Concurrent Lambda invocations | 50 simultaneous callbacks | All processed within reserved concurrency (50) |
| SEC-21 | Rate limiting | Burst of 100+ requests from same repo | Lambda rate limiter activates |

### Execution Template

```bash
# PERF-01: Load test (run from EC2 in same region)
for i in $(seq 1 100); do
  curl -s -o /dev/null -w "%{http_code}\n" \
    -X POST "$CRCR_CALLBACK_URL" \
    -H "Authorization: Bearer $OIDC_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"status":"completed","conclusion":"success"}' &
done
wait
```

---

## 8. Regression Tests

| ID | Test | How to Execute | Expected |
|----|------|----------------|----------|
| REG-01 | ootUtils.test.ts passes | `npm test` in `torchci/` | All tests pass |
| REG-02 | ootResults.test.ts passes | `npm test` in `torchci/` | All tests pass |
| REG-03 | ClickHouse schema backward compat | Apply schema migration, verify replicator | `failed_tests_json` stays nullable |
| REG-04 | Composite action backward compat | Update `action.yml`, trigger from existing downstream | Existing workflows unaffected |
| REG-05 | DynamoDB table exists | `aws dynamodb describe-table` | `torchci-oot-workflow-job` exists with correct key |
| REG-06 | Replicator mapping exists | Check Lambda replicator config | Mapping `torchci-oot-workflow-job` → `default.oot_workflow_job` present |

---

## Execution Priority

| Priority | Description | Count |
|----------|-------------|-------|
| **P0** | Must pass before merge/deployment | ~35 tests |
| **P1** | Important, workarounds acceptable | ~30 tests |
| **P2** | Edge cases, hardening, future work | ~15 tests |

## Prerequisites

- AWS Console access (DynamoDB, Lambda, CloudWatch, IAM)
- ClickHouse query access (direct or via HUD API)
- `OOT_RELAY_TOKEN` (HUD_BOT_KEY) from AWS Secrets Manager
- `CRCR_CALLBACK_URL` from Lambda environment
- Vercel deployment access (for HUD API config changes)
- Valid OIDC token from a GHA run (for Lambda auth tests)
- Browser with DevTools (for frontend verification)
