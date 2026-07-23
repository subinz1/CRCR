# CRCR

All the files and mock-ups related to the HUD changes related to CRCR (Cross-Repository CI Relay).

**Live mockups**: [subinz1.github.io/CRCR](https://subinz1.github.io/CRCR/)

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

## Implementation Status

- **Merged**: Main HUD grid (#8285), PR workflows (#8247), Summary page (#8220), Per-repo dashboard (#8319, #8330), Metrics page (#8318), CRCR Metrics in navbar (#8244), Idle crash fix (#8341), L3/L4 filter (#8343)
- **Open**: Event type column for nightly/periodic (#8353)
