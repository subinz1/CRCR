Weekly Report: PyTorch CRCR (Cross-Repository CI Relay)
Period: August 25 – September 1, 2026

Summary: Focus week on nightly HUD correctness, DynamoDB finalize safety, L3 readiness groundwork, and external Results Relay (RHEL / Spyre) plumbing. RFC-0056 cleanup continued in parallel.

Highlights:

- Nightly HUD stability — Investigated partial nightly rows at time-window boundaries and summary stats that disagreed with the visible matrix. Follow-on fixes landed as PRs for boundary handling (#8695), computing summary stats from matrix data (#8696), and hiding the crcr-test probe from the nightly CI summary table (#8697).

- Write-once finalize guard — Designed DynamoDB write-once behavior for nightly/periodic finalization so duplicate `completed` callbacks cannot clobber a sealed SHA (#8694, related state-machine discussion in #8676).

- L3 readiness — Advanced fixed-window promotion/demotion criteria (14d promote / 7d demote) toward a per-repo readiness panel and /crcr index chips (#8693, issues #8554 / #8552). Tenure wiring via `crcr_repo_tenure` kept in sync with the panel.

- Merged hardening earlier in the window — Retry dedup using run_id partition (#8555) reduced double-counting in CRCR queries; metrics page PR/Nightly tabs (#8538) and summary sentence split (#8537) already on main.

- External CI / RHEL–Spyre — Continued Results Relay path for partner nightlies (OIDC → TorchedHat receiver → CRCR → HUD). Clarified `workflow_run_url` vs `artifact_url` so original workflow links and artifact links stay distinct (#8546 territory + tooltip mockup).

- RFC — RFC-0056 (pytorch/rfcs#98) cleanup: nightly/periodic semantics, authenticated self-report path notes, and alignment with HUD event_type tabs already merged (#8353 / #8377).

- Policy — Open discussion on long-term xfail/xcancel treatment beyond the crcr-test-only pass-rate carve-out (#8623).

Merged (recent context): #8555, #8538, #8537, #8468, #8453, plus earlier nightly data-layer PRs (#8353, #8377, #8376).

In progress / open: #8693 (L3 readiness), #8694 (write-once), #8695–#8697 (nightly summary/matrix), #8676 (state machine), #8623 (xfail policy).
