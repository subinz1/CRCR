# Weekly Report: July 13 – July 21, 2026

## Summary

High-velocity week focused on three major CRCR workstreams: (1) landing the nightly CI pipeline end-to-end on RHEL 9.6, (2) expanding HUD integration with new pages and main-grid visibility, and (3) hardening reliability across the stack. Also contributed code reviews, filed bugs in peer repos, and advanced the Nightly/Periodic RFC implementation.

---

## Key Accomplishments

### 1. CRCR Nightly CI Pipeline (TorchedHat/pytorch-redhat-ci)

- **Landed RHEL 9.6 nightly workflow** — full pipeline: build → determine-tests → cpu/inductor/sgpu/mgpu jobs (PR #4)
- **Integrated TorchTalk** for structural C++ call-graph analysis alongside heuristic test selection (PR #5)
- **Added L1 build & sanity test workflow** with self-hosted `linux.rhel96` runner (PR #3)
- **Debugged and fixed 6 sequential nightly failures**: invalid test names, TorchTalk timeout, stderr pollution, invalid `run_test.py` arguments, job timeout tuning, CUDA driver mismatch
- **Added `CONTINUE_THROUGH_ERROR=True`** and per-command pass/fail summary to all test jobs
- **Fixed `test_overrides` CUDA crash** by setting `CUDA_VISIBLE_DEVICES=""` for CPU/inductor jobs

### 2. HUD Integration (pytorch/test-infra)

| PR | Title | Status |
|---|---|---|
| #8285 | Add CRCR results to main HUD grid with monsterization | Merged |
| #8302 | Add nightly/periodic callback handler (Phase 1) | Merged |
| #8303 | Add delivery-id and event-type inputs to callback action (Phase 2) | Merged |
| #8304 | Add SHA validator for nightly/periodic callbacks (Phase 1.2) | Merged |
| #8318 | Add metrics page with success-rate graphs | Merged |
| #8319 | Add downstream repo summary page with stats | Merged |
| #8330 | Align downstream repo page UI with main HUD style | Merged |
| #8340 | Exclude crcr-test from main HUD grid | Merged |
| #8341 | Fix client-side crash on CRCR pages after idle | Merged |
| #8343 | Only show L3/L4 repos on main HUD grid | Merged |

### 3. Code Reviews (6 PRs)

- `pytorch/crcr-test#12` — Handle deleted push dispatches
- `pytorch/crcr-test#13` — Fix push-deleted health report timing
- `pytorch/crcr-test#14` — Only run CRCR on merged/labeled PRs
- `pytorch/crcr-test#15` — Merge-bot landing detection followup
- `pytorch/test-infra#8292` — Update default zombie timeout
- `pytorch/rfcs#100` — RFC: rename OOT trigger label to ciflow/crcr

### 4. Bug Filing & Maintainer Work (TorchedHat/torch-test-optimizer)

Filed 5 issues after a comprehensive code review:
- #6: README CLI reference out of sync
- #7: `is_running_in_container()` resource leak + podman blind spot
- #8: File handle leak in `ShardRunner.start()`
- #9: Monitor new-failure detection logic bug
- #10: `sys.path.insert` pollution

### 5. Other

- Filed `pytorch/test-infra#8326`: Multi-issuer OIDC support for Buildkite in `jwt_helper`
- Filed `pytorch/crcr-test#17`: Track event_type column addition to ClickHouse
- Updated `TorchedHat/pytorch-redhat-ci` README to reflect current pipeline state

---

## Metrics (Jul 13–21)

| Metric | Count |
|--------|-------|
| Commits | 96 |
| Pull Requests | 15 |
| Issues Filed | 13 |
| Code Reviews | 9 |
| Repos Contributed To | 5 |

---

## Next Week Priorities

1. **Merge remaining open PRs** — #8341 (idle crash fix), #8343 (L3/L4 filter)
2. **Re-enable callback reporting** in nightly workflow once Phase 2 PR (#8303) is deployed
3. **Create periodic workflow** in `TorchedHat/pytorch-redhat-ci`
4. **Add `event_type` column** to ClickHouse schema for nightly/periodic distinction
5. **Address remaining TorchTalk timeout** — C++ structural analysis hangs on full PyTorch; investigate snapshotting or depth limits
6. **RFC 98 updates** — Incorporate nightly/periodic replay & recovery section feedback
