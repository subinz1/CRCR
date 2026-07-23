# Cross-Repository CI Relay (CRCR) — Security Assessment

**Authors:** Subin George, Jewel K M, Joel Groenenboom
**Date:** June 2026
**Status:** L2 pipeline deployed and operational
**Audience:** @malfet, @albanD, PyTorch Infrastructure Team

---

## 1. System Overview

The Cross-Repository CI Relay (CRCR) enables out-of-tree (OOT) backend repositories to run CI against upstream PyTorch PRs and report results to the PyTorch CI HUD. The system spans four trust domains:

| Component | Trust Domain | Runs In |
|---|---|---|
| Webhook Lambda | PyTorch-owned | AWS (account: 391835788720) |
| Callback Lambda | PyTorch-owned | AWS (same account) |
| Redis (ElastiCache) | PyTorch-owned | AWS (same account) |
| HUD API + DynamoDB | PyTorch-owned | Vercel + AWS (HUD account) |
| Downstream CI workflows | Third-party owned | GitHub Actions (external repos) |

The critical security boundary is between **PyTorch-owned infrastructure** and **third-party downstream repositories** that report CI results.

---

## 2. Security Controls — Current State

### 2.1 Webhook Ingress (GitHub → Webhook Lambda)

| Control | Implementation | Status |
|---|---|---|
| **HMAC-SHA256 signature verification** | `hmac.compare_digest()` against GitHub App webhook secret | Active |
| **Upstream repo pinning** | Rejects webhooks from repos other than `pytorch/pytorch` (case-insensitive) | Active |
| **Event type filtering** | Only `pull_request` and `push` events processed; all others silently dropped before signature verification | Active |
| **PR action filtering** | Only `opened`, `reopened`, `synchronize`, `closed` actions dispatched | Active |

**How it works:** GitHub signs every webhook delivery with the App's shared secret. The Lambda verifies this signature using `hmac.compare_digest()` (timing-safe comparison) before processing any payload. This guarantees webhook authenticity — only GitHub can produce a valid signature.

### 2.2 Callback Authentication (Downstream CI → Callback Lambda)

| Control | Implementation | Status |
|---|---|---|
| **GitHub OIDC token verification** | RS256 JWT verified against GitHub's JWKS endpoint (`token.actions.githubusercontent.com`) | Active |
| **Audience claim enforcement** | Token must have `aud: "pytorch-cross-repo-ci-relay"` | Active |
| **Issuer claim enforcement** | Token must originate from `https://token.actions.githubusercontent.com` | Active |
| **Repository identity extraction** | `repository` claim from OIDC token used as `verified_repo` — cannot be spoofed | Active |

**How it works:** Downstream workflows mint a GitHub OIDC token scoped to audience `pytorch-cross-repo-ci-relay`. The Callback Lambda verifies this token against GitHub's public JWKS keys (RS256). The `repository` claim in the token is cryptographically bound to the calling repository — a workflow in `org/repo-a` cannot produce a token claiming to be `org/repo-b`. This `verified_repo` is what the relay trusts for identity.

### 2.3 Allowlist Authorization

| Control | Implementation | Status |
|---|---|---|
| **Tiered allowlist (L1–L4)** | YAML file in `pytorch/pytorch` repo (`allowlist.yml`) | Active |
| **L2+ gating for callbacks** | Only repos at L2 or higher can report results to HUD | Active |
| **Duplicate repo rejection** | Parser rejects repos appearing in multiple levels | Active |
| **Redis-cached with TTL floor** | Allowlist cached with minimum 15-minute TTL to avoid GitHub rate-limit exhaustion | Active |

**How it works:** The allowlist lives in `pytorch/pytorch` (controlled by PyTorch maintainers). A downstream repo must be explicitly listed at L2+ to have its callback results accepted and forwarded to HUD. Removal from the allowlist immediately revokes callback access on the next cache refresh (≤ 20 minutes).

### 2.4 State Machine Integrity (Redis)

