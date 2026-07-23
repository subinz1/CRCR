# Introducing Cross-Repository CI Relay: Scalable CI Across the PyTorch Ecosystem

**TL;DR:** PyTorch now has a Cross-Repository CI Relay (CRCR) that automatically triggers and tracks CI in downstream repositories whenever a PR is opened or a commit is pushed against `pytorch/pytorch`. Results flow back to the [PyTorch CI HUD](https://hud.pytorch.org/crcr), giving maintainers a single dashboard for both in-tree and cross-repository CI health — without requiring downstream repos to build custom integrations.

*Joseph Groenenboom, Jewel K M, Subin George, Karhou Tam, Thanh Ha (Linux Foundation)*

## The Problem: Blind Spots in PyTorch CI

PyTorch sits at the center of a large ecosystem. Hardware backends like Intel XPU, AMD ROCm, Apple MPS, and Qualcomm AI Engine maintain their own repositories with custom operator implementations and kernels. Ecosystem projects like vLLM, SGLang, and Hugging Face Transformers depend on PyTorch as a foundational library. Even within PyTorch itself, some backends are partially in-tree (like CPU architecture-specific code) and rely on CI that runs outside the main test suite.

Until now, these downstream repositories had no standard way to:

1. **Know when to test** — Maintainers relied on polling or manual triggers to discover upstream changes that might break their code.
2. **Report results back** — Even when downstream repos ran CI against upstream PRs, the results lived in separate dashboards, invisible to PyTorch core reviewers.
3. **Correlate failures** — A PyTorch PR that breaks three downstream projects produced three independent failure signals with no unified view.

This created a coordination gap: PyTorch maintainers couldn't see downstream breakage before merging, and downstream teams couldn't easily signal regressions to upstream.

## The Solution: Cross-Repository CI Relay

The Cross-Repository CI Relay (CRCR) closes this gap with a fully automated pipeline that connects upstream PyTorch events to downstream CI and routes results back to the PyTorch CI HUD.

**How it works in 30 seconds:** A PyTorch PR triggers the relay. The relay dispatches to all registered downstream repos. Those repos run their CI and report back via an authenticated callback. The results appear on the PyTorch HUD within seconds.

## Participation Levels

The relay uses a tiered allowlist to support incremental onboarding and differentiated access. Downstream repos progress through levels as they mature:

| Level | Dispatch | Callback to HUD | Description |
|---|---|---|---|
| **L1** | Yes | No | Receive dispatches only (notification tier) |
| **L2** | Yes | Yes | Full pipeline: dispatch + HUD reporting |
| **L3** | Yes | Yes | Adds a non-blocking check run on the upstream PR (triggered via `ciflow/oot/<name>` label) |
| **L4** | Yes | Yes | Adds a blocking check run on the upstream PR (auto-triggered for every PR); reserved for critical accelerators |

**Use cases by level:**

- **L1 (Notify):** A new backend starting integration — receives dispatch events to trigger CI, but doesn't report back yet. Useful for validating that the dispatch pipeline works before committing to full reporting.
- **L2 (Report):** An ecosystem project like vLLM running compatibility checks against upstream PRs. Results appear on the CRCR HUD dashboard, giving PyTorch maintainers visibility into downstream health.
- **L3 (Signal):** A mature backend that wants upstream PR reviewers to see its CI status directly in the GitHub PR checks tab. Non-blocking — the check run is informational and doesn't prevent merging.
- **L4 (Gate):** A critical downstream project where upstream breakage has production impact. The check run blocks merging if it fails. Requires oncall contacts for triage.

L3 and L4 are reserved for future capabilities as the system matures and the community defines promotion criteria. The requirements for advancing to each level are detailed in [RFC-0050](https://github.com/pytorch/rfcs/blob/master/RFC-0050-Cross-Repository-CI-Relay-for-PyTorch-Out-of-Tree-Backends.md).

## End-to-End Architecture

![CRCR Architecture Flow](/assets/images/crcr_architecture_flow.png)
*Figure 1: End-to-end data flow from a PyTorch PR through the relay to the CI HUD.*

> **Note:** The architecture diagram above reflects all review feedback: left-to-right flow, single Redis instance, Webhook Lambda inside the PyTorch Infrastructure boundary, unified data store colors, callback arrows routed through the Callback Lambda as sole entry point, async/dashed arrow for DynamoDB Streams, and a complete legend including the HUD frontend.

| Component | Technology | Purpose |
|---|---|---|
| Webhook Lambda | Python 3.12, AWS Lambda | Receive GitHub webhooks, fan out dispatches |
| Callback Lambda | Python 3.12, AWS Lambda | Verify OIDC, enforce state machine, forward to HUD |
| Redis | Amazon ElastiCache (TLS) | State machine, allowlist cache, rate limiting |
| HUD API | Next.js on Vercel | Receive relay data, write to DynamoDB |
| DynamoDB | `torchci-oot-workflow-job` table | Primary storage for downstream CI records |
| ClickHouse | `default.oot_workflow_job` table | Analytics queries for HUD frontend |
| Replicator | AWS Lambda (DynamoDB Streams) | Real-time DynamoDB → ClickHouse replication |
| Callback Action | Composite GitHub Action | OIDC minting + payload delivery for downstream repos |

The system has five stages:

**Stage 1: Webhook Reception.** When a pull or push event occurs on `pytorch/pytorch`, GitHub sends a signed webhook to the Webhook Lambda. The Lambda verifies the HMAC-SHA256 signature, confirms the event originates from the upstream repository, and loads the tiered allowlist.

**Stage 2: Fan-Out Dispatch.** The Lambda sends a `repository_dispatch` event to every allowlisted downstream repository in parallel, carrying the full PR context (SHA, PR number, action). A `DISPATCHED` state is recorded in Redis with a timestamp, which later enables queue-time measurement.

**Stage 3: Downstream CI Execution.** Each downstream repository runs its CI workflow — building against the PR's commit SHA and executing its test suite. The workflow uses a composite GitHub Action ([`cross-repo-ci-relay-callback`](https://github.com/pytorch/test-infra/tree/main/.github/actions/cross-repo-ci-relay-callback)) to report status at two points: `in_progress` when the job starts, and `completed` with the conclusion when it finishes.

**Stage 4: Authenticated Callback.** Each callback carries a GitHub OIDC token — a short-lived RS256 JWT that cryptographically proves which repository sent it. The Callback Lambda verifies this token, checks the allowlist, enforces rate limits, validates the state machine, and forwards the result to HUD.

**Stage 5: HUD Persistence and Display.** The HUD API writes the record to DynamoDB. A DynamoDB Stream triggers the ClickHouse replicator, which lands the data in ClickHouse for the frontend to query. The result appears on `hud.pytorch.org/crcr` within seconds.

All secrets (GitHub App keys, HUD bot token, Redis credentials) are stored in AWS Secrets Manager. Redis connections use TLS in the Lambda runtime. The Webhook and Callback Lambdas run in a dedicated PyTorch-owned AWS account, separate from the HUD's Vercel-linked AWS account.

## What Downstream Repos Need to Do

The integration burden on downstream repos is minimal. A repository needs:

1. Be added to the [allowlist](https://github.com/pytorch/pytorch/blob/main/.github/allowlist.yml) (a one-line YAML entry).
2. Add a workflow file that listens to `repository_dispatch` events.
3. Use the composite callback action to report `in_progress` and `completed`.

Here's a minimal downstream workflow:

```yaml
name: PyTorch CI
on:
  repository_dispatch:
    types: [pull_request]

permissions:
  id-token: write

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: pytorch/test-infra/.github/actions/cross-repo-ci-relay-callback@main
        with:
          status: in_progress

      - uses: actions/checkout@v4
      - name: Run tests
        id: tests
        run: |
          # Your build and test logic here
          echo "outcome=success" >> "$GITHUB_OUTPUT"

      - if: always()
        uses: pytorch/test-infra/.github/actions/cross-repo-ci-relay-callback@main
        with:
          status: completed
          conclusion: ${{ steps.tests.outputs.outcome }}
          test-results: '{"passed": 42, "failed": 0, "skipped": 3}'
```

No callback URLs to configure, no secrets to manage, no custom authentication code. The action handles OIDC token minting, payload construction, and delivery.

For a step-by-step onboarding guide and a working reference implementation, see the [CRCR onboarding documentation](https://github.com/pytorch/crcr-test).

## Security Model

Accepting CI results from external repositories into PyTorch's infrastructure requires careful security design. The relay enforces five stages of validation before any data reaches the HUD.

![CRCR Security Stages](/assets/images/crcr_security_stages.png)
*Figure 2: Every callback passes through five security stages before reaching the HUD.*

### Security Stage 1: OIDC Identity Verification

The callback action mints a GitHub OIDC token with audience `pytorch-cross-repo-ci-relay`. The Callback Lambda verifies this token against GitHub's public JWKS endpoint using RS256. The `repository` claim in the token is cryptographically bound to the calling repository — a workflow in `org/repo-a` cannot produce a token claiming to be `org/repo-b`.

This is the foundation of the trust model: **the relay never trusts self-reported identity**. The OIDC-verified `verified_repo` is the single source of truth.

### Security Stage 2: Allowlist Authorization

The allowlist is a YAML file in `pytorch/pytorch`, controlled by PyTorch maintainers. Repositories must be explicitly listed at **participation level L2 or higher** to have their callback results accepted. The allowlist supports four participation levels (L1–L4), enabling differentiated access as the system evolves.

```yaml
L1:
  - org/backend-dispatch-only
L2:
  - org/backend-with-hud-reporting
L4:
  - org/trusted-backend: oncall1, oncall2
```

### Security Stage 3: Rate Limiting

A per-repository sliding-window rate limiter prevents any single downstream repo from flooding the pipeline. The rate limiter is **fail-closed**: if Redis is unreachable, callbacks are rejected (HTTP 500) rather than allowed through unchecked.

### Security Stage 4: State Machine Validation

The relay maintains a three-state lifecycle in Redis for every dispatch:

![CRCR State Machine](/assets/images/crcr_state_machine.png)
*Figure 3: Valid and invalid state transitions enforced by the relay.*

The state machine guarantees:
- **No callbacks without dispatch**: A downstream repo cannot inject results for a PR event that was never relayed.
- **No duplicates**: Replaying the same `in_progress` or `completed` callback is rejected.
- **No skipped states**: `COMPLETED` without a prior `IN_PROGRESS` is rejected.
- **Per-job tracking**: Each job execution gets its own `check_run_id` (GitHub-assigned, not controllable by the workflow), supporting multi-job workflows.

### Security Stage 5: Data Separation

The relay forwards data to HUD in two explicit namespaces:

```json
{
  "trusted": {
    "verified_repo": "org/backend-repo",
    "downstream_repo_level": "L2",
    "ci_metrics": { "queue_time": 1.23, "execution_time": 45.6 }
  },
  "untrusted": {
    "callback_payload": {
      "workflow": {
        "status": "completed",
        "conclusion": "success",
        "name": "CI",
        "test_results": { "passed": 42, "failed": 0, "skipped": 3 }
      }
    }
  }
}
```

The `trusted` block contains relay-generated fields that HUD can rely on. The `untrusted` block contains the downstream's self-reported data. HUD uses `trusted.verified_repo` for attribution and displays `untrusted.callback_payload.workflow` as informational.

### Known Limitations

A compromised maintainer of an allowlisted repo can forge conclusion values in future callbacks — for example, reporting `success` for a failing CI run. The impact is limited to **displaying incorrect data on the HUD**; this cannot affect PyTorch's build infrastructure, inject code into upstream, or influence merge decisions (unless the repo is at a future gating tier).

Mitigations:

- The `verified_repo` field always identifies the true caller (OIDC-guaranteed).
- Misbehaviour is observable in HUD data and CloudWatch logs.
- The offending repo can be removed from the allowlist, immediately revoking access.

Cross-validating reported conclusions against the GitHub Check Runs API is a planned future enhancement.

## CI Metrics: Queue Time and Execution Time

The relay computes two timing metrics from its state machine timestamps:

- **Queue time**: Time between `DISPATCHED` (webhook sends `repository_dispatch`) and `IN_PROGRESS` (downstream job starts). This measures GitHub Actions queue delays.
- **Execution time**: Time between `IN_PROGRESS` and `COMPLETED`. This measures actual CI execution duration.

These metrics are forwarded to HUD in the `trusted.ci_metrics` block and displayed on the dashboard, giving infrastructure teams visibility into both platform-level queuing and per-backend test performance.

## The HUD Dashboard

The CRCR results are displayed on the PyTorch CI HUD at [`hud.pytorch.org/crcr`](https://hud.pytorch.org/crcr):

- **Summary page** (`/crcr`): Aggregated pass rates, job counts, and average execution times across all downstream repos over the last 14 days.
- **Repo dashboard** (`/crcr/{org}/{repo}`): Per-PR matrix view showing individual job results, test counts, and execution times for a specific downstream repository.

The dashboard uses the same ClickHouse-backed query infrastructure as the rest of the PyTorch CI HUD, ensuring consistent performance and familiar UX for maintainers.

## Getting Started

If you maintain a PyTorch backend, ecosystem project, or any downstream repository that depends on PyTorch and want to integrate with CRCR:

1. **Request allowlist addition**: Open a PR to add your repository to [`pytorch/pytorch/.github/allowlist.yml`](https://github.com/pytorch/pytorch/blob/main/.github/allowlist.yml).
2. **Add the workflow**: Copy the minimal workflow template above into your repository's `.github/workflows/` directory.
3. **Ensure permissions**: The workflow must declare `permissions: id-token: write` for OIDC token minting.
4. **Verify on HUD**: Once your first dispatch completes, check [`hud.pytorch.org/crcr`](https://hud.pytorch.org/crcr) for your results.

For step-by-step onboarding and a working reference implementation, see the [CRCR onboarding documentation](https://github.com/pytorch/crcr-test). For the full design, see [RFC-0050](https://github.com/pytorch/rfcs/blob/master/RFC-0050-Cross-Repository-CI-Relay-for-PyTorch-Out-of-Tree-Backends.md) and [RFC-0054](https://github.com/pytorch/rfcs/blob/master/RFC-0054-HUD-Integration-for-Out-of-Tree-CI-Results.md).

## What's Next

- **Extended conclusion values**: Supporting `cancelled` and `timed_out` conclusions alongside `success` and `failure`, for richer status reporting.
- **Stale job cleanup**: A scheduled job to detect and mark `in_progress` records that never received a completion callback.
- **L3/L4 check run management**: Surfacing downstream CI status directly on upstream PRs for qualifying repos.
- **Push event support**: Extending dispatch beyond pull request events to cover post-merge CI on the main branch.

## Acknowledgements

CRCR was designed and implemented as a collaboration between the PyTorch Foundation infrastructure team and the Linux Foundation. We'd like to thank the reviewers and infrastructure engineers who helped shape the system: @malfet, @albanD, @atalman, @jathu, @zxiiro, @FFFrog, @KarhouTam and @can-gaa-hou for architectural design and development, infrastructure deployment and operational support.

---

*For questions or feedback, reach out on the [PyTorch Dev Infra discussion forum](https://github.com/pytorch/test-infra/discussions) or file an issue in [pytorch/test-infra](https://github.com/pytorch/test-infra/issues).*
