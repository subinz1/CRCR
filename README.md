# CRCR

All the files and mock-ups related to the HUD changes for CRCR (Cross-Repository CI Relay).

**Live mockups**: [subinz1.github.io/CRCR](https://subinz1.github.io/CRCR/)

**RFC**: [RFC-0056: CRCR Support for Nightly & Periodic CI](https://github.com/pytorch/rfcs/pull/98)

## Mockups

Interactive HTML mockups for the CRCR HUD integration. These mockups demonstrate the UI designs implemented in the `pytorch/test-infra` PRs.

| Page | Description | Related PR |
|------|-------------|------------|
| [Main HUD Grid](mockups/oot-hud-mockup.html) | CRCR columns on main HUD with L3/L4 filtering | [#8285](https://github.com/pytorch/test-infra/pull/8285) |
| [PR Workflow Boxes](mockups/oot-hud-mockup-pr-workflows.html) | CRCR backends as workflow boxes on PR page | [#8247](https://github.com/pytorch/test-infra/pull/8247) |
| [PR View (Legacy)](mockups/oot-hud-mockup-pr.html) | Original accordion-style CRCR display | [#8247](https://github.com/pytorch/test-infra/pull/8247) |
| [CRCR Summary](mockups/oot-hud-mockup-crcr-summary.html) | Summary page with stat cards and L4-L1 sections | [#8220](https://github.com/pytorch/test-infra/pull/8220) |
| [Per-Repo Dashboard](mockups/oot-hud-mockup-crcr-backend.html) | Downstream repo page with commit/author columns | [#8319](https://github.com/pytorch/test-infra/pull/8319), [#8330](https://github.com/pytorch/test-infra/pull/8330) |
| [Nightly Results](mockups/oot-hud-mockup-crcr-nightly.html) | Nightly CI results for downstream repos | [#8353](https://github.com/pytorch/test-infra/pull/8353) |
| [Periodic Results](mockups/oot-hud-mockup-crcr-periodic.html) | Periodic CI results (6-hour cadence) | [#8353](https://github.com/pytorch/test-infra/pull/8353) |
| [Nightly Tab Design](mockups/crcr-summary-nightly-design.html) | Nightly tab on CRCR summary page (Option A) | [#8377](https://github.com/pytorch/test-infra/pull/8377) |
| [Display Options](mockups/crcr-nightly-display-options.html) | 16 design options (A–P) for nightly display | Design exploration |
| [L3 Readiness Panel](mockups/l3-readiness-panel-mockup.html) | Promotion/demotion criteria with 14d / 7d columns and chips | [#8693](https://github.com/pytorch/test-infra/pull/8693) |
| [Slash-Prefix Job Grouping](mockups/job-grouping-slash-prefix.html) | Group jobs by left-hand segment before `/` | Design exploration |
| [Artifact URL Tooltip](mockups/artifact-url-tooltip-mockup.html) | Render "View artifacts" when `artifact_url` is set | [#8546](https://github.com/pytorch/test-infra/issues/8546) |
| [Metrics Page Tabs](mockups/crcr-metrics-tabs-mockup.html) | PR / Nightly tabs on CRCR metrics page | [#8538](https://github.com/pytorch/test-infra/pull/8538) |
| [Summary Sentence](mockups/crcr-summary-sentence-mockup.html) | Separate Pull Requests and Nightly HUD links | [#8537](https://github.com/pytorch/test-infra/pull/8537) |

## Reports

Weekly status reports summarizing CRCR development progress.

| Report | Period |
|--------|--------|
| [Jul 21–28](reports/weekly-status-jul21-28.md) | Merged 5 PRs, 3 code reviews, RHEL nightly stabilization |

## Implementation Status

### Merged PRs

| PR | Title |
|----|-------|
| [#8220](https://github.com/pytorch/test-infra/pull/8220) | CRCR Summary page with stat cards |
| [#8244](https://github.com/pytorch/test-infra/pull/8244) | Move CRCR link to top-level navbar |
| [#8247](https://github.com/pytorch/test-infra/pull/8247) | CRCR workflow boxes on PR page |
| [#8285](https://github.com/pytorch/test-infra/pull/8285) | CRCR columns on main HUD grid |
| [#8302](https://github.com/pytorch/test-infra/pull/8302) | Nightly/periodic callback handler (Phase 1) |
| [#8303](https://github.com/pytorch/test-infra/pull/8303) | delivery-id / event-type inputs on callback action |
| [#8304](https://github.com/pytorch/test-infra/pull/8304) | SHA validator for nightly/periodic callbacks |
| [#8318](https://github.com/pytorch/test-infra/pull/8318) | CRCR Metrics page |
| [#8319](https://github.com/pytorch/test-infra/pull/8319) | Per-repo downstream dashboard |
| [#8330](https://github.com/pytorch/test-infra/pull/8330) | PR-based grouping for downstream page |
| [#8341](https://github.com/pytorch/test-infra/pull/8341) | Fix idle crash on CRCR pages |
| [#8343](https://github.com/pytorch/test-infra/pull/8343) | Filter HUD grid to L3/L4 only |
| [#8353](https://github.com/pytorch/test-infra/pull/8353) | event_type column for nightly/periodic |
| [#8366](https://github.com/pytorch/test-infra/pull/8366) | Healthy/Degraded display on summary page |
| [#8376](https://github.com/pytorch/test-infra/pull/8376) | Treat xfail/xcancel/xtimeout as success (crcr-test) |
| [#8377](https://github.com/pytorch/test-infra/pull/8377) | Nightly tab on CRCR summary page |
| [#8386](https://github.com/pytorch/test-infra/pull/8386) | Fix PR search for CRCR check runs |
| [#8453](https://github.com/pytorch/test-infra/pull/8453) | Multi-issuer OIDC support for Buildkite |
| [#8468](https://github.com/pytorch/test-infra/pull/8468) | Move Buildkite repo mappings to ci_providers.yml |
| [#8537](https://github.com/pytorch/test-infra/pull/8537) | Split summary description with PR and Nightly links |
| [#8538](https://github.com/pytorch/test-infra/pull/8538) | PR/Nightly tabs on metrics page |
| [#8555](https://github.com/pytorch/test-infra/pull/8555) | Fix query double-counting via run_id partition |

### Recent / In progress

| PR / Issue | Title | Status |
|------------|-------|--------|
| [#8693](https://github.com/pytorch/test-infra/pull/8693) | L3 promotion/demotion readiness panel (14d / 7d windows) | Open |
| [#8694](https://github.com/pytorch/test-infra/pull/8694) | Write-once guard for nightly/periodic finalize | Open |
| [#8695](https://github.com/pytorch/test-infra/pull/8695) | Fix nightly dashboard partial rows at window boundary | Open |
| [#8696](https://github.com/pytorch/test-infra/pull/8696) | Nightly summary stats from matrix data | Open |
| [#8697](https://github.com/pytorch/test-infra/pull/8697) | Hide crcr-test from nightly CI summary table | Open |
| [#8730](https://github.com/pytorch/test-infra/pull/8730) | PR matrix: report jobs for latest commit SHA only | Open |
| [#8707](https://github.com/pytorch/test-infra/pull/8707) | Max execution time excludes timed-out jobs | Open |
| [#8676](https://github.com/pytorch/test-infra/issues/8676) | State-machine validation for nightly/periodic callbacks | Open |
| [#8623](https://github.com/pytorch/test-infra/issues/8623) | Long-term xfail / xcancel policy | Open |

## Related Repositories

| Repo | Description |
|------|-------------|
| [pytorch/test-infra](https://github.com/pytorch/test-infra) | HUD frontend, ClickHouse queries, Lambda functions |
| [pytorch/crcr-test](https://github.com/pytorch/crcr-test) | CRCR health probe repo (L2) |
| [pytorch/rfcs](https://github.com/pytorch/rfcs) | RFC-0056 for nightly/periodic CI |
| [TorchedHat/pytorch-redhat-ci](https://github.com/TorchedHat/pytorch-redhat-ci) | RHEL 9.6 downstream CI (L3) |
| [subinz1/pytorch-targeted-tests](https://github.com/subinz1/pytorch-targeted-tests) | Diff-based test selection for nightly CI |