| Control | Implementation | Status |
|---|---|---|
| **3-state lifecycle** | `DISPATCHED → IN_PROGRESS → COMPLETED` per delivery+repo+check_run_id | Active |
| **Dispatch-first enforcement** | Callbacks rejected if no prior `DISPATCHED` record exists for the `delivery_id` | Active |
| **Duplicate rejection** | Duplicate `IN_PROGRESS` or `COMPLETED` for the same `check_run_id` are rejected | Active |
| **Sequence enforcement** | `COMPLETED` without prior `IN_PROGRESS` is rejected | Active |
| **TTL-based expiry** | State records expire after 3 days (`OOT_STATUS_TTL = 259200s`) | Active |

**How it works:** The webhook Lambda writes a `DISPATCHED` record to Redis when it sends a `repository_dispatch`. The callback Lambda checks for this record before accepting any `in_progress` or `completed` callback. This ensures a downstream repo cannot inject results for a dispatch that never happened. The `check_run_id` (assigned by GitHub, not controllable by the workflow) provides per-job uniqueness.

### 2.5 Rate Limiting

| Control | Implementation | Status |
|---|---|---|
| **Per-repo sliding window** | Redis sorted set with 60-second window, configurable limit per repo | Active |
| **Fail-closed on Redis error** | Rate limit check returns HTTP 500 if Redis is unreachable | Active |

**How it works:** Each callback increments a per-repo counter in Redis. If a repo exceeds the configured request rate within a 60-second window, subsequent requests receive HTTP 429. This prevents a compromised or misbehaving downstream repo from flooding the pipeline.

### 2.6 HUD API Authentication (Relay → HUD)

| Control | Implementation | Status |
|---|---|---|
| **Shared bot token** | `x-hud-internal-bot` header verified against `INTERNAL_API_TOKEN` on Vercel | Active |
| **Standard HUD auth helper** | Uses `checkAuthWithApiToken()` (same as other internal HUD endpoints) | Active |
| **Payload size cap** | 2MB limit enforced at both Next.js body parser and application level | Active |

### 2.7 Data Trust Separation (Relay → HUD Payload)

| Control | Implementation | Status |
|---|---|---|
| **Trusted/untrusted namespace split** | Relay sends `{ trusted: {...}, untrusted: {...} }` to HUD | Active |
| **`verified_repo` in trusted namespace** | OIDC-verified repo identity is in the `trusted` block | Active |
| **Self-reported data in untrusted namespace** | Downstream's `workflow` dict (status, conclusion, name, URL, test_results) is under `untrusted.callback_payload` | Active |

**Why this matters:** The downstream workflow controls the contents of `workflow.status`, `workflow.conclusion`, `workflow.name`, etc. These are self-reported and could be fabricated by a malicious maintainer. By placing `verified_repo` in the `trusted` namespace, HUD can always identify the true caller regardless of what the callback body claims.

### 2.8 Infrastructure Security

| Control | Implementation | Status |
|---|---|---|
| **TLS-in-transit (Redis)** | `rediss://` scheme enforced when running on AWS Lambda | Active |
| **AWS Secrets Manager** | GitHub App private key and HUD bot key stored in Secrets Manager, not environment variables | Active |
| **Lambda Function URLs** | HTTPS-only endpoints with AWS-managed TLS certificates | Active |
| **Separate AWS accounts** | CRCR Lambdas and HUD/DynamoDB run in separate AWS accounts | Active |

---

## 3. Known Risks and Residual Threats

### 3.1 RISK: Malicious Downstream Maintainer — Data Fabrication

**Severity:** Medium
**Likelihood:** Low

A compromised or malicious maintainer of an allowlisted L2+ repository can:

1. **Fabricate `workflow.status` / `workflow.conclusion`** — They can report `success` for a PR that actually failed their CI, or `failure` for a PR that passed. HUD displays this self-reported data.

2. **Tamper with `test_results`** — Passed/failed/skipped counts are self-reported and could be inflated or zeroed out.

