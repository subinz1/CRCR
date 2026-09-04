# Architecture: Authenticated Nightly Self-Report

Nightly / periodic CRCR no longer depends on pytorch/pytorch opening a PR. Downstream (or a partner relay) **self-reports** results for a known pytorch commit SHA using the authenticated callback path.

## Actors

| Actor | Responsibility |
|-------|----------------|
| Downstream CI | Builds/tests against a pytorch nightly SHA; mints OIDC; posts callbacks |
| Callback action | Packages `delivery_id`, `event_type`, job fields, optional URLs |
| CRCR / HUD API | Verifies relay token / OIDC path; writes DynamoDB |
| ClickHouse sync | Mirrors workflow-job rows for HUD queries |
| HUD UI | Nightly tab + per-repo matrix keyed by SHA |

## Identity model

- **`event_type`**: `nightly` or `periodic` (not `pull_request`)
- **`delivery_id`**: pytorch commit SHA under test (groups all jobs for that nightly)
- **`pr_number`**: absent or `0` — PR dashboards filter these out (`pr_number > 0`)

Schema foundation: [test-infra#8353](https://github.com/pytorch/test-infra/pull/8353). Handler / validator phases: [#8302](https://github.com/pytorch/test-infra/pull/8302), [#8303](https://github.com/pytorch/test-infra/pull/8303), [#8304](https://github.com/pytorch/test-infra/pull/8304).

## Lifecycle

```
in_progress  →  completed (finalize)
                     │
                     └─ write-once guard (#8694 / #8676)
                        blocks duplicate finalize for same identity
```

1. Downstream starts suite → `in_progress` callback (optional but useful for pending cells).
2. Jobs finish → `completed` callback with conclusions, durations, URLs.
3. Finalize seals the DynamoDB item for that SHA + repo (+ job identity as implemented).
4. HUD nightly queries read ClickHouse rows for `event_type = 'nightly'`.

## Trust boundary

Self-report is still **authenticated**:

- First-party CRCR uses the relay / callback allowlist path.
- External partners may enter via Results Relay (OIDC → allowlisted receiver → CRCR). See `docs/external-ci-results-relay.md`.

Untrusted payload fields (logs URLs, free-text names) are stored for display; trusted fields (repo identity, event type) come from verified claims / allowlist mapping.

## HUD surfaces

- Summary **Nightly** tab ([#8377](https://github.com/pytorch/test-infra/pull/8377))
- Per-repo nightly matrix (SHA columns)
- Metrics Nightly tab ([#8538](https://github.com/pytorch/test-infra/pull/8538))

RFC reference: [pytorch/rfcs#98](https://github.com/pytorch/rfcs/pull/98) (RFC-0056).
