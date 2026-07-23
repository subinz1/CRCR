# CRCR PR Review Comments

## PR #8170 — State machine key change (KarhouTam)

### 1. Bug: Missing `payload` arg in test constructor

- **File**: `aws/lambda/cross_repo_ci_relay/tests/test_redis_helper.py`
- **Where**: `test_set_callback_state_redis_exception_raises` method, `get_side_effect` function

`CallbackStateRecord(CallbackState.DISPATCHED, 1000.0)` is called with only 2 arguments, but the updated dataclass requires 3 (`state`, `timestamp`, `payload`). `payload: dict | None` has no default value, so this will raise `TypeError` at runtime. Should be `CallbackStateRecord(CallbackState.DISPATCHED, 1000.0, {})` — matching the pattern used everywhere else in this file.

### 2. Stale docstring references wrong constant

- **File**: `aws/lambda/cross_repo_ci_relay/utils/misc.py`
- **Where**: `CallbackState` docstring, `DISPATCHED` description

The docstring says `run_id=DISPATCH_CHECK_RUN_ID` but the constant was renamed to `DISPATCH_RUN_ID`. Should read:

```
DISPATCHED: webhook side, when repository_dispatch is sent (run_id=DISPATCH_RUN_ID).
```

### 3. Multi-job workflow semantic change needs documentation

- **File**: `aws/lambda/cross_repo_ci_relay/README.md`
- **Where**: State machine section

The switch from per-job (`check_run_id`) to per-workflow (`run_id:run_attempt`) keying means that if a downstream workflow has multiple jobs that independently call the CRCR callback action with `status: in_progress`, the second job's callback will be rejected with a 400 ("rejecting replay attack IN_PROGRESS"). The previous `check_run_id` keying supported this because each job had a unique ID.

If the intended contract is now "one `in_progress` + one `completed` callback per workflow run," this should be documented explicitly so downstream repos know they cannot call the callback from multiple jobs. The README currently says "Supports multiple workflows per webhook" — worth clarifying that it does NOT support multiple independent job-level callbacks within the same workflow run.

---

## PR #8198 — Zombie workflow cleaner (KarhouTam)

### 4. No defensive check for missing `payload` in zombie handler

- **File**: `aws/lambda/cross_repo_ci_relay/callback/cleanup_handler.py`
- **Where**: `_build_timeout_payload`, line `stored = state_record.payload`

`_build_timeout_payload` immediately dereferences `state_record.payload` as a dict (`stored["trusted"]`). If the payload is `None` (e.g. corrupted Redis data, or the `in_progress` callback somehow stored without a payload), this will raise `TypeError: 'NoneType' object is not subscriptable`. Consider adding a guard:

```python
if not state_record.payload:
    logger.warning("zombie state record has no stored payload, skipping")
    return None, None  # caller should handle
```

### 5. `set_callback_state` in cleanup handler omits `workflow_name`

- **File**: `aws/lambda/cross_repo_ci_relay/callback/cleanup_handler.py`
- **Where**: step 2 in the `handle` function, `redis_helper.set_callback_state(...)` call

The `set_callback_state` call doesn't pass `workflow_name`, so it defaults to `None`. This means the log line in `set_callback_state` will show `workflow_name=None`. Consider extracting the workflow name from the stored payload (`state_record.payload["untrusted"]["callback_payload"]["workflow"]["name"]`) and passing it through for better observability in logs. Minor, since the zombie flow is exceptional.

### 6. `_build_timeout_payload` mutates the stored payload dict in-place

- **File**: `aws/lambda/cross_repo_ci_relay/callback/cleanup_handler.py`
- **Where**: lines setting `stored_trusted["ci_metrics"]`, `workflow["status"]`, `workflow["conclusion"]`, `workflow["completed_at"]`

This function mutates `state_record.payload` in-place rather than making a copy. Since the dict was deserialized from Redis this is safe today, but it's fragile — if the zombie list is ever iterated more than once (e.g. retry logic), the mutations from the first pass would carry over. A `copy.deepcopy` of `stored` at the top would make this resilient.

---

## PR #8173 — Conclusion input description (can-gaa-hou)

### 7. No validation at all for `conclusion` value

- **File**: `.github/actions/cross-repo-ci-relay-callback/action.yml`
- **Where**: the removed `if status == "completed" and conclusion not in ("success", "failure")` block

The old check was too strict (blocked `cancelled`, `timed_out`, etc.), but the replacement removes ALL validation. Now any arbitrary string (including typos like `"sucess"` or nonsense like `"foobar"`) is silently accepted and forwarded to the callback Lambda. Consider keeping a lightweight allow-list of GitHub's known check-run conclusions:

```python
_VALID_CONCLUSIONS = {"success", "failure", "cancelled", "timed_out", "action_required", "neutral", "skipped", "stale"}
if status == "completed" and conclusion not in _VALID_CONCLUSIONS:
    sys.exit(f"::error::conclusion must be one of {_VALID_CONCLUSIONS}, got {conclusion!r}")
```

