# xfail / xcancel Policy Notes

Tracking issue: [test-infra#8623](https://github.com/pytorch/test-infra/issues/8623) — *Address how we will treat xfail and xcancel going forward*.

## Current behavior (crcr-test only)

[test-infra#8376](https://github.com/pytorch/test-infra/pull/8376) taught pass-rate queries to treat expected non-success outcomes as successes **for `pytorch/crcr-test` only**:

- `xfail`
- `xcancel`
- `xtimeout`

Those conclusions are intentional probe outcomes in the CRCR health-probe repo: the suite is designed to exercise failure / cancel / timeout paths without marking the relay itself unhealthy.

Queries touched for the scoped fix include:

- `crcr_summary`
- `crcr_success_rate`
- `crcr_backend_summary`

Other downstream repos still count those conclusions as non-success for HUD pass-rate math unless a broader policy lands.

## Why the special case exists

`pytorch/crcr-test` is an L2 health probe, not a product CI suite. A "successful" probe day can include deliberate failures. Without the x-prefix carve-out, the summary page permanently shows CRCR itself as degraded.

## Open questions for #8623

1. **Generalize beyond crcr-test?** Should any L2/L3 partner opt into x-prefix semantics via allowlist metadata, or stay probe-only forever?
2. **HUD presentation** — Keep green pass-rate but still show red job cells for xfail rows? Or render a distinct chip so operators see intentional vs accidental failure?
3. **Nightly vs PR** — Apply the same rule to `event_type = nightly|periodic`, or only PR dashboards?
4. **Naming contract** — Formalize that only the `x` prefix (not free-form conclusions) is recognized, and document it for partners.
5. **Alerting** — Should oncall bots ignore x-prefix failures the same way pass-rate does?

## Interim recommendation

Until #8623 closes:

- Keep the **crcr-test-only** success reinterpretation.
- Do not teach partner suites to emit `xfail`/`xcancel` expecting green pass rates.
- Document any new probe conclusions in `pytorch/crcr-test` README before relying on them in queries.
