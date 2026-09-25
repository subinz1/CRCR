# CRCR Repository Level History

Issue [pytorch/test-infra#8806](https://github.com/pytorch/test-infra/issues/8806) needs an auditable record of a downstream repository's trust-tier changes. The [history mockup](../mockups/crcr-level-history-mockup.html) places that record in a per-repository **History** view rather than the global metrics page.

## HUD integration

History is an additional, collapsible panel in the existing repository dashboard, not a replacement dashboard or a PR/nightly tab. It keeps the active page's repository header, time-range control, expanded L3 readiness panel, and current KPI cards. The history panel sits alongside the existing results matrix and supplies a decision timeline, a reliability signal, and an evidence-backed decision log.

The timeline deliberately does not overlay tier transitions and reliability in a single chart. A tier is a discrete policy state; reliability is a supporting signal evaluated over a window. Showing them separately makes it clear which value changed and why.

## Why this view

The decision record needs the same repository context as the existing PR, nightly, and metrics dashboards. A reviewer can answer four questions without leaving the page:

1. What tier is this repository at now, and since when?
2. Which level changes led here?
3. Was a decision manual, automatically promoted, or automatically demoted?
4. Which policy version, measurements, ownership checks, and source PR supported it?

The tier rail gives a readable lifecycle. The success-rate overlay gives decision context without making a chart the source of truth. The event log and evidence panel remain the audit record.

## Production record

Each immutable history row should include:

| Field | Purpose |
| --- | --- |
| `downstream_repo` | Repository whose tier changed |
| `previous_level`, `new_level` | Explicit transition; no inference from the current allowlist |
| `changed_at` | Decision timestamp |
| `change_type` | `manual`, `auto_promotion`, or `auto_demotion` |
| `policy_version` | Criteria definition that made the decision |
| `trigger_reason` | Structured criterion snapshot, including measurements and thresholds |
| `source_url` | Allowlist PR, automated verdict, or other decision evidence |
| `actor` | Human or automation identity that wrote the record |

`trigger_reason` should be structured data, not only prose, so the UI can render concise evidence while investigations can query exact thresholds and observed values.

## Proposed delivery phases

1. **Capture** — define an append-only ClickHouse audit table and write a manual allowlist-change event path. Backfill only confirmed historical changes if a reliable source exists.
2. **Query** — add parameterized per-repository history and health-overlay queries, including stable ordering and source links.
3. **HUD** — add the History tab, current-tier summary, event log, and evidence drawer to the per-repository CRCR dashboard.
4. **Automation** — make promotion/demotion agents emit policy-versioned decision events before or atomically with the allowlist update. Add criteria snapshots and links to the agent verdict.

The mock intentionally keeps automatic decisions illustrative: no current repository history is asserted until the audit store exists.
