# CRCR Observability Contract

The HUD is only useful when operators can explain where a result came from and
which layer is responsible when it is missing. CRCR retains enough identity to
trace a displayed cell back to a downstream workflow attempt.

## Required diagnostic fields

| Field | Operator use |
|---|---|
| downstream repository | find ownership and allowlist configuration |
| event type | distinguish PR, nightly, and periodic views |
| delivery ID | group scheduled jobs by tested PyTorch SHA |
| run ID and attempt | distinguish reruns from independent jobs |
| job and workflow name | understand matrix grouping |
| status and conclusion | separate pending from terminal outcomes |
| started/completed time | investigate latency and zombies |
| workflow/artifact URLs | navigate from HUD to primary evidence |

## Read-model rule

The operational store can contain several attempts for the same logical job.
Analytical HUD queries should select the latest attempt before calculating
success rates, failure counts, or durations. Otherwise a rerun contributes both
its superseded result and its final result.

## Explainability path

```
HUD cell → query row → delivery/run/job identity → callback log → downstream run
```

Each arrow should be navigable or searchable without guessing from a job title.
If a new callback field cannot participate in that path, it should not silently
become a dashboard metric.

See [HUD metrics semantics](hud-metrics-semantics.md) and
[incident triage](incident-triage.md).
