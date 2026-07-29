Weekly Report: PyTorch CRCR (Cross-Repository CI Relay)
Period: July 21 - July 28, 2026

Summary: Major week focused on HUD improvements, nightly CI data layer, pass rate accuracy fixes, and RHEL nightly pipeline stabilization. Also completed 3 code reviews for external CRCR contributors and advanced the nightly tab UI design with mockups.

Highlights:

HUD Dashboard Improvements (5 PRs merged) — Redesigned the per-repo CRCR dashboard page to match the main HUD visual style with commit/author columns and PR-level row grouping (#8330). Added "Healthy"/"Degraded" health badge to the summary page, replacing raw percentages (#8366). Filtered CRCR columns on the main HUD to only show L3/L4 repos (#8343), excluded the crcr-test health-probe repo from the grid (#8340). Fixed a client-side crash on all CRCR pages caused by useSWR fetcher not throwing on non-200 responses after idle (#8341).

Nightly/Periodic Data Layer (PR #8353, under review) — Added event_type column (defaulting to 'pull_request') to the crcr_workflow_job ClickHouse schema, updated the write path in crcrUtils.ts to extract and persist event_type from callback payloads, and added pr_number > 0 filters to all five PR-related queries to prevent nightly/periodic rows from polluting PR dashboards. This is the data layer foundation for RFC-0056 (CRCR Nightly & Periodic CI).

Nightly Tab UI (PR #8377, draft) — Created event-type tabs (Pull Requests | Nightly) on the CRCR summary page. Built a new crcr_nightly_summary ClickHouse query filtering on event_type = 'nightly' with latest SHA tracking. Implemented the tab UI with repo count badges, nightly results table with SHA links to pytorch/pytorch commits, and empty state for when no nightly data exists. Depends on #8353.

Pass Rate Accuracy Fix (PR #8376, under review) — Fixed pass rate calculation for pytorch/crcr-test by counting xfail/xcancel/xtimeout jobs (intentional probe outcomes) as successes instead of failures. Updated three ClickHouse queries (crcr_summary, crcr_success_rate, crcr_backend_summary) with the corrected logic, scoped to pytorch/crcr-test only. Fixed SQLFLUFF CI failure for line length violations on the same day.

RHEL Nightly CI Stabilization (TorchedHat/pytorch-redhat-ci) — Increased all four test job timeouts (cpu, inductor, sgpu, mgpu) from 10h to 24h to handle full test suite runs. Added 30-minute per-command timeout to prevent individual hanging tests from blocking entire jobs. Fixed exit code 127 in test summary steps where shell metacharacters in error output were being interpreted as commands. Updated README with current timeout configuration and corrected script names.

Code Reviews (3 completed) — Reviewed #8386 by @KarhouTam (oncall bot cross-fork PR fix): identified unreachable Search API fallback due to else-if chain bug, missing trailing comma causing PYFMT CI failure, and empty-PR format issue; all addressed by author across 3 iterations. Reviewed #8183 by @KarhouTam (oncall bot implementation): flagged dedup logic issue where single MARKER per-PR could silently drop notifications for multiple failing backends. Reviewed pytorch/crcr-test#19 by @can-gaa-hou (oot-to-crcr rename): requested documentation of the x-prefix naming convention in README.

Nightly Display Design & Mockups (subinz1/CRCR, 30 commits) — Created standalone nightly tab design mockup using the Page-Level Tabs approach selected from 16 explored options. Populated all 16 design option mockups with live CRCR summary page data. Added cross-linked index page for easy navigation across all mockup pages.

Merged PRs: #8330 (per-repo UI redesign), #8340 (exclude crcr-test), #8341 (idle crash fix), #8343 (L3/L4 filter), #8366 (Healthy/Degraded badge) + ~10 direct pushes to TorchedHat/pytorch-redhat-ci for nightly fixes.

Open PRs: #8353 (event_type schema), #8376 (pass rate fix), #8377 (nightly tab UI)

RFC: RFC-0056 (CRCR Nightly & Periodic CI) — pytorch/rfcs#98, open