3. **Report results for PRs they were legitimately dispatched for, but with false conclusions** — The state machine ensures a valid dispatch existed, but cannot verify the truthfulness of the reported outcome.

**Current Mitigations:**
- Every HUD row carries `verified_repo` (OIDC-authenticated), making the source of any fabricated data identifiable.
- Allowlist is controlled by PyTorch maintainers; offending repos can be removed.
- `check_run_id` is GitHub-assigned and prevents cross-job impersonation within the same dispatch.

**Residual Gap:** There is no automated mechanism to detect fabricated results. Detection relies on manual observation or cross-referencing with the actual GitHub Actions run URL (which is also self-reported, though the `verified_repo` + `delivery_id` combination provides a strong audit trail).

**Possible Future Mitigation:** Cross-validate reported `conclusion` against the GitHub Check Runs API using the `check_run_id` (which is GitHub-assigned and trustworthy). This would require an additional GitHub API call per callback but would detect mismatches.

### 3.2 RISK: Replay Attacks

**Severity:** Low
**Likelihood:** Low

A downstream repo could replay an older `in_progress` or `completed` callback using a previously valid OIDC token and delivery_id.

**Current Mitigations:**
- OIDC tokens have a short expiry (~5 minutes from GitHub).
- The state machine rejects duplicate `IN_PROGRESS` and duplicate `COMPLETED` for the same `check_run_id`.
- Redis records expire after 3 days, limiting the replay window.

**Residual Gap:** There is no dispatch-side nonce. Within the OIDC token's validity window (~5 minutes), a replay of a legitimate callback could theoretically succeed if it targets a different `check_run_id`. In practice, `check_run_id` is GitHub-assigned per job execution and not predictable.

### 3.3 RISK: Stale `in_progress` Records

**Severity:** Low
**Likelihood:** Medium

If a downstream workflow crashes before sending the `completed` callback (e.g., runner failure, GitHub infrastructure issue, concurrency cancellation), the record remains permanently as `in_progress` in DynamoDB/ClickHouse. The Redis state expires after 3 days, but the HUD data persists indefinitely.

**Current Mitigations:**
- Redis TTL (3 days) cleans up state machine records.
- The `if: always()` pattern in the callback action attempts to send `completed` even on job failure.

**Residual Gap:** No cleanup mechanism for stale DynamoDB/ClickHouse records. The HUD will show these as permanently "running" jobs.

**Possible Future Mitigation:** A scheduled Lambda or cron job that scans for `in_progress` records older than a configurable threshold (e.g., 6 hours) and marks them as `timed_out`.

### 3.4 RISK: Allowlist Poisoning via Upstream PR

**Severity:** Medium
**Likelihood:** Very Low

The allowlist file lives in `pytorch/pytorch`. A PR that modifies `allowlist.yml` to add a malicious repository would, upon merge, grant that repository L2+ callback access.

**Current Mitigations:**
- The file is in the PyTorch main repository, subject to standard code review and merge protections.
- Allowlist changes are human-readable YAML diffs and easy to spot in review.

**Residual Gap:** No automated CI check that validates allowlist changes or alerts on new entries.

**Possible Future Mitigation:** A GitHub Actions workflow that comments on PRs modifying `allowlist.yml`, tagging the infra oncall for explicit approval.

### 3.5 RISK: Secrets Synchronization

**Severity:** High (if misconfigured)
**Likelihood:** Low

The `HUD_BOT_KEY` (in AWS Secrets Manager, used by the Callback Lambda) must match `INTERNAL_API_TOKEN` (in Vercel environment, used by the HUD API). If these diverge, all callbacks are silently rejected with HTTP 401.

**Current Mitigations:**
- Both values are managed through infrastructure-as-code (Terraform for AWS, Vercel dashboard for HUD).
- The auth check uses the standard `checkAuthWithApiToken()` helper used by other HUD internal endpoints.

**Residual Gap:** No automated monitoring to detect token mismatch. A secret rotation on one side without updating the other would break the pipeline silently.

