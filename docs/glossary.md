# CRCR Glossary

| Term | Meaning |
|---|---|
| CRCR | Cross-Repository CI Relay: the system connecting upstream PyTorch changes and downstream compatibility CI. |
| backend | A downstream repository or CI provider registered with CRCR. |
| trust tier | L1–L4 integration depth, from dispatch-only onboarding through a blocking PR prerequisite. |
| event participation | The logical events a backend supports, such as `pull_request` and `nightly`. |
| dispatch | An upstream-triggered request for a downstream CI system to run work. |
| callback | An authenticated downstream-to-CRCR result update. |
| Results Relay | A receiver that verifies an external partner's OIDC identity before forwarding a result into CRCR. |
| delivery ID | Stable identity for a result group; for scheduled work, normally the PyTorch SHA under test. |
| run attempt | A specific retry of a downstream workflow run. HUD metrics normally select the latest attempt. |
| zombie sweeper | Periodic process that finalizes work left `in_progress` beyond the configured timeout. |
| crcr-test | PyTorch's intentional health-probe backend, containing success and expected-failure probes. |
| HUD | The PyTorch CI dashboard at [hud.pytorch.org](https://hud.pytorch.org/). |
| DynamoDB | Operational storage for callback state. |
| ClickHouse | Analytical store queried by HUD pages. |

For diagrams and system context, begin with the [documentation map](README.md)
and [HUD data flow](hud-data-flow.md).
