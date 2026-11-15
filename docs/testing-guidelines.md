# Testing guidelines

## Purpose

Tests protect product behavior, data integrity, privacy, security, and athlete safety. Prefer
deterministic tests with synthetic fixtures and mocked provider or model boundaries.

## Test design

- Cover the implemented success path and meaningful boundaries and failures.
- Preserve missing observations instead of fabricating values.
- Verify idempotency, transactions, duplicate prevention, provenance, and rollback where relevant.
- Keep real athlete records, credentials, access tokens, GPS traces, and private prompts out of
  tests, fixtures, snapshots, command output, and evidence.
- Mock external providers and LLM responses in automated tests.
- Never weaken an assertion or safety constraint merely to make a check pass.
- Keep proposed workout-plan changes unapplied until explicit athlete approval.

Focused checks during implementation are optional. Do not require baseline suites, intermediate
validation, governance validators, or independent QA before implementation.

## Final verification

The only mandatory final verification commands are:

```bash
uv run pytest
uv run ruff check .
```

Run them when the requested functionality has been implemented, demonstrated, and supplied with its
essential tests. Report the real results, including expected failures or skips shown by pytest.

## Deferred product specifications

Strict expected failures may temporarily preserve executable product specifications for unfinished
behavior. Remove the marker when the behavior is implemented. GitHub issue ownership and a separate
governance-policy test are not required.
