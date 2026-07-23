# CRCR Success Rate Alerting — Open Questions

**Issue:** [pytorch/test-infra#8309](https://github.com/pytorch/test-infra/issues/8309)
**Context:** Action item from CRCR sync meeting (Jul 14, 2026)

---

## How In-Tree CI Alerting Works Today

| Mechanism | What it monitors | Threshold | Notification channel |
|-----------|-----------------|-----------|---------------------|
| `check_alerts.py` (cron every 5 min) | Consecutive job failures on `main` and `nightly` | ≥ 2 consecutive failing commits | GitHub Issue → Meta Butterfly/WorkChat |
| `queue_alert.py` (cron every 5 min) | Queue depth & duration | >50 queued + >30min–2h depending on machine type | GitHub Issue + `pytorch/alerting-infra` Lambda |
| `check_live_runners.py` (cron every 5 min) | Runner capacity | Min live runners per label (e.g., 12 for A100) | GitHub Issue |
| Grafana `broken_viable_strict.sql` | Jobs failing ≥ 3 consecutive commits on `main` | ≤5 jobs = "broken", >5 = "badly broken" | Grafana notification channel (external config) |
| Grafana `nightly_pipeline_failures.sql` | Nightly binary pipeline failures | Any failure in last 24h | Grafana notification channel |
| `daily_regression.py` | Test metric regressions (cost, time, success rate) | ≥ 10% change vs previous window | `pytorch/alerting-infra` Lambda → team routing |

**Key takeaway:** There is **no Slack webhook in test-infra**. Notifications go through:
1. GitHub Issues in `pytorch/test-infra` → Butterfly bot → WorkChat
2. `pytorch/alerting-infra` AWS Lambda → team-based routing
3. Grafana alert rules → notification channels configured in Grafana UI

---

## Open Questions for CRCR Alerting

### 1. What metric do we alert on?

| Option | Description |
|--------|-------------|
| **A. Rolling pass rate** | Alert when pass rate over a window drops below threshold (e.g., <80% in last 24h) |
| **B. Consecutive failures** | Alert when a repo has N consecutive failures (mirrors `check_alerts.py` pattern) |
| **C. Both** | Pass rate for trends, consecutive failures for acute breakage |

### 2. What is the "healthy range"?

- What pass rate threshold triggers an alert? (e.g., 80%? 90%? 95%?)
- Should this be configurable per downstream repo?
- Should the threshold differ by level (L3 vs L4)?

### 3. What time window?

- Rolling 24 hours?
- Rolling 7 days?
- Should we require a minimum sample size (e.g., at least 10 runs) to avoid false alerts on new repos?

### 4. Per-repo or aggregate?

- Alert per downstream repo (e.g., "pytorch/crcr-test dropped to 60%")?
- Or alert on the overall CRCR aggregate pass rate?
- Or both?

### 5. Which notification channel?

| Option | Pros | Cons |
|--------|------|------|
| **GitHub Issue** (match existing pattern) | Consistent with in-tree alerts; Butterfly/WorkChat integration already works | External contributors can't see WorkChat |
| **`pytorch/alerting-infra` Lambda** | Team-based routing already built; supports FIRING/RESOLVED states | Requires access to the Lambda URL + auth secret |
| **Grafana alert rule** | ClickHouse query already exists; built-in notification channels | Alert rules configured in Grafana UI, not source-controlled |
| **Slack webhook directly** | Simple; visible to all CRCR contributors | No precedent in test-infra; needs webhook URL management |

### 6. Who gets notified?

- dev-infra team only? (as the issue says)
- The downstream repo's oncalls (from the allowlist)?
- Both?

### 7. Alert states: FIRING vs RESOLVED?

- Should alerts auto-resolve when the rate recovers? (the `alerting-infra` Lambda supports `FIRING`/`RESOLVED` states)
- Or just fire-and-forget?

### 8. Where does the detection logic live?

| Option | Description |
|--------|-------------|
| **A. GitHub Actions cron** (like `check_alerts.py`) | Add a new job to `check-alerts.yml` or create a new workflow. Queries ClickHouse via HUD API. |
| **B. Grafana alert rule** (like `broken_viable_strict.sql`) | Add a new SQL file to `clickhouse_db_schema/grafana_alerts/`. Configure alert rule in Grafana UI. |
| **C. Lambda** | New Lambda triggered by EventBridge on a schedule. |

### 9. Dedup / flap prevention?

- How do we avoid alert storms if the rate fluctuates around the threshold?
- Cooldown period between alerts? (e.g., one alert per repo per 6 hours)
- Hysteresis? (alert at <80%, resolve at >90%)

### 10. Does this cover nightly/periodic too?

- Should nightly CI results factor into the success rate alert?
- Or should nightly have its own separate alerting?

---

## Recommendation

The simplest approach that matches existing patterns:

1. **Add a Grafana alert query** (`clickhouse_db_schema/grafana_alerts/crcr_success_rate.sql`) — we already have the `crcr_success_rate` ClickHouse query
2. **Configure a Grafana alert rule** with threshold (to be decided by WG)
3. **Route to dev-infra** via Grafana's existing notification channel

This requires zero new infrastructure and follows the same pattern as `broken_viable_strict.sql` and `nightly_pipeline_failures.sql`.
