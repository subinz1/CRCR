# CRCR

All files, mockups, docs, diagrams, and reports related to the CRCR (Cross-Repository CI Relay) integration into the PyTorch CI Health Dashboard (HUD).

**Live mockups**: [subinz1.github.io/CRCR](https://subinz1.github.io/CRCR/)

## Repository Structure

```
├── index.html                 # Landing page (GitHub Pages entry point)
├── mockups/                   # Interactive HTML mockups
├── docs/                      # Design docs, proposals, blog post, reviews
│   └── rfcs/                  # RFC snapshots (RFC-0050, RFC-0054)
├── diagrams/                  # Excalidraw diagrams and architecture PNGs
├── reports/                   # Weekly reports, nightly status, test reports
├── test-plans/                # L1/L2 test plans and manual infra test plans
└── scripts/                   # Utility scripts (diagram gen, torchtalk test)
```

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

## Docs

| Document | Description |
|----------|-------------|
| [AI-First Development Report](docs/CRCR_AI_First_Development_Report.md) | Report on AI-assisted CRCR development |
| [Blog Post](docs/CRCR_Blog_Post.md) | CRCR blog post draft |
| [Nightly/Periodic Proposal](docs/CRCR_Nightly_Periodic_Proposal.md) | Proposal for nightly & periodic CI support |
| [Nightly/Periodic Options Comparison](docs/CRCR_Nightly_Periodic_Options_Comparison.md) | Comparison of implementation options |
| [Security Assessment](docs/CRCR_Security_Assessment.md) | CRCR security review |
| [PR Review Comments](docs/CRCR_PR_Review_Comments.md) | Collected PR review feedback |
| [Alerting Questions](docs/CRCR_Alerting_Questions.md) | Alerting design Q&A |
| [OOT → CRCR Rename Plan](docs/OOT_to_CRCR_Rename_Plan.md) | Migration plan from OOT to CRCR naming |
| [HUD Data Source Mapping](docs/OOT_HUD_Data_Source_Mapping.md) | Data source mapping for HUD queries |
| [L2 PR Summary](docs/L2_PR_SUMMARY.md) | L2 callback PR summary |
| [RFC 96 Analysis](docs/RFC_96_NEW_COMMENTS_ANALYSIS.md) | RFC 96 comment analysis |

## Diagrams

| File | Description |
|------|-------------|
| [Architecture Diagram](diagrams/crcr_architecture_diagram.excalidraw) | Full CRCR architecture (Excalidraw) |
| [Architecture Flow](diagrams/crcr_architecture_flow.png) | Architecture flow diagram |
| [State Machine](diagrams/crcr_state_machine.png) | Callback state machine diagram |
| [Security Layers](diagrams/crcr_security_layers.png) | Security architecture layers |
| [Nightly/Periodic Flow](diagrams/CRCR_Nightly_Periodic_Flow.excalidraw) | Nightly & periodic CI flow (Excalidraw) |
| [In-tree CI Architecture](diagrams/intree_ci_architecture_diagram.excalidraw) | In-tree CI architecture reference |

## Implementation Status

- **Merged**: Main HUD grid (#8285), PR workflows (#8247), Summary page (#8220), Per-repo dashboard (#8319, #8330), Metrics page (#8318), CRCR Metrics in navbar (#8244), Idle crash fix (#8341), L3/L4 filter (#8343)
- **Open**: Event type column for nightly/periodic (#8353)
