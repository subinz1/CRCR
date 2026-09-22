# CRCR status: Sep 15–21, 2026

## Focus

- Closed a health-observability blind spot for a timeout probe left permanently
  `in_progress` when zombie sweeping fails.
- Made it possible to configure L2 backends as nightly-only without exposing
  them as unavailable PR integrations.
- Continued documenting the authenticated partner-results path and its HUD
  operating model.

## Health visibility

[test-infra#8801](https://github.com/pytorch/test-infra/pull/8801) updates the
health query to retain the latest non-terminal probe rows. The HUD can now show
the difference between work awaiting the sweep and a job overdue for
finalization. [#8834](https://github.com/pytorch/test-infra/pull/8834) adds a
details view for that triage information.

## Event participation stack

The event-participation work is intentionally split into deployable layers:

1. [#8854](https://github.com/pytorch/test-infra/pull/8854) parses explicit
   allowlist event metadata while retaining historical defaults.
2. [#8855](https://github.com/pytorch/test-infra/pull/8855) filters the CRCR
   summary by the selected tab's event.
3. [#8856](https://github.com/pytorch/test-infra/pull/8856) filters relay
   dispatch using the same participation data.
4. [pytorch#197864](https://github.com/pytorch/pytorch/pull/197864) configures
   selected L2 backends for nightly reporting after the test-infra stack is
   deployed.

## Follow-up

- Watch CI and review feedback for the health and event-participation stacks.
- Validate that nightly-only backends remain visible in Nightly while absent
  from Pull Requests.
- Keep partner callback failures diagnosable without letting telemetry outages
  hide pipeline failures.
