# External CI Results Relay

External partners (for example Spyre nightly via TorchedHat / `torch-spyre`) do not write directly to the PyTorch CRCR DynamoDB table. They post results to a **Results Relay**, which authenticates the caller and forwards into the CRCR / HUD path.

## High-level flow

```
Partner GHA workflow
  → mint OIDC token (audience scoped to the relay)
  → POST /results  (JSON job payload)
       → Results Relay Lambda
            · verify OIDC / JWKS
            · allowlist check
            · validate payload
       → receiver workflow (e.g. TorchedHat/pytorch-redhat-ci)
            · optional PUSH_TO_HUD
       → CRCR callback / HUD
            · DynamoDB → ClickHouse → hud.pytorch.org/crcr
```

This keeps partner secrets out of pytorch/pytorch while still showing partner nightly health next to first-party CRCR backends.

## Identity and dedup

- **OIDC**: no long-lived API keys; repo identity comes from token claims.
- **Allowlist**: only registered partner repos may deliver.
- **`delivery_id`**: for nightly/periodic HUD rows, prefer the **pytorch commit SHA** so the HUD can group partner jobs onto the correct nightly column.
- **`job_name` / `workflow_name`**: drive HUD grouping and tooltips; slash-prefixed names work well with slash-based grouping mockups.

## `workflow_run_url` vs `artifact_url`

RFC HUD pages distinguish two outbound links:

| Field | Intended link | Typical use |
|-------|---------------|-------------|
| `workflow_run_url` | Downstream CI run page | "View workflow run" |
| `artifact_url` | Downstream-hosted logs / artifacts | "View artifacts" |

Historically the callback action and DynamoDB extract path accepted `artifact_url`, and ClickHouse selected it, but the per-repo dashboard UI often only rendered `workflow_run_url` (see [test-infra#8546](https://github.com/pytorch/test-infra/issues/8546)). Partners who only populate `workflow_run_url` still get a useful link; partners who also send `artifact_url` should expect a separate "View artifacts" affordance once the HUD tooltip renders it (see `mockups/artifact-url-tooltip-mockup.html`).

## Practical guidance for partners

1. Mint OIDC with the relay audience; do not share static tokens.
2. Set `delivery_id` to the pytorch nightly SHA under test.
3. Prefer stable, human-readable `job_name` values (`suite / case`).
4. Populate `workflow_run_url` always; add `artifact_url` when logs live outside the workflow run page.
5. Treat relay failures as best-effort — never gate the partner pipeline on HUD delivery.

See also: `docs/partner-onboarding-checklist.md`.
