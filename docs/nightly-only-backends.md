# Nightly-Only Backends

A nightly-only backend contributes compatibility results for scheduled PyTorch
SHAs without receiving upstream pull-request or ciflow-push dispatches.

## Intended behavior

| Surface or path | Nightly-only backend behavior |
|---|---|
| Pull Requests tab on `/crcr` | Not listed |
| Nightly tab on `/crcr` | Listed with nightly pass-rate data |
| PR webhook dispatch | Not dispatched |
| ciflow push dispatch | Not dispatched |
| Scheduled downstream workflow | Runs on the partner's cadence |
| Authenticated callback | Accepted and displayed when allowlisted |

This is different from disabling a backend. The backend remains L2 (or another
configured trust tier), retains HUD observability, and can be promoted later if
it develops PR coverage.

## Suitable candidates

- CI that depends on expensive or scarce specialized hardware
- Pipelines that build a nightly container before testing
- New partners that need observational validation before PR routing
- Providers whose native scheduler is the source of truth for runs

## Operator checklist

1. Confirm the partner reports the PyTorch SHA it actually tested as
   `delivery_id`.
2. Verify its job names and conclusions produce useful matrix cells.
3. Add explicit `events: [nightly]` metadata after parser and dispatch support
   is deployed.
4. Confirm it appears only under the Nightly summary tab.
5. Leave the partner at L2 until coverage, duration, and reliability justify a
   higher trust tier.

For payload requirements, see the [partner onboarding checklist](partner-onboarding-checklist.md).
