# CRCR Documentation Map

This directory records the operating contracts behind the Cross-Repository CI
Relay (CRCR) and its HUD surfaces. It is complementary to the interactive
mockups in [`../mockups/`](../mockups/).

## Start here

| Need | Read |
|---|---|
| Understand the persistence and HUD path | [HUD data flow](hud-data-flow.md) |
| Add a downstream partner | [Partner onboarding checklist](partner-onboarding-checklist.md) |
| Send externally authenticated results | [External CI Results Relay](external-ci-results-relay.md) |
| Understand a scheduled result | [Authenticated nightly self-report](architecture-nightly-self-report.md) |
| Interpret relay health | [Health-probe runbook](relay-health-probe.md) |

## Event participation and routing

- [Event participation](event-participation.md) explains which backends take
  part in pull-request versus nightly reporting.
- [Dispatch semantics](dispatch-semantics.md) maps upstream webhook inputs to
  downstream dispatches.
- [Nightly-only backends](nightly-only-backends.md) describes the intended HUD
  experience for a backend that self-reports scheduled work only.
- [Callback lifecycle](callback-lifecycle.md) covers the state transitions from
  `in_progress` through finalized result rows.

## Operations and policy

- [Observability contract](observability-contract.md)
- [HUD metrics semantics](hud-metrics-semantics.md)
- [Incident triage](incident-triage.md)
- [Partner operator runbook](partner-operator-runbook.md)
- [Promotion readiness](promotion-readiness.md)
- [Repository level-history design](level-history-design.md)
- [Release checklist](release-checklist.md)
- [Write-once guard](write-once-guard.md)
- [xFail / xCancel policy notes](xfail-xcancel-policy-notes.md)

Documentation describes intended behavior. The deployed implementation and the
linked PyTorch RFCs remain authoritative when they differ.