**Possible Future Mitigation:** A health-check endpoint or canary that periodically validates end-to-end auth. Alert on `HUD rejected callback: HTTP 401` in CloudWatch logs.

---

## 4. Trust Model Summary

```
┌─────────────────────────────────────────────────────────────┐
│                    TRUSTED BOUNDARY                          │
│                                                              │
│  GitHub (pytorch/pytorch)                                    │
│    │  HMAC-SHA256 signed webhook                            │
│    ▼                                                         │
│  Webhook Lambda ──► Redis (DISPATCHED state)                │
│    │  GitHub App installation token                          │
│    ▼                                                         │
│  repository_dispatch to downstream repos                    │
│                                                              │
├──────────────────── TRUST BOUNDARY ─────────────────────────┤
│                                                              │
│  Downstream CI (third-party)                                │
│    │  OIDC token (RS256, audience-scoped)                   │
│    ▼                                                         │
│  Callback Lambda                                             │
│    ├─ OIDC verification (identity)                          │
│    ├─ Allowlist check (authorization)                        │
│    ├─ Rate limiting (abuse prevention)                       │
│    ├─ State machine (lifecycle integrity)                    │
│    └─ trusted/untrusted namespace split (data separation)   │
│    │  x-hud-internal-bot token                              │
│    ▼                                                         │
│  HUD API → DynamoDB → ClickHouse → Frontend                │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Key principle:** The relay never trusts downstream-reported data for identity. OIDC provides cryptographic proof of caller identity, and `verified_repo` is the single source of truth propagated to HUD.

---

## 5. Recommendations (Prioritized)

| Priority | Recommendation | Effort | Impact |
|---|---|---|---|
| **P1** | Add CloudWatch alarm on `HUD rejected callback: HTTP 401` to detect auth token mismatches | Low | Prevents silent pipeline breakage |
| **P1** | Add CloudWatch alarm on `rate limit exceeded` to detect abuse or misconfiguration | Low | Early abuse detection |
| **P2** | Implement stale `in_progress` cleanup (scheduled Lambda scanning DynamoDB for records older than 6 hours) | Medium | Prevents permanently "running" jobs on HUD |
| **P2** | Add CI check on PRs modifying `allowlist.yml` that tags infra oncall for review | Low | Prevents accidental or malicious allowlist changes |
| **P3** | Cross-validate reported `conclusion` against GitHub Check Runs API | Medium | Detects result fabrication by compromised downstream repos |
| **P3** | Add dispatch-side nonce to fully eliminate replay window | Medium | Closes theoretical replay gap |

---

## 6. Appendix: Secret and Configuration Inventory

| Secret/Config | Location | Used By | Purpose |
|---|---|---|---|
| GitHub App private key | AWS Secrets Manager (`crcr-secret-prod`) | Webhook Lambda | Mint installation tokens for `repository_dispatch` |
| GitHub App webhook secret | AWS Secrets Manager (`crcr-secret-prod`) | Webhook Lambda | HMAC-SHA256 webhook signature verification |
| `HUD_BOT_KEY` | AWS Secrets Manager (`crcr-secret-prod`) | Callback Lambda | Authenticate to HUD API (`x-hud-internal-bot` header) |
| `INTERNAL_API_TOKEN` | Vercel environment | HUD API (`results.ts`) | Verify incoming requests from Callback Lambda |
| `REDIS_ENDPOINT` | Lambda environment variable | Both Lambdas | ElastiCache connection (TLS enforced in Lambda runtime) |
| `REDIS_LOGIN` | AWS Secrets Manager (`crcr-secret-prod`) | Both Lambdas | ElastiCache authentication |
| `ALLOWLIST_URL` | Lambda environment variable | Webhook Lambda | GitHub URL for allowlist YAML |
| `OUR_AWS_ACCESS_KEY_ID` | Vercel environment | HUD API | DynamoDB write access (HUD AWS account) |
| `OUR_AWS_SECRET_ACCESS_KEY` | Vercel environment | HUD API | DynamoDB write access (HUD AWS account) |
