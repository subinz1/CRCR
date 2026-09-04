Weekly Report: PyTorch CRCR (Cross-Repository CI Relay)
Period: September 1 – September 4, 2026

Summary: Short early-September window closing out nightly HUD fixes, L3 readiness review, and partner relay docs/mockups. Emphasis on accurate README status and operator-facing documentation.

Highlights:

- L3 readiness panel (#8693) — Review and mockup alignment for Criterion / Target / 14d promotion / 7d demotion columns with Promotion/Demotion chips on /crcr. Collapsed-by-default Details expansion remains the UX default.

- Nightly summary stack (#8695 / #8696 / #8697) — Boundary partial-row fix, matrix-derived summary stats, and crcr-test exclusion from the nightly summary table moved through review.

- Write-once guard (#8694) — Finalize-once semantics for nightly/periodic DynamoDB rows continued review against #8676 state-machine expectations.

- PR matrix / timeout follow-ups — Open work on latest-SHA job reporting for PR matrices (#8730) and max execution time calculation excluding timed-out jobs (#8707).

- Results Relay / Spyre — Documented partner delivery expectations: OIDC, `delivery_id` = pytorch SHA, slash-friendly job names, optional `artifact_url` alongside `workflow_run_url`.

- Docs & mockups (this repo) — L3 readiness and slash-prefix grouping mockups; write-once, Results Relay, and xfail policy notes; weekly reports brought current.

Open at period end: #8693, #8694–#8697, #8730, #8707, #8676, #8623.

RFC: pytorch/rfcs#98 (RFC-0056) — cleanup in progress / comments addressed as HUD nightly path stabilizes.
