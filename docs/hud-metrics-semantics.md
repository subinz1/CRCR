# HUD Metrics Semantics

CRCR numbers answer different questions at different levels. A correct metric
must state its event scope, attempt-selection rule, and denominator.

## Common metrics

| Metric | Unit | Key rule |
|---|---|---|
| pass rate | latest terminal job attempts | successful jobs / completed jobs |
| failures | latest terminal job attempts | explicit non-success terminal outcomes |
| nightly runs | tested PyTorch SHAs | group scheduled rows by delivery SHA |
| pending jobs | latest jobs | `in_progress`, not silently excluded |
| overdue jobs | latest pending jobs | older than timeout plus sweep grace |
| average duration | completed jobs with timing | define whether timeout duration is included |

## Summary versus detail pages

The repository dashboard should be able to explain the summary. If a summary
deduplicates by run/job/attempt while the detail table counts every stored row,
their pass rates will diverge even if each query is internally valid.

Use one eligibility window and one latest-attempt selection policy across both
surfaces. The summary may aggregate afterward; it should not invent a separate
population.

## Empty data is not success

An absent completed row must not produce a 100% pass rate. For health probes in
particular, an `in_progress` timeout candidate is valuable evidence: it tells
the operator that a finalization path may have stopped working.

When presenting a percentage, provide the numerator and denominator next to it
or in the tooltip. See [relay health-probe runbook](relay-health-probe.md).
