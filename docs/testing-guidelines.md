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

Pull-request CI repeats these commands independently. It must verify the exact pull-request head
commit, use the committed dependency lock, and expose command outcomes in durable GitHub logs and
the job summary. Local Engineer results, independent QA results, and CI results are three distinct
evidence sources; none substitutes for another.

## Documentation Impact Gate

After Engineering stabilizes and before independent QA, run the tracked
`.agents/skills/docs-sync/SKILL.md` against an explicit base and exact candidate commit. Store its
Documentation Impact Report outside the candidate commit and validate the matching JSON artifact:

```bash
uv run python .agents/validate_docs_impact.py \
  --report /path/to/documentation-impact.json \
  --candidate-sha "$(git rev-parse HEAD)"
```

The validator must exit zero for QA to start. A current `UPDATED` or evidence-based
`NO_DOC_CHANGE` report can pass; `BLOCKED`, missing, malformed, or stale evidence cannot. Any later
commit invalidates the report and requires documentation review and validation again. The focused
validator tests must cover both passing outcomes and every blocking class, but they do not replace
the full test suite, independent QA, or hosted CI.

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

`tests/test_deferred_test_policy.py` enforces the approved count, ownership, strictness, removal
instructions, and absence of skips. CI must run that policy test explicitly in addition to the full
suite. An ordinary failure, skip, missing or extra expected failure, or strict xfail that unexpectedly
passes is a failed quality gate, never a result to ignore or relabel.
