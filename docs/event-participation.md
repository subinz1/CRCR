# Event Participation

CRCR has two independent questions for every downstream backend:

1. **Trust level:** how deeply is the backend integrated (L1–L4)?
2. **Event participation:** which logical events should it receive or report?

Keeping these separate lets a backend be visible in the HUD at L2 without
requiring it to run for every upstream pull request.

## Supported event classes

| Event | Typical producer | Purpose |
|---|---|---|
| `pull_request` | PyTorch PR webhook | Validate an upstream change before or alongside merge |
| `nightly` | Downstream scheduled CI | Report compatibility for a PyTorch commit SHA |

Legacy allowlist entries participate in both classes so their behavior does not
change when event metadata is introduced. A backend that needs a narrower scope
declares it explicitly, for example:

```yaml
L2:
  - example-org/example-backend:
      events:
        - nightly
```

This configuration is deliberately explicit: adding a future event type must
not silently opt every existing backend into it.

## Why this matters

Scheduled-only partners often own their own build cadence, runners, or image
publishing workflow. Forwarding every PR to them wastes capacity and creates a
misleading empty row on the Pull Requests CRCR page. They can still provide
valuable compatibility signal by testing a known PyTorch SHA nightly and
self-reporting the final jobs.

## Rollout sequence

1. Deploy parsing support for event metadata while preserving legacy defaults.
2. Filter HUD summary tables by the selected event.
3. Filter webhook dispatch by the selected event.
4. Add explicit `events` metadata for a partner only after the preceding
   changes are deployed.

The sequence is important: an older parser may only understand the historical
list form of the allowlist. See [dispatch semantics](dispatch-semantics.md) and
[nightly-only backends](nightly-only-backends.md).
