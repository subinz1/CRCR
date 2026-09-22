# Dispatch Semantics

The relay treats upstream webhook delivery and downstream result reporting as
different directions. Allowlist event participation applies to **dispatch**;
it does not discard authenticated callbacks for a configured downstream repo.

## Upstream inputs

| Input | Logical CRCR event | Target selection |
|---|---|---|
| `pull_request` webhook | `pull_request` | L1+ repos participating in pull requests |
| Push carrying an OOT ciflow label | `pull_request` | Same PR-participating set; used for dispatch compatibility |
| `pull_request.labeled` for an L3 label | `pull_request` | Matching L3 backend that participates in pull requests |
| Partner's schedule | `nightly` | No PyTorch webhook dispatch; partner self-reports later |

The push route is treated as pull-request participation because it is an
alternate transport for PR-triggered out-of-tree work, not a new scheduled
event class.

## L3 labels

L3 has an additional label-to-repository mapping. Before creating an
`in_progress` check run from `pull_request.labeled`, CRCR verifies both:

1. the label maps to an L3 backend; and
2. that backend participates in `pull_request`.

This prevents an accidental PR check for a nightly-only backend.

## Scheduled results

For a downstream nightly, PyTorch does not dispatch a GitHub event. The
downstream workflow obtains the commit SHA, builds or tests it, and posts an
authenticated callback. The callback is grouped by SHA in the HUD Nightly view.

See [event participation](event-participation.md) for configuration and
[authenticated nightly self-report](architecture-nightly-self-report.md) for
the result path.
