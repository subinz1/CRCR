# Callback Lifecycle

CRCR callback rows describe a single downstream job attempt. The lifecycle is
small by design so the relay can safely retry network delivery without changing
the meaning of a completed result.

```
accepted → in_progress → completed
                    └── timed_out (sweeper finalization)
```

## Before persistence

The receiver establishes the trusted envelope before it accepts a payload:

1. Verify the relay token or provider OIDC assertion.
2. Derive repository identity from verified claims and allowlist mappings.
3. Validate event type, delivery identity, status, conclusion, and URLs.
4. Reject malformed or unauthorized deliveries with a diagnostic response.

Free-form job names and artifact URLs are display data; repository identity and
authorization are not taken on faith from those fields.

## State rules

| Transition | Meaning |
|---|---|
| absent → `in_progress` | work has started and may be shown as pending |
| `in_progress` → terminal | normal callback completion |
| `in_progress` → `timed_out` | zombie sweep concludes no final callback arrived |
| terminal → terminal | restricted for scheduled results to avoid late retries rewriting history |

Pull-request attempts may need different retry behavior because reruns are part
of their normal workflow. Scheduled results are keyed by the tested SHA, so a
finalized nightly must remain stable for the HUD to be trustworthy.

## Consumer expectations

DynamoDB holds the operational row; ClickHouse holds the queryable copy. HUD
surfaces should use latest-attempt logic so an earlier failure does not remain in
the denominator after a successful rerun. See [HUD data flow](hud-data-flow.md)
and [write-once guard](write-once-guard.md).
