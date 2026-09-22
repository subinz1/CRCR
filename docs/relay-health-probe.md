# Relay Health-Probe Runbook

`pytorch/crcr-test` is a deliberate fault-injection backend. Its jobs prove
that CRCR can dispatch, receive callbacks, normalize terminal outcomes, and
surface the result on the HUD.

## Expected probe outcomes

| Probe family | Expected final outcome | What it verifies |
|---|---|---|
| normal | `success` | ordinary dispatch and callback delivery |
| xfail | `failure` | intentional failure propagation |
| xcancel | `cancelled` | cancellation propagation |
| xtimeout | `timed_out` | timeout finalization by the zombie sweeper |

The x-prefixed outcomes are expected successes for the **health probe only**;
they are not a general rule for partner CI. See
[xFail / xCancel policy notes](xfail-xcancel-policy-notes.md).

## The zombie-sweeper signal

An `xtimeout` job begins as `in_progress`. If no terminal callback arrives, the
zombie sweeper should finalize it as `timed_out`. A terminal-only health query
has a blind spot: a broken sweeper leaves the job `in_progress` forever, so it
vanishes from the denominator instead of failing the health card.

The health query therefore retains latest `in_progress` rows and separates two
states:

- **Awaiting sweep:** the job is younger than the configured timeout plus the
  sweeper grace period.
- **Overdue:** the job has exceeded that window and degrades relay health.

The current deployment uses the callback's six-hour default timeout. The HUD
adds a short grace period for the periodic sweep rather than declaring a job
unhealthy at the exact timeout boundary.

## Operator response

1. Open the health card details and identify the affected run, job, and age.
2. Check callback and sweeper logs for the delivery identity.
3. Confirm the job has not already completed under a later attempt.
4. Fix the sweeper or callback path; do not simply exclude the stale row.
5. Verify a new `xtimeout` probe reaches `timed_out` after the configured
   timeout.

One completed probe alone is not sufficient evidence: the timeout probe is the
specific check for the finalization path.
