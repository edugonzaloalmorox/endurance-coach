# Testing Guidelines

## Purpose

Tests are release evidence for the exact commit under review. They must be deterministic,
reproducible, and tied to observable acceptance criteria. A passing command is not sufficient when
the behavior it is intended to prove was not exercised.

## Test design

- Isolate tests from the network, local Ollama processes, clocks, and mutable user state unless an
  integration test explicitly declares and controls that dependency.
- Use deterministic fixtures and scripted clients for agent, skill, and provider behavior.
- Cover normal behavior, boundaries, missing inputs, invalid inputs, and safety constraints named by
  the issue.
- Do not weaken assertions or change acceptance criteria after implementation to manufacture a
  passing result.
- Never put real athlete records, credentials, access tokens, or other secrets in tests, fixtures,
  snapshots, command output, or evidence. Use synthetic data and mock COROS/Intervals.icu clients.
- Verify that proposed workout-plan changes remain proposals until the athlete explicitly approves
  them.

## Required verification

Run the commands configured for the repository, including:

```bash
uv run pytest
uv run pytest -m "not exercise"
uv run ruff check .
```

Report each exact command, its exit status, and its actual passed, failed, skipped, deselected,
expected-failure, and unexpected-pass counts. Inspect the reported behavior; do not infer success
from an exit status alone. Run focused tests as useful, but they do not replace the full suite.

## Deferred executable specifications

A deferred test may use `xfail(strict=True)` only as an exceptional, temporary representation of
behavior assigned to an open implementation issue. Every strict xfail must:

- remain collected and keep its complete assertions and inputs;
- identify its owning issue in the marker reason;
- state that the owning issue must remove the marker when it implements the behavior;
- appear explicitly, with its owning issue, in Engineer and QA evidence; and
- fail the suite as an unexpected pass until the marker is deliberately removed.

Do not use `skip`, a non-strict xfail, marker-based default exclusion, or weakened assertions to make
deferred behavior disappear. The owning implementation issue must remove its strict xfail marker and
make the unchanged executable specification pass. A new deferred test or a change to this policy
requires Product Owner approval during grooming.
