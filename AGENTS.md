# Endurance Coach — Agent Instructions

## Mission

Build a working, local Python AI endurance coach. The human is the Product Owner and AI Architect; agents deliver working features autonomously within the agreed scope.

Current priorities, in order:
1. Import historical FIT/FIT.GZ files and CSV metadata into SQLite.
2. Keep the database current using the Intervals.icu API.
3. Enable natural-language analysis and training recommendations through Ollama and read-only retrieval tools.

## Default workflow: implement → demonstrate → verify

- Read the user request and inspect only the relevant code. Treat an actionable request or ready issue as sufficient specification; do not re-groom it.
- Start implementing immediately. Deliver a complete, usable vertical slice before expanding tests or documentation. Do not stop at contracts, scaffolding or plans.
- During implementation, run only diagnostics or targeted checks needed to unblock the work. Do not run baseline suites, repeated full suites, governance validators or independent QA at every step.
- Demonstrate the feature through a real CLI command or representative end-to-end use case. Use private local data only when authorized and available; otherwise use a synthetic fixture and disclose the limitation.
- After the feature works, add or update a small number of meaningful tests, run targeted tests, then run the full suite and lint once at final verification. Rerun only affected checks after fixes unless broader verification is warranted.
- Update materially affected documentation once. Report what works, how to reproduce it, actual check results and remaining blockers.

Do not loop over requirements, generate repeated plans, or spawn agents to verify intermediate work. Resolve routine ambiguity with a reasonable documented assumption. If blocked, identify the concrete blocker and continue with independent work where possible. Never claim success without evidence.

## Architecture

Keep a local modular monolith using Python 3.12+, uv, SQLite and Ollama. Prefer existing modules and cohesive functions over new layers, frameworks or placeholder packages.

| Responsibility | Boundary |
| --- | --- |
| Ingestion and integrations | Parse FIT/CSV, normalize provider data, sync Intervals.icu |
| Storage | SQLite, transactions, identity, provenance and deduplication |
| Domain and analytics | Validated models and deterministic sports calculations |
| LLM and retrieval | Bounded, typed read-only tools; grounded interpretation |
| CLI and configuration | Thin commands and environment-based settings |

Organize code by responsibility, not issue number. Preserve useful existing interfaces. Keep calculations independent of provider and LLM calls. Load runtime coaching skills from `coach_skills/` only when needed; development skills are separate.

Use FIT files as the historical measurement source, CSV as complementary metadata, and Intervals.icu for incremental updates. Defer COROS MCP, vector databases, speculative abstractions and unrestricted Text-to-SQL unless explicitly requested.

## Essential quality and safety

- Preserve missing values, distinguish measured from estimated data, and retain units and source provenance. Never replace valid historical measurements with restricted or null API results.
- Make imports and synchronization idempotent; prevent duplicate activities and use transactions. Leave original files unchanged.
- Calculate numerical metrics in Python or SQL, not in the LLM. State data limitations and use historically valid athlete settings where required.
- Keep external integrations read-only. Validate tool inputs and bound query results, context size and model iterations.
- Keep athlete data, GPS tracks, credentials and real databases out of Git, logs, fixtures and PRs. Use local Ollama; never send private records to unapproved services.
- Never apply training-plan changes without explicit athlete approval.
- Test critical behavior: parsing, data integrity, duplicate prevention, metric accuracy, failure handling and privacy. Preserve meaningful existing tests; never weaken assertions to obtain a pass. Use deterministic fixtures and mock external services in automated tests.

## Development and release

Use a feature branch or isolated worktree and preserve existing user changes. Never bypass branch protection. Commit, push or open PRs only when authorized; merges and issue closures remain human-controlled by default.

Use a single implementation agent by default. PM, documentation and independent QA passes are optional unless an existing mandatory release gate requires them; perform required gates once per completed candidate, not during implementation. Do not claim independent QA if it was not independent.

Request approval only for consequential architecture changes, significant new dependencies, external writes or permissions, destructive operations, or changes to privacy and athlete approval rules. Routine implementation decisions need no approval.

`docs/process.md`, role documents and development skills are supporting references, not additional planning loops. Align conflicting workflow instructions with this implementation-first policy; do not silently bypass enforced CI or repository protections. Report any remaining mandatory gate that conflicts with this workflow.

## Commands

- `uv sync` — when dependencies change or setup requires it.
- `uv run pytest tests/<test_file>.py` — focused verification.
- `uv run pytest` — final regression verification.
- `uv run ruff check .` — final linting.

Keep the final report concise: implemented feature, demonstration command and result, verification results, and blockers. Passing tests alone is not a deliverable.