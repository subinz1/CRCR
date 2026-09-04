# Partner Onboarding Checklist (Results Relay → CRCR HUD)

Use this when an external CI suite should appear on the PyTorch CRCR nightly HUD via Results Relay. No partner-specific secrets or endpoints are listed here — obtain those from the relay operators.

## Before first delivery

- [ ] Confirm the partner GitHub repo will be **allowlisted** on the relay.
- [ ] Confirm CI runs on **GitHub Actions** (or another supported OIDC issuer agreed with operators).
- [ ] Agree the **OIDC audience** string for the relay (tokens minted for other audiences are rejected).
- [ ] Decide which pytorch **nightly SHA** each run targets and how the workflow learns that SHA.

## Payload contract

- [ ] `delivery_id` = **pytorch commit SHA** (required for correct nightly column grouping).
- [ ] `event_type` = `nightly` or `periodic` as appropriate.
- [ ] Stable `job_name` values; prefer slash form `group / case` for HUD grouping.
- [ ] `workflow_name`, `run_id`, `run_attempt` populated for dedup / tooltips.
- [ ] `conclusion` / `status` use the relay’s accepted enums (`success`, `failure`, …).
- [ ] `workflow_run_url` points at the **original** partner workflow run.
- [ ] Optional: `artifact_url` when logs/artifacts live outside the workflow run page.

## Auth & safety

- [ ] Mint a **fresh OIDC token per delivery**; do not embed long-lived API keys.
- [ ] Treat relay/HUD posting as **best-effort** — partner CI must not fail closed if HUD is down.
- [ ] Do not send secrets, credentials, or private log contents in the JSON payload.

## Validation on HUD

- [ ] After a successful post, confirm the SHA appears on the CRCR **Nightly** view for the mapped repo.
- [ ] Spot-check job chips and duration; open `workflow_run_url` (and `artifact_url` if provided).
- [ ] Re-run finalize once and confirm write-once behavior does not flip a sealed nightly (operators: see `docs/write-once-guard.md`).

## References

- `docs/external-ci-results-relay.md`
- `docs/architecture-nightly-self-report.md`
- `docs/hud-data-flow.md`
- Mockup: `mockups/artifact-url-tooltip-mockup.html`
