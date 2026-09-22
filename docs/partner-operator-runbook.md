# Partner Operator Runbook

Use this runbook after a partner is onboarded and begins sending CRCR results.
It focuses on keeping the partner pipeline reliable while preserving actionable
HUD signal.

## Every scheduled run

1. Resolve the PyTorch SHA to test and retain it as `delivery_id`.
2. Run the build/test pipeline according to the partner's own failure policy.
3. Post authenticated job updates with stable names and the original workflow
   URL.
4. Treat an unavailable relay as telemetry degradation, not a reason to mask a
   build or test failure.
5. Confirm the completed callback includes the actual terminal conclusion.

## When the relay post fails

| Symptom | Partner action |
|---|---|
| authorization error | verify repository, workflow identity, and OIDC audience |
| schema error | inspect the response; correct field names/types before retrying |
| transient HTTP/network failure | retry with the same delivery and attempt identity |
| receiver dispatch fails | record the downstream run URL; do not report success solely because dispatch started |

## When HUD data looks wrong

- Ensure the PyTorch SHA—not the partner commit—is the scheduled `delivery_id`.
- Check whether the intended row is a later attempt than the one being viewed.
- Verify the repo is configured for the event type being reported.
- Check both `workflow_run_url` and optional `artifact_url`.

Escalate with the delivery ID, run ID, attempt, event type, timestamp, and a
sanitized callback response. This is enough for relay operators to trace the
record without receiving secrets.
