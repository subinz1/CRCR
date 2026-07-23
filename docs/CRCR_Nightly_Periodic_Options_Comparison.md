# CRCR Nightly & Periodic CI — Options Comparison

**Purpose:** Working Group decision document for RFC-0056  
**Date:** July 2026  
**Context:** [RFC PR #98](https://github.com/pytorch/rfcs/pull/98) · [Atalman's review comment](https://github.com/pytorch/rfcs/pull/98#discussion_r3547247472)

---

## Background

CRCR currently dispatches downstream CI only on `pull_request` and `push` webhook events from `pytorch/pytorch`. To extend coverage to **nightly** and **periodic** test runs, we need a mechanism to:

1. **Trigger** downstream repos on a schedule
2. **Correlate** results back to a specific upstream commit (for HUD display)
3. **Reuse** the existing state machine (`DISPATCHED → IN_PROGRESS → COMPLETED`)

Two approaches are being discussed. This document provides a detailed comparison with all file-level changes required for each.

---

## Option A: EventBridge Cron → Lambda (Atalman's Suggestion)

### Overview

Add AWS EventBridge rules on cron schedules. When triggered, a Lambda fetches the `pytorch/pytorch` `main` HEAD SHA via GitHub API, uses the SHA as the `delivery_id` (idempotent — skips if already dispatched for that SHA), and dispatches to downstream repos using the existing `_dispatch_to_allowlist()` machinery.

```
EventBridge cron (e.g., daily 00:00 UTC)
    ↓
Lambda handler (source: crcr.scheduler)
    ↓
GET /repos/pytorch/pytorch/commits/main → SHA
    ↓
delivery_id = SHA (skip if already dispatched)
    ↓
_dispatch_to_allowlist(event_type="nightly", delivery_id=SHA)
    ↓
Downstream repo receives repository_dispatch
    ↓
(Same callback path as today)
```

### File Changes Required

#### 1. Terraform — New EventBridge Rules + Targets

**New file:** `terraform/crcr/eventbridge_nightly.tf` (or added to existing Terraform config)

```hcl
resource "aws_cloudwatch_event_rule" "crcr_nightly" {
  name                = "crcr-nightly-dispatch"
  description         = "Trigger CRCR nightly dispatch"
  schedule_expression = "cron(0 0 * * ? *)"  # midnight UTC daily
}

resource "aws_cloudwatch_event_target" "crcr_nightly_webhook" {
  rule      = aws_cloudwatch_event_rule.crcr_nightly.name
  target_id = "crcr-webhook-lambda"
  arn       = aws_lambda_function.crcr_webhook.arn
  input     = jsonencode({
    source     = "crcr.scheduler"
    event_type = "nightly"
    target_ref = "main"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_nightly" {
  statement_id  = "AllowEventBridgeNightly"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.crcr_webhook.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.crcr_nightly.arn
}

# Repeat for periodic with different schedule
resource "aws_cloudwatch_event_rule" "crcr_periodic" {
  name                = "crcr-periodic-dispatch"
  description         = "Trigger CRCR periodic dispatch"
  schedule_expression = "cron(45 0,8,16 * * ? *)"
}

resource "aws_cloudwatch_event_target" "crcr_periodic_webhook" {
  rule      = aws_cloudwatch_event_rule.crcr_periodic.name
  target_id = "crcr-webhook-lambda"
  arn       = aws_lambda_function.crcr_webhook.arn
  input     = jsonencode({
    source     = "crcr.scheduler"
    event_type = "periodic"
    target_ref = "viable/strict"
  })
}

resource "aws_lambda_permission" "allow_eventbridge_periodic" {
  statement_id  = "AllowEventBridgePeriodic"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.crcr_webhook.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.crcr_periodic.arn
}
```

#### 2. Webhook Lambda — New Scheduler Handler Path

**Modified file:** `aws/lambda/cross_repo_ci_relay/webhook/lambda_function.py`

Must add a new code path *before* the HTTP parsing, to detect EventBridge invocations:

```python
def lambda_handler(event, context):
    # NEW: Handle EventBridge scheduled invocations
    if event.get("source") == "crcr.scheduler":
        return _handle_scheduled_dispatch(event)

    # Existing HTTP webhook path below...
    method, path, body_bytes, headers = parse_lambda_event(event)
    ...
```

**New file:** `aws/lambda/cross_repo_ci_relay/webhook/scheduler_handler.py`

~100-150 lines of new code:

```python
import logging
import requests
from utils.config import get_config
from utils.misc import EventDispatchPayload
from . import event_handler

logger = logging.getLogger(__name__)

def handle_scheduled_dispatch(event: dict) -> dict:
    config = get_config()
    dispatch_type = event.get("event_type", "nightly")
    target_ref = event.get("target_ref", "main")

    # Fetch HEAD SHA from GitHub API
    sha = _fetch_head_sha(config, target_ref)

    # Idempotency: check if this SHA was already dispatched
    if _already_dispatched(config, sha, dispatch_type):
        return {"skipped": True, "reason": f"SHA {sha} already dispatched"}

    # Build synthetic payload mimicking a push event
    synthetic_payload = {
        "ref": f"refs/heads/{target_ref}",
        "after": sha,
        "repository": {"full_name": config.upstream_repo},
    }

    delivery_id = sha

    return event_handler.handle(
        config,
        payload=synthetic_payload,
        event_type=dispatch_type,
        delivery_id=delivery_id,
    )

def _fetch_head_sha(config, ref):
    token = gh_helper.get_repo_access_token(
        config.github_app_id,
        config.github_app_private_key,
        config.upstream_repo,
    )
    resp = requests.get(
        f"https://api.github.com/repos/{config.upstream_repo}/commits/{ref}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()["sha"]

def _already_dispatched(config, sha, dispatch_type):
    # Check Redis for existing DISPATCHED record with this SHA as delivery_id
    ...
```

#### 3. Webhook Lambda — Expand Event Handler

**Modified file:** `aws/lambda/cross_repo_ci_relay/webhook/event_handler.py`

```python
def handle(config, payload, event_type, delivery_id):
    if event_type == "pull_request":
        action = payload.get("action", "")
        if action not in _PULL_REQUEST_ALLOW_ACTIONS:
            return {"ignored": True}
    # NEW: nightly/periodic have no action filtering — always dispatch
    elif event_type in ("nightly", "periodic"):
        pass

    client_payload: EventDispatchPayload = { ... }
    ...
```

#### 4. Allowlist — New Nightly/Periodic Flag

**Modified file:** `pytorch/pytorch/.github/allowlist.yml` or `utils/allowlist.py`

```yaml
L2:
  - TorchedHat/pytorch-redhat-ci:
      oncalls: user1
      nightly: true
      periodic: false
```

#### 5. CloudWatch Monitoring

**New:** CloudWatch alarms for EventBridge rule invocation failures, Lambda errors on the scheduler path.

#### 6. Downstream Repos

**Modified file in each downstream repo:** `.github/workflows/crcr-ci.yml`

```yaml
on:
  repository_dispatch:
    types: [pull_request, push, nightly, periodic]
```

### Total Infrastructure Footprint

| New AWS Resources | Count |
|---|---|
| EventBridge Rules | 2 (nightly + periodic) |
| EventBridge Targets | 2 |
| Lambda Permissions | 2 |
| CloudWatch Alarms | 2-4 (invocation + error for each) |
| New Lambda code paths | 1 (scheduler_handler.py) |
| New Python dependencies | `requests` (if not already present) |

### Concerns

1. **New infrastructure to maintain.** Two EventBridge rules, Terraform config, CloudWatch alarms. When the schedule needs to change, it's a Terraform deployment — not a simple PR.
2. **GitHub API dependency.** The Lambda must call `GET /repos/pytorch/pytorch/commits/{ref}` to fetch the SHA. This adds an external API dependency (rate limits, transient failures) to the dispatch path.
3. **No visibility in pytorch/pytorch.** The nightly/periodic schedule is hidden inside AWS infrastructure. PyTorch maintainers won't see it in the Actions tab — they'd need AWS console access or CloudWatch logs.
4. **Schedule changes require Terraform.** Changing the cron schedule is an infrastructure deployment, not a code review.
5. **No manual re-trigger from GitHub UI.** Downstream teams or PyTorch maintainers can't trigger an ad-hoc nightly dispatch without AWS CLI/console access.
6. **Idempotency adds complexity.** The SHA-keyed idempotency logic (skip if already dispatched) requires additional Redis lookups and edge-case handling (what if `main` doesn't advance for days?).
7. **Dual maintenance surface.** The webhook Lambda now has two entry points (HTTP from GitHub, EventBridge from AWS), each with different input formats, auth models, and failure modes.

---

## Option B: Reuse Existing Upstream Events (Our Proposal)

### Overview

Instead of building new infrastructure, we leverage **events that already happen** in the PyTorch ecosystem:

- **Nightly:** The existing [`trigger_nightly_core.yml`](https://github.com/pytorch/test-infra/blob/main/.github/workflows/trigger_nightly_core.yml) workflow in `test-infra` already pushes a new commit to the `nightly` branch in `pytorch/pytorch` every day at `30 7 * * *` UTC. This push generates a **real GitHub `push` webhook** that the CRCR Lambda already receives. We just need the Lambda to detect `ref == refs/heads/nightly` and map it to `event_type = "nightly"`. **No new workflow, no new branch — zero changes in `pytorch/pytorch`.**

- **Periodic:** There is no existing branch-push mechanism for periodic. We add **one lightweight workflow** (`crcr_periodic_trigger.yml`) in `pytorch/pytorch` that runs on the same cron schedule as the upstream periodic CI. This workflow pushes a lightweight tag (e.g., `crcr-periodic/2026-07-10-0100`) to `pytorch/pytorch`. Tag pushes generate real `push` webhooks (with `ref: refs/tags/...`), which the Lambda already receives. The Lambda maps the tag pattern to `event_type = "periodic"`.

**No new branches. Maximum one new workflow file in `pytorch/pytorch`. No new AWS infrastructure.**

### How It Works

#### Nightly — Zero New Files

```
test-infra/trigger_nightly_core.yml (existing, runs daily at 30 7 * * *)
    ↓
git push -f origin "${NIGHTLY_COMMIT}:nightly"    ← ALREADY HAPPENING
    ↓
GitHub generates real `push` webhook:
    X-GitHub-Event: push
    X-GitHub-Delivery: <UUID>
    X-Hub-Signature-256: <valid HMAC>
    payload.ref: "refs/heads/nightly"
    payload.after: "<viable/strict HEAD SHA>"
    ↓
CRCR Webhook Lambda receives push event (existing path, no new auth)
    ↓
Lambda detects ref == "refs/heads/nightly" → maps event_type to "nightly"    ← NEW (~2 lines)
    ↓
delivery_id = X-GitHub-Delivery (from GitHub — globally unique)
    ↓
_dispatch_to_allowlist(event_type="nightly") — existing machinery, zero changes
    ↓
Downstream repos receive repository_dispatch with event_type: "nightly"
    ↓
(Same callback path as today)
```

The key insight: **the nightly push is already happening every day.** The CRCR webhook Lambda already receives this event. Right now, it dispatches it to downstream repos as `event_type: "push"`. The only change is mapping the branch name to `"nightly"` instead. Two lines of code.

#### Periodic — One New Workflow

```
pytorch/pytorch/.github/workflows/crcr_periodic_trigger.yml (NEW, cron schedule)
    ↓
git tag crcr-periodic/2026-07-10-0100 HEAD
git push origin crcr-periodic/2026-07-10-0100
    ↓
GitHub generates real `push` webhook:
    X-GitHub-Event: push
    X-GitHub-Delivery: <UUID>
    X-Hub-Signature-256: <valid HMAC>
    payload.ref: "refs/tags/crcr-periodic/2026-07-10-0100"
    payload.after: "<HEAD SHA>"
    ↓
CRCR Webhook Lambda receives push event (existing path, no new auth)
    ↓
Lambda detects ref starts with "refs/tags/crcr-periodic/" → maps to "periodic"    ← NEW (~2 lines)
    ↓
delivery_id = X-GitHub-Delivery (from GitHub)
    ↓
_dispatch_to_allowlist(event_type="periodic") — existing machinery
    ↓
Downstream repos receive repository_dispatch with event_type: "periodic"
    ↓
(Same callback path as today)
```

Tag pushes generate the same `push` webhook event type as branch pushes. The existing `_SUPPORTED_EVENTS = {"pull_request", "push"}` gate, signature verification, and repo check all work unchanged.

### Why Nightly Needs Zero New Files

The existing [`trigger-nightly` action](https://github.com/pytorch/test-infra/blob/main/.github/actions/trigger-nightly/action.yml) already does:

```bash
# From test-infra/.github/actions/trigger-nightly/action.yml (line 35-40)
HEAD_COMMIT_HASH=$(git rev-parse HEAD)
NIGHTLY_DATE=$(date +"%Y-%m-%d")
NIGHTLY_RELEASE_COMMIT=$(git commit-tree -p FETCH_HEAD HEAD^{tree} \
    -m "${NIGHTLY_DATE} nightly release (${HEAD_COMMIT_HASH})")
git push -f origin "${NIGHTLY_RELEASE_COMMIT}:nightly"
```

This pushes a commit based on `viable/strict` HEAD to the `nightly` branch **every day**. That push already generates a webhook to the CRCR Lambda. Today the Lambda treats it as a generic `push` event. With ~2 lines of code, it becomes a `nightly` dispatch.

The existing `trigger_nightly_core.yml` also has `workflow_dispatch`, so manual re-trigger is already built-in — anyone who can run that workflow also re-triggers the CRCR nightly dispatch.

### File Changes Required

#### 1. Periodic Trigger Workflow (only new file in `pytorch/pytorch`)

**New file:** `pytorch/pytorch/.github/workflows/crcr_periodic_trigger.yml`

```yaml
name: CRCR Periodic Dispatch

on:
  schedule:
    # Aligned with upstream periodic.yml (45 0,8,16 * * 1-5)
    # Offset by 15 min to ensure upstream periodic has started
    - cron: '0 1,9,17 * * 1-5'
    - cron: '0 5 * * 0,6'
  workflow_dispatch: {}

permissions:
  contents: write

jobs:
  dispatch:
    if: github.repository_owner == 'pytorch'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
        with:
          ref: viable/strict
          fetch-depth: 1

      - name: Push CRCR periodic tag
        run: |
          TAG_NAME="crcr-periodic/$(date -u +%Y%m%d-%H%M)"
          git tag "$TAG_NAME"
          git push origin "$TAG_NAME"

      - name: Cleanup old tags (keep last 30)
        run: |
          git fetch --tags
          git tag -l 'crcr-periodic/*' | sort -r | tail -n +31 | while read -r old; do
            git push origin ":refs/tags/$old" 2>/dev/null || true
          done
```

~25 lines. The workflow:
1. Checks out `viable/strict` HEAD
2. Creates a lightweight tag `crcr-periodic/YYYYMMDD-HHMM`
3. Pushes it — this generates the `push` webhook
4. Cleans up old tags (keeps last 30) to prevent tag proliferation

The `crcr-periodic/*` tag namespace won't conflict with any existing tags (releases use `v2.x.x`, CI flow uses `ciflow/periodic/*`).

#### 2. Webhook Lambda — Ref-to-Dispatch-Type Mapping

**Modified file:** `aws/lambda/cross_repo_ci_relay/webhook/lambda_function.py`

Add ref detection *after* signature verification, inside the existing `push` flow. **No new entry point, no new auth path, no new `_SUPPORTED_EVENTS` entry.**

```python
_SUPPORTED_EVENTS = frozenset({"pull_request", "push"})  # UNCHANGED

# Ref-to-dispatch-type mapping for scheduled CRCR dispatches
_CRCR_SCHEDULED_REFS = {
    "refs/heads/nightly": "nightly",
}
_CRCR_PERIODIC_TAG_PREFIX = "refs/tags/crcr-periodic/"


def lambda_handler(event, context):
    method, path, body_bytes, headers = parse_lambda_event(event)
    # ... existing path (unchanged) ...

    event_type = headers.get("x-github-event", "")
    if event_type not in _SUPPORTED_EVENTS:           # ← push is already supported
        return ...

    config = get_config()
    _verify_signature(...)                              # ← real GitHub signature, unchanged

    payload = json.loads(body_bytes)
    repo = ...
    if repo.lower() != config.upstream_repo.lower():   # ← unchanged
        return ...

    # NEW: Map scheduled refs to dispatch types (only for push events)
    if event_type == "push":
        ref = payload.get("ref", "")
        if ref in _CRCR_SCHEDULED_REFS:
            event_type = _CRCR_SCHEDULED_REFS[ref]
        elif ref.startswith(_CRCR_PERIODIC_TAG_PREFIX):
            event_type = "periodic"

    result = event_handler.handle(config, payload, event_type=event_type, delivery_id=delivery)
    return ...
```

**That's it — ~8 lines of new code.** Everything else stays the same.

#### 3. Event Handler — No Changes Required

The `handle()` function in `event_handler.py` only special-cases `pull_request` (action filtering). For `nightly` and `periodic`, there's no action to filter — the event should always be dispatched. The existing default path handles this correctly:

```python
def handle(config, payload, event_type, delivery_id):
    if event_type == "pull_request":
        action = payload.get("action", "")
        if action not in _PULL_REQUEST_ALLOW_ACTIONS:
            return {"ignored": True}
    # push, nightly, periodic: no action filtering — fall through to dispatch

    client_payload: EventDispatchPayload = {
        "event_type": event_type,      # "nightly" or "periodic" (mapped)
        "delivery_id": delivery_id,    # from X-GitHub-Delivery
        "payload": payload,            # full push webhook payload
    }
    dispatched, failed = _dispatch_to_allowlist(config=config, client_payload=client_payload)
    ...
```

No code change needed — `nightly` and `periodic` are neither `pull_request` nor need special handling.

#### 4. Downstream Repos

**Modified file in each downstream repo:** `.github/workflows/crcr-ci.yml`

```yaml
on:
  repository_dispatch:
    types: [pull_request, push, nightly, periodic]
```

+1 line per downstream repo.

### What We Do NOT Need to Change

| Component | Change Required? | Why |
|---|---|---|
| **New branches in `pytorch/pytorch`** | **No** | Nightly uses the existing `nightly` branch. Periodic uses lightweight tags. |
| **GitHub webhook signature verification** | No | Both nightly push and periodic tag push are real GitHub events with real `X-Hub-Signature-256`. |
| **`_SUPPORTED_EVENTS` gate** | No | Both events arrive as `push` — already in the supported set. The ref mapping happens *after* the gate. |
| **Delivery ID generation** | No | GitHub provides `X-GitHub-Delivery` for every webhook. Globally unique, no dedup needed. |
| **Redis state machine** | No | `DISPATCHED → IN_PROGRESS → COMPLETED` works unchanged. |
| **Callback Lambda** | No | Callbacks use `delivery_id` to find `DISPATCHED` records. Nothing changes. |
| **HUD ingestion** | No | `event_type` already flows through the pipeline. ClickHouse stores it. |
| **Terraform / AWS infrastructure** | No | No EventBridge rules, no Lambda permissions, no CloudWatch alarms. |
| **OIDC / Auth changes** | No | Real GitHub webhooks. Same auth as every other push event. |
| **GitHub API calls from Lambda** | No | SHA is in `payload.after`. No API call needed. |
| **`event_handler.py`** | No | Default path (no action filtering) handles new event types correctly. |

### Why This Is Better

| Advantage | Detail |
|---|---|
| **Zero new AWS infrastructure** | No EventBridge rules, no Terraform, no CloudWatch alarms. Nothing new to deploy, monitor, or maintain in AWS. |
| **Nightly: zero files in pytorch/pytorch** | The existing `trigger_nightly_core.yml` push to `nightly` branch already generates the webhook. Just map the branch name. |
| **~8 lines of Lambda code** | A dictionary + prefix check. Compare to Option A's ~150 LOC new handler + idempotency logic + GitHub API integration. |
| **Real GitHub webhooks** | Both nightly and periodic generate genuine `push` events with proper `X-Hub-Signature-256` and `X-GitHub-Delivery`. No synthetic payloads, no new auth paths. |
| **SHA is in the payload** | `payload.after` contains the tested commit SHA. No GitHub API call needed. No rate limit concerns. |
| **Globally unique delivery_id** | GitHub provides `X-GitHub-Delivery` for every webhook. No idempotency logic needed. |
| **Nightly manual re-trigger is free** | `trigger_nightly_core.yml` already has `workflow_dispatch`. Triggering it re-pushes to `nightly`, which re-triggers CRCR nightly. |
| **Periodic manual re-trigger** | `crcr_periodic_trigger.yml` has `workflow_dispatch` — trigger from GitHub UI. |
| **Schedule changes are PRs** | The periodic schedule lives in a workflow file, not Terraform. |
| **Proven pattern** | The `nightly` branch push is the same mechanism used for nightly builds of pytorch/pytorch, pytorch/audio, pytorch/vision, pytorch/executorch, and 10+ other repos. It's been running reliably for years. |
| **Consistent SHA** | All downstream repos receive the same SHA (from `payload.after`) and the same `delivery_id`. Cross-backend comparison is meaningful. |
| **No dual maintenance** | The webhook Lambda keeps a single entry point: HTTP POST from GitHub. No EventBridge path. |

### Addressing Atalman's Suggestions

| Atalman's Point | How Option B Handles It |
|---|---|
| **Use SHA as correlation ID** | The SHA is in `payload.after`, provided by GitHub. HUD correlates by commit SHA — `hud.pytorch.org/pytorch/pytorch/commit/<sha>`. Fully supported. |
| **Idempotent — skip if main hasn't moved** | For nightly: if `viable/strict` HEAD hasn't changed, the `trigger_nightly_core.yml` action still pushes (force-push same tree). GitHub generates a new webhook with a new `X-GitHub-Delivery`. Each dispatch is independent. If the WG wants to skip, a single `if` in the trigger workflow handles it — no Lambda-side dedup needed. |
| **No event from pytorch/pytorch** | For nightly: the push to `nightly` already happens every day — it's not a new event, it's a new interpretation of an existing one. For periodic: one lightweight tag push per schedule. |
| **HUD grouping by SHA, not pr_number=0** | Agreed. Both nightly and periodic provide the SHA in `payload.after`. HUD groups by commit SHA. No `pr_number=0` sentinel. |

---

## Option C: Authenticated Self-Report (Atalman's Latest Suggestion)

**Source:** [PR #98 comment](https://github.com/pytorch/rfcs/pull/98#issuecomment-4962790260)

### Overview

Instead of a central scheduler dispatching *to* downstream repos, each downstream repo drives its own schedule and reports results back. The relay stops being a trigger and becomes a **validating ingest endpoint**. There is no `DISPATCHED` record — the state machine precondition is dropped entirely and replaced with authorization + SHA-validity at callback time.

```
Downstream repo's own cron schedule
    ↓
Fetches pytorch/pytorch HEAD SHA (or nightly/viable-strict ref)
    ↓
Runs CI against that SHA
    ↓
Calls back to the relay with:
    - OIDC token (proves repo identity)
    - dispatch_id = pytorch/pytorch commit SHA
    - event_type = "nightly" or "periodic"
    ↓
Relay validates:
    1. OIDC token → repo is on allowlist
    2. GET /repos/pytorch/pytorch/commits/{sha} → SHA is real
    ↓
Upsert record keyed by (repo, SHA) → HUD
```

### What Changes

| Component | Change |
|---|---|
| Callback Lambda | New code path: accept callbacks without prior DISPATCHED record |
| Callback Lambda | New: GitHub API call to validate SHA + caching layer |
| Callback Lambda | New: upsert logic replacing state machine for self-reports |
| Callback Lambda | Modified: OIDC verification as sole trust anchor (currently OIDC + state machine) |
| Downstream repos | New: cron workflow that fetches upstream SHA, runs CI, calls callback |
| Webhook Lambda | No changes |
| Terraform / AWS | No changes |
| pytorch/pytorch | No changes |

### Strengths

| # | Advantage |
|---|---|
| 1 | **No trigger from pytorch/pytorch** — nothing in upstream emits an event. No new workflows, no new branches, no new tags. |
| 2 | **No new AWS infrastructure** — no EventBridge, no Terraform. |
| 3 | **Self-service schedule** — each downstream repo owns its cron. Changes are PRs to the downstream repo, not Terraform or upstream workflows. |
| 4 | **workflow_dispatch for free** — manual re-trigger of the downstream cron workflow re-runs the nightly. |
| 5 | **Coordination-free correlation** — dispatch_id is the SHA, derivable by any actor independently. |

### Concerns and Inconsistencies

| # | Concern |
|---|---|
| 1 | **State machine bypass.** Drops the `DISPATCHED → IN_PROGRESS → COMPLETED` precondition. "Upsert" is a fundamentally different model. The callback Lambda needs a new code path that skips state validation — this is a significant architectural change, not "no infrastructure." |
| 2 | **Contradiction with earlier review.** Atalman's inline review comment recommended **Option A (EventBridge)** with SHA as delivery_id, working *within* the existing dispatch model. This comment proposes **eliminating dispatch entirely** — a fundamentally different architecture. |
| 3 | **"No infrastructure" understates Lambda changes.** The comment says "No new AWS infrastructure" but requires: new callback Lambda code path, GitHub API SHA validation, SHA caching layer, upsert logic, modified OIDC trust model. The complexity shifts from AWS resources to Lambda code. |
| 4 | **Trust model weakening.** Atalman acknowledges: "this proves the SHA is real, not that CI actually ran against it." A downstream could report all-pass results for a SHA it never tested. Acceptable in a cooperative-partner model, but strictly weaker than the dispatch model where the relay controls what gets tested. |
| 5 | **No SHA alignment across backends.** Each downstream independently fetches HEAD. If `main` advances between repo A's cron and repo B's cron, they test **different commits**. Cross-backend comparison on HUD becomes fragmented. Atalman's suggestion to "pin the same stable daily ref" reintroduces coupling. |
| 6 | **Missing-run detection is silent.** Explicitly stated as a non-goal: "absence of a signal is not an error condition." This means if a downstream's cron silently breaks, nobody on the relay side knows — contradicts the zombie sweeper model built for PR/push dispatches. Two different reliability models in the same system. |
| 7 | **SHA overwrite on re-runs.** Upsert keyed by `(repo, SHA)` means if a nightly fails and is re-run against the same SHA, the new result overwrites the old one. No audit trail of previous runs. The composite key `{sha}-{YYYYMMDD}` is mentioned as optional, but it's the common case for re-runs. |
| 8 | **No timing metrics.** Without a `DISPATCHED` record, there's no `dispatched_at` timestamp. Queue time metrics (how long the downstream job waited) are lost entirely. |
| 9 | **SHA validation adds runtime dependency.** `GET /repos/pytorch/pytorch/commits/{sha}` requires GitHub API availability and token rate limits (5000 req/hr). "Cached to avoid rate limits" needs specifics — cached where? For how long? What if the cache is cold? |
| 10 | **Callback payload contract undefined.** Current callbacks carry `delivery_id`, `event_type`, PR metadata. A nightly self-report has different fields. The new payload schema is not specified. How does the relay distinguish a nightly self-report from a PR callback? |

### Implementation Effort (Estimated)

| Step | Work | Effort |
|---|---|---|
| 1. Callback Lambda upsert path | New code path: skip state machine, validate OIDC + SHA, upsert | 2 days |
| 2. SHA validation + caching | GitHub API integration + cache layer (Redis or in-memory) | 1 day |
| 3. Downstream cron workflow | New workflow in each downstream: fetch SHA, run CI, call callback | 1 day per repo |
| 4. HUD changes | Group by SHA for non-PR results | 1 day |
| 5. End-to-end testing | Test self-report flow with TorchedHat/pytorch-redhat-ci | 1 day |
| **Total** | | **~5-6 days** |

---

## Side-by-Side Comparison

| Criteria | Option A: EventBridge → Lambda | Option B: Reuse Existing Events | Option C: Authenticated Self-Report |
|---|:---:|:---:|:---:|
| **New AWS resources** | 4+ (2 rules, 2 targets, 2 permissions, alarms) | **0** | 0 |
| **New Terraform config** | ~60 lines | **0** | 0 |
| **New files in pytorch/pytorch** | 0 | **1** (periodic workflow only) | **0** |
| **New branches in pytorch/pytorch** | 0 | **0** | 0 |
| **Webhook Lambda changes** | ~150 LOC (new handler + GitHub API + idempotency) | **~8 LOC** (ref mapping dict) | 0 |
| **Callback Lambda changes** | 0 | **0** | ~200 LOC (upsert path + SHA validation + caching) |
| **New auth paths** | None (EventBridge is trusted) | **None** (real GitHub webhook) | Modified (OIDC as sole trust anchor, no state machine) |
| **Security surface change** | New Lambda entry point | **None** | Weakened (self-reported results, no dispatch verification) |
| **State machine** | **Preserved** (DISPATCHED → IN_PROGRESS → COMPLETED) | **Preserved** | **Bypassed** (upsert replaces state machine) |
| **Operational visibility** | CloudWatch logs (AWS console) | **GitHub Actions tab** (web UI) | Downstream repo Actions tab |
| **Manual re-trigger (nightly)** | Lambda console/CLI | **Already built-in** (trigger_nightly_core has workflow_dispatch) | Downstream workflow_dispatch |
| **Manual re-trigger (periodic)** | Lambda console/CLI | **GitHub UI** (workflow_dispatch) | Downstream workflow_dispatch |
| **Schedule changes** | Terraform deployment | **Git PR** (periodic) / already managed (nightly) | PR to each downstream repo |
| **SHA availability** | Must fetch via GitHub API | **In webhook payload** (payload.after) | Must fetch via GitHub API (per downstream) |
| **Delivery ID** | Must generate (SHA or composite) | **Provided by GitHub** (X-GitHub-Delivery) | SHA (self-declared) |
| **Idempotency logic** | Required (Redis check for duplicate SHA) | **Not needed** (each push/tag = new delivery) | Upsert (overwrites previous result for same SHA) |
| **SHA alignment across backends** | **Guaranteed** (single dispatch) | **Guaranteed** (single webhook) | Not guaranteed (each repo fetches independently) |
| **Missing-run detection** | Zombie sweeper works | **Zombie sweeper works** | Explicitly not supported |
| **Timing metrics** | Full (dispatched_at → completed_at) | **Full** | Partial (no dispatched_at) |
| **Schedule reliability** | EventBridge 99.99% SLA | GitHub cron best-effort* | GitHub cron best-effort (per downstream) |
| **Existing precedent** | Zombie sweeper (EventBridge → callback Lambda) | **Nightly triggers** (git push → nightly branch) | None in CRCR |
| **Maintenance surface** | AWS + Lambda + Terraform | **GitHub workflow file only** | Each downstream repo independently |
| **Implementation effort** | ~5 days | **~2 days** | ~5-6 days |

*\*Schedule reliability: The existing `trigger_nightly_core.yml` has been running on GitHub `schedule:` cron for years across 13+ repos. In practice, skipped runs are rare and always recovered on the next schedule hit. For nightly, this is a non-issue because we piggyback on the existing trigger — no new cron dependency.*

---

## Implementation Timeline — Option B

| Step | Work | Effort |
|---|---|---|
| 1. Lambda ref mapping | Add `_CRCR_SCHEDULED_REFS` dict + tag prefix check in `lambda_function.py` | 0.5 day |
| 2. Periodic workflow | Create `crcr_periodic_trigger.yml` in pytorch/pytorch | 0.5 day |
| 3. Downstream workflow update | Add `nightly`, `periodic` to dispatch types | 0.5 day |
| 4. End-to-end testing | Test with TorchedHat/pytorch-redhat-ci and pytorch/crcr-test | 0.5 day |
| **Total** | | **~2 days** |

No Terraform, no AWS console, no CloudWatch setup, no new Lambda dependencies, no new branches.

---

## Implementation Timeline — Option A

| Step | Work | Effort |
|---|---|---|
| 1. Terraform config | EventBridge rules, targets, permissions for nightly + periodic | 1 day |
| 2. Lambda scheduler handler | New handler: GitHub API SHA fetch, idempotency check, synthetic payload | 1.5 days |
| 3. CloudWatch monitoring | Alarms for invocation failures, Lambda errors | 0.5 day |
| 4. Allowlist nightly/periodic flags | Add opt-in config per repo | 0.5 day |
| 5. Downstream workflow update | Add `nightly`, `periodic` to dispatch types | 0.5 day |
| 6. End-to-end testing | Test full EventBridge → Lambda → downstream → callback path | 1 day |
| **Total** | | **~5 days** |

---

## Summary of All Changes Per Option

### Option A — Files Changed/Added

| File | Repo | Type | Lines |
|---|---|---|---|
| `terraform/crcr/eventbridge_nightly.tf` | test-infra | **New** | ~50 |
| `aws/lambda/.../webhook/lambda_function.py` | test-infra | Modified | +10 |
| `aws/lambda/.../webhook/scheduler_handler.py` | test-infra | **New** | ~120 |
| `aws/lambda/.../utils/allowlist.py` | test-infra | Modified | +20 |
| CloudWatch alarm config (Terraform) | test-infra | **New** | ~30 |
| Downstream `.github/workflows/crcr-ci.yml` | each downstream | Modified | +1 line |
| **Total new code** | | | **~230 lines** |

### Option B — Files Changed/Added

| File | Repo | Type | Lines |
|---|---|---|---|
| `.github/workflows/crcr_periodic_trigger.yml` | pytorch/pytorch | **New** | ~25 |
| `aws/lambda/.../webhook/lambda_function.py` | test-infra | Modified | +8 |
| Downstream `.github/workflows/crcr-ci.yml` | each downstream | Modified | +1 line |
| **Total new code** | | | **~35 lines** |

---

### Option C — Files Changed/Added

| File | Repo | Type | Lines |
|---|---|---|---|
| `aws/lambda/.../callback/lambda_function.py` | test-infra | Modified | +50 (new self-report code path) |
| `aws/lambda/.../callback/self_report_handler.py` | test-infra | **New** | ~120 (SHA validation, upsert, caching) |
| `aws/lambda/.../utils/sha_validator.py` | test-infra | **New** | ~40 (GitHub API SHA check + cache) |
| Downstream `.github/workflows/crcr-nightly.yml` | each downstream | **New** | ~50 (cron + CI + callback) |
| **Total new code** | | | **~260 lines + ~50 per downstream** |

---

## Open Questions for WG

1. **State machine: preserve or replace?** Option B preserves the existing state machine unchanged. Option C replaces it with upsert for nightly/periodic. Do we want two different models (state machine for PR/push, upsert for nightly/periodic) in the same callback Lambda?

2. **SHA alignment: required or optional?** If different backends test different SHAs in the same nightly window, the HUD nightly view becomes fragmented. Options A and B guarantee alignment (single dispatch). Option C does not.

3. **Missing-run detection: needed?** Options A and B benefit from the zombie sweeper (stuck runs are detected). Option C explicitly drops this. Is silent cron failure in a downstream repo acceptable?

4. **Trust model: relay-controlled or self-reported?** Options A and B have the relay control what gets dispatched. Option C accepts self-reported results where the relay can verify the SHA is real but not that CI actually ran against it.

5. **Timing metrics: important?** Options A and B provide `dispatched_at` for queue time calculations. Option C loses this metric. Does the WG need queue time data for nightly/periodic?

6. **Re-run audit trail:** Options A and B create independent dispatch records per run. Option C's upsert overwrites the previous result for the same SHA. Is an audit trail of multiple runs against the same SHA needed?

---

## Recommendation

**Option B** is the simpler, more practical choice:

- **~7x less code than Option A** (~35 lines vs ~230 lines), **~8x less than Option C** (~35 vs ~260+)
- **Zero new AWS infrastructure** — no EventBridge, no Terraform, no CloudWatch
- **Preserves the state machine** — no architectural changes to the callback Lambda
- **Zero new branches** — nightly reuses the existing `nightly` branch, periodic uses lightweight tags
- **Only 1 new file** in `pytorch/pytorch` (the periodic workflow)
- **Nightly is essentially free** — we're just reinterpreting a webhook event that already arrives at the Lambda every day
- **Real GitHub webhooks** — no synthetic payloads, no new auth, no security boundary changes
- **Guaranteed SHA alignment** — all backends get the same SHA from the same webhook
- **~2 days to implement** vs ~5 days for Option A vs ~5-6 days for Option C

Option A builds new AWS infrastructure to solve a problem that the existing webhook pipeline already handles naturally. Option C shifts complexity to the callback Lambda and weakens the trust model. Option B just maps a branch name to a dispatch type — two lines of code.
