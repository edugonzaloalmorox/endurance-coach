# Endurance Coach — Agent Instructions

## Mission

Build a working, local Python AI endurance coach. The human is the Product Owner and AI Architect;
agents implement requested functionality autonomously within the agreed product and safety scope.

Current priorities are historical FIT/FIT.GZ ingestion into SQLite, incremental Intervals.icu
synchronization, and local Ollama-backed analysis and recommendations.

Read `docs/process.md` before repository work.

## Default development workflow

1. Implement the requested functionality.
2. Demonstrate that it works through a representative CLI or end-to-end use case.
3. Add essential tests for behavior, failures, data integrity, privacy, and security.
4. Run final verification:

```bash
uv run pytest
uv run ruff check .
```

No requirements-validation phase, intermediate test run, GitHub issue, issue-specific branch,
pull request, PM pass, Orchestrator pass, independent QA pass, or documentation-impact gate is
required. Use any of them only when useful or when repository permissions enforce them. Do not add
governance mechanisms or tests that make these optional practices mandatory again.

Preserve existing user changes. Never bypass repository permissions or branch protection. Commit,
push, open or merge pull requests, and modify external systems only when authorized.

## Architecture

Organize code by responsibility rather than implementation sequence:

- `domain/` owns business contracts and must not import infrastructure.
- `analysis/` owns deterministic calculations and must not call providers, databases, or LLMs.
- `integrations/` owns external formats and providers and maps them to internal contracts.
- `llm/` owns bounded local model interaction.
- `skills/` owns runtime skill discovery and loading; runtime skills live in `coach_skills/`.
- `services/` coordinates workflows across boundaries.
- `storage/` owns persistence, transactions, provenance, and idempotency.
- `fixtures/` contains deterministic synthetic data only.
- `cli.py` stays thin and `config.py` owns typed configuration.

Add packages incrementally. Do not create placeholders or perform unrelated repository-wide moves.
Preserve public interfaces when moving affected code and avoid circular imports or hidden global
state.

## Product quality, safety, and privacy

- Preserve missing values, units, and source provenance. Distinguish measured, estimated, derived,
  and unavailable data.
- Historical imports and provider synchronization must be idempotent, transactional, and safe to
  retry. Never modify source archives.
- Intervals.icu is the primary activity source; COROS is supplementary. Reconcile duplicates.
- Keep external integrations read-only unless an explicitly approved scope says otherwise.
- Calculate metrics in Python or SQL, not in the LLM. Do not invent unavailable measurements.
- Keep athlete records, GPS tracks, credentials, real databases, prompts, and secrets out of Git,
  logs, fixtures, and external services. Use deterministic synthetic data in automated tests.
- Keep Ollama inference local unless another provider is explicitly approved.
- Validate tool inputs and bound results, model context, retries, and iterations.
- Never apply a proposed workout-plan change without explicit athlete approval.
- Use explicit SQLite transactions, preserve auditability, and enforce database integrity.
- Preserve meaningful product, data-integrity, privacy, and security tests. Never weaken assertions
  merely to obtain a pass.

## Python standards

Use Google-style docstrings for public modules, classes, methods, and functions where they add
useful purpose, arguments, returns, errors, units, side effects, assumptions, or limitations.

Configured commands:

- `uv sync` when dependencies change or setup requires it.
- `uv run pytest tests/<test_file>.py` for optional focused verification.
- `uv run pytest` for mandatory final regression verification.
- `uv run ruff check .` for mandatory final linting.

Report implemented behavior, the demonstration performed, final verification results, and any real
limitations or blockers. Passing tests alone is not a product deliverable.
