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
| [Display Options](mockups/crcr-nightly-display-options.html) | 16 design options for nightly/periodic display | Design exploration |
| [Nightly Tab Design](mockups/crcr-summary-nightly-design.html) | Standalone nightly tab mockup (Option A) | [#8377](https://github.com/pytorch/test-infra/pull/8377) |
| [Display Options](mockups/crcr-nightly-display-options.html) | 16 design options (A–P) for nightly display | Design exploration |

## Implementation Status

### Merged PRs

| PR | Title |
|----|-------|
| [#8220](https://github.com/pytorch/test-infra/pull/8220) | CRCR Summary page with stat cards |
| [#8244](https://github.com/pytorch/test-infra/pull/8244) | Move CRCR link to top-level navbar |
| [#8247](https://github.com/pytorch/test-infra/pull/8247) | CRCR workflow boxes on PR page |
| [#8285](https://github.com/pytorch/test-infra/pull/8285) | CRCR columns on main HUD grid |
| [#8318](https://github.com/pytorch/test-infra/pull/8318) | CRCR Metrics page |
| [#8319](https://github.com/pytorch/test-infra/pull/8319) | Per-repo downstream dashboard |
| [#8330](https://github.com/pytorch/test-infra/pull/8330) | PR-based grouping for downstream page |
| [#8341](https://github.com/pytorch/test-infra/pull/8341) | Fix idle crash on CRCR pages |
| [#8343](https://github.com/pytorch/test-infra/pull/8343) | Filter HUD grid to L3/L4 only |
| [#8386](https://github.com/pytorch/test-infra/pull/8386) | Fix PR search for CRCR check runs |

### Open PRs

| PR | Title | Status |
|----|-------|--------|
| [#8302](https://github.com/pytorch/test-infra/pull/8302) | Nightly/periodic callback handler | In review |
| [#8303](https://github.com/pytorch/test-infra/pull/8303) | CI-neutral callback action | In review |
| [#8304](https://github.com/pytorch/test-infra/pull/8304) | SHA validator for nightly commits | In review |
| [#8353](https://github.com/pytorch/test-infra/pull/8353) | Event type column for nightly/periodic | Draft |
| [#8366](https://github.com/pytorch/test-infra/pull/8366) | Healthy/Degraded display on summary page | Draft |
| [#8376](https://github.com/pytorch/test-infra/pull/8376) | Fix x-prefix success rate calculation | Draft |
| [#8377](https://github.com/pytorch/test-infra/pull/8377) | Nightly tab on CRCR summary page | Draft |
