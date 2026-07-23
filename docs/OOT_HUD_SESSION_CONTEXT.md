# OOT HUD Session Context — Restore Point

**Saved:** May 24, 2026

---

## 1. Repository Setup

- **Working repo (pytorch):** `/home/sugeorge/Documents/PR-related-files/pytorch`
- **Working repo (test-infra):** `/home/sugeorge/Documents/PR-related-files/test-infra`
- **Fork:** `subinz1/test-infra`
- **Upstream:** `pytorch/test-infra`
- **Remote `origin`:** `https://github.com/subinz1/test-infra.git`
- **Remote `upstream`:** `https://github.com/pytorch/test-infra`

---

## 2. PR Stack (Split from #8069)

The original PR #8069 was split into 3 stacked PRs per reviewer request from @atalman and @malfet.

### PR 1 — DB queries + utils + tests
- **PR:** https://github.com/pytorch/test-infra/pull/8110
- **Branch:** `oot-hud-1-queries`
- **Status:** ✅ MERGED into `main` as `d6b24c2`
- **Files (8):**
  - `torchci/clickhouse_queries/oot_summary/params.json`
  - `torchci/clickhouse_queries/oot_summary/query.sql`
  - `torchci/clickhouse_queries/oot_backend_dashboard/params.json`
  - `torchci/clickhouse_queries/oot_backend_dashboard/query.sql`
  - `torchci/clickhouse_queries/oot_pr_results/params.json`
  - `torchci/clickhouse_queries/oot_pr_results/query.sql`
  - `torchci/lib/oot/ootUtils.ts`
  - `torchci/test/ootUtils.test.ts`

### PR 2 — OOT frontend components
- **PR:** https://github.com/pytorch/test-infra/pull/8111
- **Branch:** `oot-hud-2-components`
- **Status:** Open (approved by @atalman and @zxiiro, awaiting CI pass + merge)
- **Latest commit:** `6c37a8d` (fix for missing `upstreamRepo` in `MatrixRow`)
- **Files (3):**
  - `torchci/components/oot/OotPrSection.tsx`
  - `torchci/pages/oot/index.tsx`
  - `torchci/pages/oot/[org]/[repo].tsx`
- **Note:** Rebased by @atalman onto `main` after #8110 merged. Additional fix commit pushed for `upstreamRepo` TypeScript error.

