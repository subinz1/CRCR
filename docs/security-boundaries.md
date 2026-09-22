# CRCR Security Boundaries

CRCR accepts results from systems outside the PyTorch repository boundary. The
relay therefore authenticates who is allowed to make a claim before it stores
or displays that claim.

## Trust decisions

| Decision | Trusted source |
|---|---|
| Which repository is calling | verified OIDC claims or a verified relay envelope |
| Whether the repo is eligible | allowlist configuration |
| Which trust tier applies | allowlist configuration |
| Whether a payload may be accepted | schema and state validation |
| Job title, URL, duration | untrusted display payload after validation |

## OIDC guidance

- Mint short-lived tokens for the relay's expected audience.
- Validate issuer, audience, signature, expiration, and repository claims.
- Rotate through provider JWKS rather than storing partner credentials.
- Do not log bearer tokens, raw authorization headers, or secrets in job
  metadata.

## Replay and duplicate control

`delivery_id`, run identity, and attempt fields provide a stable basis for
deduplication. They are not substitutes for authentication. Scheduled final
callbacks additionally need write-once protection so a late duplicate cannot
change an established nightly result.

## What partner CI should send

Send the minimal metadata necessary to diagnose a CI run: the tested PyTorch
SHA, job identity, status/conclusion, duration, and public or authorized links.
Do not send private logs, credentials, or opaque serialized environment data.

The [external results relay](external-ci-results-relay.md) documents the
partner-facing path in more detail.
