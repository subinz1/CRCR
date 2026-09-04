# CRCR HUD Data Flow (Short)

Concise path from callback to pixels on [hud.pytorch.org/crcr](https://hud.pytorch.org/crcr).

## Write path

```
Downstream / Results Relay
  → authenticated callback (OIDC or relay token)
  → HUD / CRCR API
  → DynamoDB (workflow-job records)
  → automatic sync
  → ClickHouse (crcr_* tables / queries)
```

1. **Ingest** — Callback carries `event_type`, `delivery_id`, job name, conclusion, optional `workflow_run_url` / `artifact_url`.
2. **DynamoDB** — Source of truth for latest job state; nightly finalize is write-once (see `docs/write-once-guard.md`).
3. **ClickHouse** — Analytical copy used by HUD SQL (`crcr_summary`, nightly summary, per-repo dashboard, metrics).

## Read path

```
Browser → Next.js HUD pages
        → API routes / SWR
        → ClickHouse queries (filtered by event_type / pr_number)
        → React tables, chips, tooltips
```

| Surface | Typical filter |
|---------|----------------|
| Main HUD CRCR columns | L3/L4 viable jobs |
| `/crcr` summary | PR vs Nightly tabs |
| `/crcr/[org]/[repo]` | Per-repo PR or nightly matrix |
| Metrics | PR / Nightly chart tabs |

## Event separation

- PR dashboards: `pr_number > 0` (nightly rows excluded).
- Nightly dashboards: `event_type = 'nightly'` (and periodic analog where enabled).

## Failure modes operators care about

| Symptom | Likely layer |
|---------|--------------|
| Missing nightly SHA column | Callback never arrived / wrong `delivery_id` |
| Partial row at day boundary | Query window vs SHA grouping (#8695) |
| Summary ≠ matrix | Stats not derived from matrix (#8696) |
| Duplicate finalize flip | Missing write-once (#8694) |
| Artifact link missing | UI only rendering `workflow_run_url` (#8546) |

Related: `docs/architecture-nightly-self-report.md`, `docs/external-ci-results-relay.md`.