### PR 3 — API endpoint + integration
- **PR:** https://github.com/pytorch/test-infra/pull/8112
- **Branch:** `oot-hud-3-integration`
- **Status:** Open (approved by @atalman and @zxiiro, awaiting #8111 merge)
- **Latest commit:** `d25f5e9` (rebased onto #8111 fix)
- **Files (4 unique):**
  - `torchci/pages/api/oot/results.ts`
  - `torchci/pages/[repoOwner]/[repoName]/pull/[prNumber].tsx`
  - `aws/lambda/clickhouse-replicator-dynamo/lambda_function.py`
  - `torchci/test/ootResults.test.ts`
- **Merge order:** After #8111

### Original PR
- **PR:** https://github.com/pytorch/test-infra/pull/8069
- **Branch:** `oot-hud-pipeline`
- **Status:** Open (kept as tracking reference, to be closed after all 3 merge)

### ClickHouse Schema PR
- **PR:** https://github.com/pytorch/test-infra/pull/8105
- **Status:** ✅ MERGED — `default.oot_workflow_job` table schema

---

## 3. Related PRs and Repos

| PR/Repo | Description | Status |
|---------|-------------|--------|
| pytorch/rfcs#96 | RFC-0054: HUD Integration for OOT CI Results | Open |
| pytorch/test-infra#7967 | [CRCR] Initial implementation of L2 | Merged |
| pytorch/ci-infra#614 | L2 CRCR deployment configuration (Terraform) | Merged |
| pytorch/pytorch#184482 | Add pytorch/crcr-test to L2 allowlist | Merged |
| pytorch/crcr-test | Test repo for CRCR L1-L4 testing | Active |
| pytorch/test-infra#8108 | Bump mypy python_version 3.9→3.11 (lint fix) | Merged |

---

## 4. Key People

- **@atalman** (Andrey Talman) — pytorch/test-infra maintainer, primary reviewer
- **@malfet** (Nikita) — pytorch/test-infra maintainer, reviewer
- **@zxiiro** — Reviewer, approved PRs
- **@KarhouTam** — L2 relay author, reviewed #8069
- **@can-gaa-hou** — L2 relay co-author
- **@fffrog** — L2 relay co-author
- **@albanD** — PyTorch, GitHub App approvals
- **@groenenboomj** (Joseph) — Team member
- **@jewelkm89** (Jewel) — Team member
- **@subinz1** (Subin George) — PR author

---

## 5. Key Technical Details

### Authentication
- API endpoint uses `X-OOT-Relay-Token` header
- Timing-safe comparison via `crypto.timingSafeEqual` with `Uint8Array`
- Token stored in `process.env.OOT_RELAY_TOKEN`

### DynamoDB
- Table: `torchci-oot-workflow-job`
- Key: `dynamoKey` = `{verified_repo}/{delivery_id}/{workflow_name}/{job_name}/{check_run_id}`
- Uses `UpdateItem` with dynamic `SET` expressions (prevents clobbering)

### ClickHouse
- Table: `default.oot_workflow_job`
- Engine: `SharedReplacingMergeTree`
- Replicated from DynamoDB via `clickhouse-replicator-dynamo` Lambda

### Frontend Pages
- `/oot` — Global OOT summary
- `/oot/[org]/[repo]` — Per-backend dashboard
- PR page integration: `OotPrSection` rendered only for `pytorch/pytorch` PRs

### Trust Levels
- L1: Dispatch only (no callback)
- L2: Dispatch + callback with OIDC verification + HUD reporting
- L3: Future — performance-gated
- L4: Future — full integration

---

## 6. Review Feedback Addressed

All of these are incorporated into the split PRs:

1. ✅ `timingSafeEqual` for token comparison (from @atalman)
2. ✅ `Uint8Array` wrapping for `Buffer.from` (from @atalman)
3. ✅ Remove dead `failed_tests_json` field (from @atalman)
4. ✅ Replace `test_results?: any` with typed shape (from @atalman)
5. ✅ Guard against malformed `row.repo` in summary page (from @atalman)
6. ✅ `LIMIT 100` on `oot_pr_results` query (from @atalman)
7. ✅ Use `upstream_repo` instead of hardcoded `pytorch/pytorch` in PR links (from @malfet)
8. ✅ Only render `OotPrSection` for `pytorch/pytorch` PRs (from @malfet)
9. ✅ Fix HTTP 502→500 for DynamoDB errors (from @KarhouTam)
10. ✅ Remove unused `groupKey` variable (from @KarhouTam)
11. ✅ Extract shared `conclusionColor`/`conclusionLabel` to ootUtils (from @KarhouTam)
12. ✅ Add `upstream_repo` to `OotJobRow` and `upstreamRepo` to `MatrixRow` (from @atalman, post-split)
13. ✅ Validate `job_name` and `check_run_id` as required fields
14. ✅ Missing env var returns 500 "Server misconfigured"

---

## 7. Branch State (as of May 24, 2026)

```
oot-hud-1-queries     → merged into upstream/main
oot-hud-2-components  → 6c37a8d (pushed to origin, PR #8111)
oot-hud-3-integration → d25f5e9 (pushed to origin, PR #8112)
oot-hud-pipeline      → original branch (PR #8069, tracking reference)
```

---

## 8. Other Artifacts

- **crcr-test README:** `/home/sugeorge/Documents/PR-related-files/pytorch/agent_space/crcr-test-README.md`
  - Onboarding doc for https://github.com/pytorch/crcr-test
  - Contacts: @groenenboomj, @jewelkm89, @subinz1, @albanD, @atalman, @fffrog

- **Conference Abstract:** `/home/sugeorge/Documents/PR-related-files/pytorch/agent_space/PyTorch_NA_Conference_Abstract.md`
  - Title: "Scaling PyTorch's Compatibility Promise — A Tiered CI Relay for Out-of-Tree Backends"
  - Authors: Subin George, Jewel Mathew

- **RFC V3:** `/home/sugeorge/Documents/PR-related-files/pytorch/OOT_HUD_RFC_V3.md`

---

## 9. Pending / Next Steps

1. Wait for CI to pass on #8111 (after `upstreamRepo` fix) → merge
2. After #8111 merges, rebase #8112 onto main → CI → merge
3. Close original #8069 once all 3 are merged
4. Vercel preview access — requested but not yet granted to @subinz1
5. Integration testing with live L2 relay data once all PRs merge
