# CRCR Incident Triage

Start with the user-visible symptom, then follow the identity of the affected
delivery rather than scanning unrelated dashboard data.

| Symptom | First checks | Likely owner |
|---|---|---|
| backend missing from PR page | event participation, trust tier, PR label | relay configuration |
| backend missing from Nightly page | delivery SHA, callback acceptance, event type | partner or callback receiver |
| red cell has no useful link | workflow/artifact URL in callback row | partner workflow/UI |
| pass rate differs across pages | time window and latest-attempt selection | HUD query |
| timeout probe stays pending | callback logs and sweeper age | relay operations |
| duplicate nightly result changes | delivery identity and finalize guard | callback/state machine |

## Minimal incident record

Record these before making a configuration change:

- downstream repository and trust level
- event type and delivery ID
- workflow run ID, attempt, and job name
- first-seen time and current row status
- expected versus actual HUD surface
- a sanitized link to the workflow or artifact

## Avoid false fixes

Do not solve a missing result by broadening an allowlist, removing a failed row,
or marking a stale job as successful without establishing the root cause. Those
actions turn a diagnostic signal into a silent data-quality problem.

Use [observability contract](observability-contract.md) for the trace path and
[relay health-probe runbook](relay-health-probe.md) for sweeper-specific cases.
