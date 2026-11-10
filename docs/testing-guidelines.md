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

Use focused tests while Engineering iterates. Once the Engineering candidate is stable, run the
configured final local verification once against that candidate, including:

```bash
uv run pytest tests/test_documentation_impact_gate.py
uv run pytest
uv run pytest -m "not exercise"
uv run ruff check .
git diff --check
```

Report each exact command, its exit status, and its actual passed, failed, skipped, deselected,
expected-failure, and unexpected-pass counts. Inspect the reported behavior; do not infer success
from an exit status alone. Run focused tests as useful, but they do not replace the full suite.

Pull-request CI repeats the configured quality gate independently and remains the final full-suite
release verification. It must verify the exact pull-request head commit, use the committed
dependency lock, and expose command outcomes in durable GitHub logs and the job summary. Independent
QA remains read-only and verifies every acceptance criterion with acceptance-focused checks; when
successful exact-head CI already supplies full-suite coverage, QA may rely on that durable evidence
instead of rerunning the full suite. Local Engineer results, independent QA results, and CI results
remain three distinct evidence sources and must refer to the same candidate where applicable.

Record each phase handoff using the compact machine-readable fields in `docs/process.md`. Use actual
exposed token usage or `unavailable`, never an estimate. Link durable evidence rather than copying
complete logs, while retaining exact commands, exit codes, concise passed/failed/skipped/deselected/
expected-failure/unexpected-pass counts, and material failures in that evidence. Never include
prompts, hidden reasoning, secrets, credentials, or athlete data.

## Documentation-impact routing pre-check

After the Engineering candidate is stable, classify the explicit base-to-candidate changed paths
using the deterministic mapping in `docs/process.md`. Record only `MATERIAL_CANDIDATE` or
`NO_MATERIAL_INDICATOR`. This advisory result chooses a full or concise documentation review; it
never produces `UPDATED`, `NO_DOC_CHANGE`, or `BLOCKED`, and never permits QA to bypass `docs-sync`.
Unknown paths route conservatively to `MATERIAL_CANDIDATE`.

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
implementation or documentation commit changes the candidate SHA, invalidates the report and QA
evidence, and requires the routing pre-check, `docs-sync`, report validation, independent QA, and
hosted CI again. A `NO_MATERIAL_INDICATOR` permits a concise review but still requires an
evidence-based `NO_DOC_CHANGE` report and successful validator result. The focused validator tests
must cover both passing outcomes and every blocking class, but they do not replace the final local
verification, independent QA, or hosted CI.

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