This gives you the broader set you need while still catching typos at the source rather than letting them propagate to HUD.

---

## PR #8119 — L3/L4 check run management (can-gaa-hou)

### 8. Unused variable `pr_number`

- **File**: `aws/lambda/cross_repo_ci_relay/webhook/event_handler.py`
- **Where**: `_handle_pr_labeled` function

`pr_number = str(pr.get("number", ""))` is declared and checked for truthiness in the guard `if not pr_number or not head_sha:`, but never used after that. Either remove the variable and the guard (the function works fine without it), or if it's intended for future logging, add that log line.

### 9. `AllowlistLevel` comparison via string `.value` is fragile

- **File**: `aws/lambda/cross_repo_ci_relay/callback/callback_handler.py` and `aws/lambda/cross_repo_ci_relay/utils/allowlist.py`
- **Where**: `if repo_level.value >= AllowlistLevel.L3.value` and `needs_check_run`

`AllowlistLevel` is a `str` enum with values `"L1"` through `"L4"`. The `>=` comparison works via lexicographic ordering, which happens to be correct for single-digit levels. But this is fragile — if a level like `"L10"` is ever added, `"L10" < "L2"` lexicographically. The TypeScript side already uses a proper numeric `LEVEL_ORDER` mapping. Consider adding a similar ordering mechanism on the Python side, or using the enum member order.

### 10. `_handle_check_run_rerequested` error response leaks details

- **File**: `aws/lambda/cross_repo_ci_relay/webhook/event_handler.py`
- **Where**: `_handle_check_run_rerequested` function

The function checks `level.value < AllowlistLevel.L3.value` to gate re-runs, which is correct. However, the error path raises `HTTPException(502)` which exposes the downstream repo name and error details to the caller. For a webhook endpoint, this may leak information. Consider returning a generic error message.

### 11. `upstream_repo` config field — is it added to `RelayConfig`?

- **File**: `aws/lambda/cross_repo_ci_relay/utils/config.py`
- **Where**: `RelayConfig` dataclass

The tests set `cfg.upstream_repo = "pytorch/pytorch"` on a MagicMock, and the production code accesses `config.upstream_repo`, `config.github_app_id`, and `config.github_app_private_key`. If `upstream_repo` is not yet a field on the `RelayConfig` dataclass (it doesn't appear to be added in this PR's config.py changes), the production code will raise `AttributeError`. Please confirm this field is added in the config PR or in the base.

---

## PR #8183 — On-call bot and allowlist (KarhouTam) [Draft]

### 12. Oncall comment dedup is per-PR, not per-commit — stale comments on new pushes

- **File**: `torchci/lib/bot/crcrOncallBot.ts`
- **Where**: `findExistingComment` and the dedup check

The `MARKER` (`<!-- crcr-oncall -->`) dedup means only ONE oncall comment is ever posted per PR. If a PR is updated with new commits and the downstream check fails again on the new commit, no new comment is posted because the marker from the old failure is still there. The oncall team could miss new failures. Consider:

- Including the `head_sha` in the marker so each commit gets its own comment, or
- Updating the existing comment body with the new failure details instead of skipping

### 13. `FAILURE_CONCLUSIONS` constant duplicated

- **File**: `torchci/lib/bot/crcrOncallBot.ts` and `torchci/lib/bot/pytorchBotHandler.ts`
- **Where**: Both files define `const FAILURE_CONCLUSIONS = new Set(["failure", "cancelled", "timed_out", "action_required"])`

Same constant defined in two places. Extract to a shared module (e.g. `torchci/lib/crcrConstants.ts` or alongside the allowlist) so they stay in sync.

### 14. L4 merge blocking scope — runs for all repos, not just pytorch/pytorch

- **File**: `torchci/lib/bot/pytorchBotHandler.ts`
- **Where**: the inserted `if (!forceRequested)` block before the `isPyTorchPyTorch` check

The L4 CRCR blocking check runs for ALL repos in the pytorch org, not just `pytorch/pytorch`. The existing CI-blocking logic below is gated by `isPyTorchPyTorch(this.owner, this.repo)`. Should the CRCR blocking check also be scoped to pytorch/pytorch only? If so, wrap it in the same guard:

```typescript
if (!forceRequested && isPyTorchPyTorch(this.owner, this.repo)) {
    const blockingRepos = await this.getCrcrBlockingFailures();
    ...
}
```

---

## Cross-PR Note

PRs #8170 (key change to `run_id:run_attempt`) and #8119 (L3/L4 check run mgmt) both modify `callback_handler.py` and `event_handler.py` with fundamentally different keying models (`run_id:run_attempt` vs `check_run_id`). Whichever merges second will need a rebase to reconcile. PR #8198 (zombie cleaner) builds on top of #8170, so it has a merge ordering dependency on #8170.
