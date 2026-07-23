# CRCR Nightly: RHEL 9.6 — Status Report

**Repo:** [TorchedHat/pytorch-redhat-ci](https://github.com/TorchedHat/pytorch-redhat-ci)
**Workflow:** `CRCR Nightly: RHEL 9.6 Build & Test`
**Runner:** `linux.rhel96` (self-hosted)

## Latest Runs (all passing)

| Run | Trigger | Date (UTC) | Duration | Result |
|-----|---------|------------|----------|--------|
| [#26](https://github.com/TorchedHat/pytorch-redhat-ci/actions/runs/29676377036) | cron | Jul 19, 2026 | 1h 57m | **All green** |
| [#25](https://github.com/TorchedHat/pytorch-redhat-ci/actions/runs/29633174563) | cron | Jul 18, 2026 | 1h 8m | **All green** |
| [#24](https://github.com/TorchedHat/pytorch-redhat-ci/actions/runs/29595271686) | manual | Jul 17, 2026 | 1h 9m | **All green** |

## Run #26 Breakdown (Jul 19 — latest cron)

| Job | Duration | Status |
|-----|----------|--------|
| build | 76m | ✅ |
| determine-tests | 14s | ✅ |
| cpu-tests | 23m | ✅ |
| inductor-tests | 10m | ✅ |
| sgpu-tests | 3m | ✅ |i wan
| mgpu-tests | 4m | ✅ |

## Pipeline Architecture

```
build → determine-tests → cpu-tests → inductor-tests → sgpu-tests → mgpu-tests
```

- **Build**: Builds PyTorch from `pytorch/pytorch` nightly branch source SHA inside a RHEL 9.6 container (podman)
- **determine-tests**: Computes delta between current and previous nightly SHA, selects targeted tests via `targeted_tests.py`, falls back to full suite
- **Test jobs**: Run sequentially on the same self-hosted runner; categorized into CPU, Inductor, single-GPU, and multi-GPU

## Key Facts

- Tests run against `pytorch/pytorch` nightly HEAD source SHA (extracted from the nightly release commit message)
- Delta-based test selection reduces test time when changes are incremental
- All test execution uses PyTorch's standard `run_test.py` runner
- No results sent to HUD yet (callback steps removed until nightly handler lands)
- Cron schedule: daily at 04:00 UTC
