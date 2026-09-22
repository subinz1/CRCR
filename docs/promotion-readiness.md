# Promotion Readiness

Trust-tier promotion is an operational decision, not a dashboard-color change.
The relay should collect enough evidence at a lower tier before it asks PyTorch
authors to rely on a downstream result.

## Tier intent

| Tier | Integration intent |
|---|---|
| L1 | dispatch/onboarding validation |
| L2 | HUD-visible observational reporting |
| L3 | non-blocking PR check when explicitly requested |
| L4 | blocking merge prerequisite |

## Evidence to collect

- sustained pass rate over a declared evaluation window
- stable and explainable job naming/matrix coverage
- reliable callback authentication and SHA alignment
- reasonable duration and timeout behavior
- clear partner ownership and on-call contacts
- demonstrated rerun and incident-triage process

## Promotion review questions

1. Does the result represent the requested PyTorch commit and event?
2. Can an author reach logs or artifacts from the HUD cell?
3. Are failures actionable by a known partner contact?
4. Has the backend handled transient infrastructure outages without corrupting
   its reporting history?
5. Would a false negative or delayed result impose an acceptable cost at the
   proposed tier?

A nightly-only L2 backend can build excellent observational history without
being a candidate for L3 until it adds PR-event participation.
