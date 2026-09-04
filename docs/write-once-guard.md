# DynamoDB Write-Once Guard for Nightly Callbacks

Nightly and periodic CRCR callbacks go through a multi-step lifecycle (`in_progress` → `completed`). Without a write-once guard, a late retry or duplicate finalize can overwrite a finished DynamoDB row and corrupt HUD history.

## Problem

For scheduled event types (`nightly`, `periodic`), the natural primary key is the pytorch commit SHA (via `delivery_id`), not a PR number. Partners and self-report workflows can legitimately send multiple callbacks for the same SHA:

1. Initial `in_progress` when the suite starts
2. Final `completed` when jobs finish
3. Accidental re-runs or double-fires of the finalize step

If finalize is applied twice, HUD can show flipped conclusions, lost durations, or mixed job sets for the same nightly SHA.

## Write-once rule

Tracked in [test-infra#8676](https://github.com/pytorch/test-infra/issues/8676) (state-machine validation) and implemented by [test-infra#8694](https://github.com/pytorch/test-infra/pull/8694) (write-once guard for nightly/periodic finalization).

Intended behavior:

- Allow transition from empty / `in_progress` → `completed`
- Reject (or no-op) a second `completed` write for the same nightly/periodic identity
- Keep PR (`pull_request`) callback semantics unchanged — retries still need to update the latest attempt

## What HUD consumers get

Once finalize is sealed:

- Nightly matrix rows for a SHA stay stable across Lambda retries
- Summary stats derived from matrix data (see related nightly fixes) are not silently rewritten
- Operators can trust that a green nightly SHA did not get clobbered by a late duplicate callback

## Related work

| Item | Role |
|------|------|
| [#8676](https://github.com/pytorch/test-infra/issues/8676) | State-machine validation for nightly/periodic callbacks |
| [#8694](https://github.com/pytorch/test-infra/pull/8694) | Write-once guard on DynamoDB finalization |
| [#8695](https://github.com/pytorch/test-infra/pull/8695) | Nightly dashboard partial rows at time-window boundary |
| [#8696](https://github.com/pytorch/test-infra/pull/8696) | Nightly summary stats from matrix data |

## Operator tip

If a nightly SHA truly needs a correction after finalize, treat it as an exceptional ops action (new delivery identity or explicit admin path) rather than re-posting the same `completed` callback.
