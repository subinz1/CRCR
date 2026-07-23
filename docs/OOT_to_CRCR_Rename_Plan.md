# OOT → CRCR Rename Plan — pytorch/test-infra

**Scope:** Rename all `oot`/`OOT` references to `crcr`/`CRCR` across the test-infra repository.
**Reason:** Standardize naming to use the official "Cross-Repository CI Relay" (CRCR) terminology.

---

## 1. File/Directory Renames (9 total)

### Source paths (directories + files)

| # | Current Path | New Path |
|---|---|---|
| 1 | `torchci/pages/api/oot/results.ts` | `torchci/pages/api/crcr/results.ts` |
| 2 | `torchci/lib/oot/ootUtils.ts` | `torchci/lib/crcr/crcrUtils.ts` |
| 3 | `torchci/components/oot/OotPrSection.tsx` | `torchci/components/crcr/CrcrPrSection.tsx` |
| 4 | `torchci/clickhouse_queries/oot_summary/query.sql` | `torchci/clickhouse_queries/crcr_summary/query.sql` |
| 5 | `torchci/clickhouse_queries/oot_backend_dashboard/query.sql` | `torchci/clickhouse_queries/crcr_backend_dashboard/query.sql` |
| 6 | `torchci/clickhouse_queries/oot_pr_results/query.sql` | `torchci/clickhouse_queries/crcr_pr_results/query.sql` |
| 7 | `clickhouse_db_schema/default.oot_workflow_job/schema.sql` | `clickhouse_db_schema/default.crcr_workflow_job/schema.sql` |
| 8 | `torchci/test/ootUtils.test.ts` | `torchci/test/crcrUtils.test.ts` |
| 9 | `torchci/test/ootResults.test.ts` | `torchci/test/crcrResults.test.ts` |

---

## 2. Content Changes by File (~13 files)

### 2.1 Lambda — `aws/lambda/cross_repo_ci_relay/`

| # | File | Changes |
|---|---|---|
| 1 | `utils/config.py` | `oot_status_ttl` → `crcr_status_ttl`; comment `OOT-status records` → `CRCR-status records` |
| 2 | `utils/redis_helper.py` | `"oot:allowlist_yaml"` → `"crcr:allowlist_yaml"`, `"oot:state:"` → `"crcr:state:"`, `"oot:rate:"` → `"crcr:rate:"`, `"oot:in_progress"` → `"crcr:in_progress"`, `config.oot_status_ttl` → `config.crcr_status_ttl` |
| 3 | `README.md` | `oot:state:{delivery_id}:{repo}:{run_id}:{run_attempt}` → `crcr:state:...` |
| 4 | `tests/test_redis_helper.py` | `"oot:in_progress"` (6 occurrences) → `"crcr:in_progress"` |
| 5 | `tests/test_callback_handler.py` | `oot_status_ttl` references |
| 6 | `tests/test_cleanup_handler.py` | `"http://hud/api/oot/results"` → `"http://hud/api/crcr/results"` |
| 7 | `tests/test_hud.py` | `api/oot` endpoint references |

### 2.2 ClickHouse Replicator

| # | File | Changes |
|---|---|---|
| 8 | `aws/lambda/clickhouse-replicator-dynamo/lambda_function.py` | `oot_workflow_job` → `crcr_workflow_job` |

### 2.3 Frontend — `torchci/`

| # | File | Changes |
|---|---|---|
| 9 | `torchci/lib/fetchRecentWorkflows.ts` | `fetchOotWorkflows` → `fetchCrcrWorkflows`, `oot_workflow_job` → `crcr_workflow_job`, comments |
| 10 | `torchci/pages/api/drci/drci.ts` | `fetchOotWorkflows` → `fetchCrcrWorkflows`, `ootWorkflows` → `crcrWorkflows`, error messages, comments |
| 11 | `torchci/pages/crcr/[org]/[repo].tsx` | `ootUtils` → `crcrUtils` imports |
| 12 | `torchci/pages/[repoOwner]/[repoName]/pull/[prNumber].tsx` | `OotPrSection` → `CrcrPrSection` import |

---

## 3. String Rename Map

### 3.1 Redis Keys

| Old | New |
|---|---|
| `oot:state:` | `crcr:state:` |
| `oot:rate:` | `crcr:rate:` |
| `oot:allowlist_yaml` | `crcr:allowlist_yaml` |
| `oot:in_progress` | `crcr:in_progress` |

### 3.2 Config Fields

| Old | New |
|---|---|
| `oot_status_ttl` | `crcr_status_ttl` |

### 3.3 ClickHouse Tables

| Old | New |
|---|---|
| `oot_workflow_job` | `crcr_workflow_job` |
| `oot_pr_results` | `crcr_pr_results` |
| `oot_summary` | `crcr_summary` |
| `oot_backend_dashboard` | `crcr_backend_dashboard` |

### 3.4 DynamoDB Stream

| Old | New |
|---|---|
| `torchci-oot-workflow-job` | `torchci-crcr-workflow-job` |

### 3.5 API Endpoints

| Old | New |
|---|---|
| `/api/oot/results` | `/api/crcr/results` |

### 3.6 TypeScript Functions & Variables

| Old | New |
|---|---|
| `fetchOotWorkflows` | `fetchCrcrWorkflows` |
| `ootUtils` | `crcrUtils` |
| `ootResults` | `crcrResults` |
| `ootWorkflows` | `crcrWorkflows` |

### 3.7 React Components & Types

| Old | New |
|---|---|
| `OotPrSection` | `CrcrPrSection` |
| `OotJobRow` | `CrcrJobRow` |
| `OotWorkflowJobRecord` | `CrcrWorkflowJobRecord` |
| `OotSummaryTable` | `CrcrSummaryTable` |
| `OotMatrix` | `CrcrMatrix` |

### 3.8 Environment Variables & Headers

| Old | New |
|---|---|
| `OOT_RELAY_TOKEN` | `CRCR_RELAY_TOKEN` |
| `X-OOT-Relay-Token` | `X-CRCR-Relay-Token` |
| `OOT_STATUS_TTL` | `CRCR_STATUS_TTL` |

### 3.9 CSS Classes (in mockup HTML files)

| Old | New |
|---|---|
| `oot-table` | `crcr-table` |
| `oot-page` | `crcr-page` |
| `oot-page-header` | `crcr-page-header` |

### 3.10 Prose / Documentation

| Old | New |
|---|---|
| `OOT` (standalone) | `CRCR` |
| `OOT-specific` | `CRCR-specific` |
| `Out-of-Tree` (where used as system name) | `CRCR` |

---

## 4. Summary

| Category | Count |
|---|---|
| **File/directory renames** | 9 |
| **Files with content changes** | ~13 |
| **Total files affected** | **~21** |
| **Unique string patterns to replace** | ~30 |

---

## 5. Notes

- **ClickHouse table renames** (`oot_workflow_job` → `crcr_workflow_job`, etc.) require a coordinated migration — the schema file rename alone won't rename the live table. A migration script or `RENAME TABLE` statement is needed.
- **DynamoDB stream name** (`torchci-oot-workflow-job`) is an AWS resource — renaming requires infrastructure changes, not just code changes.
- **Redis key prefix changes** (`oot:*` → `crcr:*`) should be deployed carefully — existing keys in Redis will still use the old prefix until they expire (TTL-based).
- **API endpoint change** (`/api/oot/results` → `/api/crcr/results`) is a breaking change for any existing callers. Consider keeping the old endpoint as a redirect temporarily.
- The **GitHub Actions composite action** (`cross-repo-ci-relay-callback`) does not contain "oot" in its name or path — no rename needed there.
