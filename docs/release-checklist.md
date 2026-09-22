# CRCR Release Checklist

Use this checklist for a relay, HUD-query, or allowlist deployment that changes
which results are routed or displayed.

## Before merge

- [ ] Identify whether the change affects PR, nightly, periodic, or every event.
- [ ] Preserve legacy behavior for allowlist entries without new metadata.
- [ ] Verify the dashboard and API query use the same eligibility/attempt rule.
- [ ] Add coverage for malformed configuration and the excluded-event case.
- [ ] Document any new partner-facing callback requirement.

## Deployment order

1. Deploy parser/schema support.
2. Deploy receiver/dispatch behavior.
3. Deploy HUD query and rendering behavior.
4. Add explicit allowlist metadata for individual backends.

Applying configuration before deployed code understands it is a common source
of avoidable outages.

## After deployment

- [ ] Trigger or observe a known-good PR flow if it was changed.
- [ ] Verify a scheduled result groups under the expected PyTorch SHA.
- [ ] Check that excluded backends are absent from the inappropriate summary tab.
- [ ] Confirm failed callbacks are visible in logs and have actionable errors.
- [ ] Record the deployed behavior in the relevant operator documentation.

See [event participation](event-participation.md) for the nightly-only rollout
and [incident triage](incident-triage.md) if a result is missing.
