🟢 *CRCR Nightly: RHEL 9.6 — All Green*

Repo: <https://github.com/TorchedHat/pytorch-redhat-ci|TorchedHat/pytorch-redhat-ci>
Runner: `linux.rhel96` (self-hosted)

*Latest Runs:*
• <https://github.com/TorchedHat/pytorch-redhat-ci/actions/runs/29676377036|#26> — Jul 19 (cron) — 1h 57m — ✅ All passed
• <https://github.com/TorchedHat/pytorch-redhat-ci/actions/runs/29633174563|#25> — Jul 18 (cron) — 1h 8m — ✅ All passed
• <https://github.com/TorchedHat/pytorch-redhat-ci/actions/runs/29595271686|#24> — Jul 17 (manual) — 1h 9m — ✅ All passed

*Run #26 Jobs (Jul 19):*
```
build            76m   ✅
determine-tests  14s   ✅
cpu-tests        23m   ✅
inductor-tests   10m   ✅
sgpu-tests        3m   ✅
mgpu-tests        4m   ✅
```

*Pipeline:*
`build → determine-tests → cpu → inductor → sgpu → mgpu`

• Builds PyTorch from nightly branch source SHA on RHEL 9.6 (podman)
• Delta-based test selection (current vs previous nightly SHA)
• Uses PyTorch's `run_test.py` for all test execution
• Cron: daily at 04:00 UTC
• HUD reporting not yet enabled (pending nightly handler merge)
