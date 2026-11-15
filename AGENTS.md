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

1. `domain/` must not import infrastructure modules.
2. `analysis/` depends on domain contracts, not external providers.
3. `integrations/` communicates with external systems and maps data into validated internal contracts.
4. `llm/` must not directly bypass application services, tool permissions, or external-provider allowlists.
5. `services/` coordinates application behavior and dependencies.
6. `storage/` isolates persistence mechanisms.
7. Avoid circular imports and hidden global state.
8. Prefer dependency injection when it materially improves testability or separation.
9. Do not introduce frameworks merely to enforce the architecture.

### Incremental migration policy

The current repository contains flat modules such as:

- `models.py`
- `metrics.py`
- `runtime.py`
- `skills.py`
- `sample_data.py`

**Do not reorganize them all in one unrelated PR.**

For each approved issue:

1. Identify the responsible target package.
2. Add new functionality to that package where appropriate.
3. If existing functionality must move, migrate only the affected modules.
4. Update imports, tests, and documentation.
5. Preserve public interfaces or provide temporary compatibility re-exports where necessary.
6. Avoid circular dependencies.
7. Remove compatibility wrappers only through an explicitly scoped, verified change.
8. Verify no behavior has unintentionally changed.

For example, the COROS MCP issue may introduce `integrations/coros_mcp.py` without requiring an immediate refactor of `metrics.py`, `models.py`, or `runtime.py`.

A repository-wide structural migration requires a separately approved issue and migration plan.

### Testing organization

Mirror the product's functional modules in `tests/` where practical.

Examples:

- `analysis/` → `tests/analysis/`
- `integrations/` → `tests/integrations/`
- `llm/` → `tests/llm/`
- `skills/` → `tests/skills/`
- `storage/` → `tests/storage/`

Rules:

- Use deterministic fixtures.
- Mock external providers and LLM responses in CI.
- Separate unit tests from integration tests.
- Test module boundaries and failure behavior.
- Verify normal inputs, edge cases, missing data, and safety constraints.
- Keep factory governance tests separate from product behavior tests.
- Preserve existing test paths until the related migration is approved.

### Structural quality requirements

Before submitting an implementation, Engineer should verify:

- New code is placed in the correct responsibility-based package.
- Modules do not mix unrelated infrastructure and business logic.
- Dependencies follow the documented direction.
- No unnecessary abstraction or duplicate implementation has been introduced.
- Related tests cover the functionality.
- The relevant architecture documentation remains accurate.

Escalate major boundary changes or departures from the agreed architecture.

Routine placement within these boundaries does not require human approval.

---

## Factory Roles

### Orchestrator

Coordinates lifecycle states, selects dependency-ready issues, delegates tasks, validates documentation evidence, and enforces retry limits.

Does not groom, implement, review documentation, or independently verify code.

Prefer deterministic state management over LLM judgment for permissions and gates.

### PM

Transforms GitHub Issues into executable specifications containing scope, acceptance criteria, dependencies, assumptions, risk, and exclusions.

For implementation issues, identify the expected module responsibilities and architectural constraints when relevant.

Escalate consequential ambiguity.

Follow `docs/agents/pm.md`.

### Engineer

Implements approved specifications using the modular architecture.

Responsibilities include:

- Implementing functionality in the appropriate modules.
- Maintaining dependency boundaries.
- Writing tests and documentation.
- Running required checks.
- Preparing an exact candidate commit.
- Reporting implementation evidence.

Follow `docs/agents/software-engineer.md`.

### Documentation Impact Gate

The `docs-sync` development skill reviews the exact candidate against its explicit base after Engineering and before QA.

It updates only materially affected `README.md` and `docs/` content, records `UPDATED`, `NO_DOC_CHANGE`, or `BLOCKED`, and produces an external report validated by `.agents/validate_docs_impact.py`.

When module structure or dependency boundaries change materially, review `docs/architecture.md`.

Documentation evidence does not replace independent QA.

### QA Engineer

Independently verifies the implementation and acceptance criteria against the exact candidate commit.

QA must refuse handoffs without a valid, current Documentation Impact Report.

QA must also assess compliance with module boundaries when the issue changes application architecture.

QA does not modify implementation code or weaken tests.

Follow `docs/agents/qa-engineer.md`.

### Human Product Owner / AI Architect

Defines product direction, architecture, high-impact decisions, risk tolerance, and acceptance expectations.

Approves consequential architecture deviations, new permissions, and integration decisions.

Routine implementation details do not require human approval.

Use real subagents only when supported. Otherwise disclose that verification was performed in sequential role passes rather than independently.


## Autonomy Boundaries

Agents may execute without per-step approval when:

- The issue is ready and dependency-complete.
- Requirements are unambiguous.
- The implementation stays within approved architectural boundaries.
- Permissions authorize the required actions.

**Escalate to the human before proceeding when:**

- A new architectural direction, framework, deployment platform, model provider, or significant dependency is proposed.
- Requirements conflict or acceptance criteria materially change.
- New credentials, OAuth scopes, external writes, or data sharing are required.
- A change affects athlete safety, privacy, or approval requirements.
- A significant cross-module refactor or new dependency direction is proposed.
- QA cannot establish correctness or retry limits are reached.
- Destructive operations or GitHub protection-policy changes are needed.

Do not escalate ordinary module placement, routine refactoring, or implementation decisions already covered by these rules.


## Execution and Release Rules

- GitHub Issues are the authoritative backlog.
- Follow `docs/process.md`.
- Work only on dependency-ready issues.
- Use issue-specific branches or isolated worktrees.
- Never implement directly on `master`.
- Do not change acceptance criteria to manufacture a PASS.
- Complete appropriate Engineering checks and the Documentation Impact Gate before QA starts.
- Validate the documentation report against the exact candidate SHA.
- Any later commit invalidates earlier exact-SHA documentation and QA eligibility.
- Missing, stale, malformed, or `BLOCKED` documentation evidence prevents QA.
- Run applicable unit/integration tests, linting, safety checks, and secret checks.
- Preserve evidence for implementation, documentation, QA, CI, and human decisions.
- Agents may commit, push issue branches, and create PRs only with authorized tooling and permissions.
- **Merging and closing issues remain human-controlled by default.**
- Never bypass branch protection.
- If QA fails, return the failure to Engineer. Cap automatic execution at three total Engineering attempts: the initial implementation plus at most two automated repair attempts. A further failure or an unreproducible result requires `NEEDS_HUMAN`.

### Efficiency guidelines

- Keep routine, short, or inherently sequential implementation in one Engineer context.
- Use subagents only for genuinely independent work that can be isolated without duplicating context or weakening ownership.
- Final QA remains a separate read-only context when supported.
- Prefer focused tests during implementation; required final checks and hosted CI remain mandatory.
- Avoid spawning new subagents for short deterministic tasks.
- Reuse verified existing evidence when its commit SHA and conditions remain valid.
- Avoid repeatedly reading unchanged files or documentation.
- Do not introduce additional abstraction layers without a clear functional need.
- Keep reports concise and refer to existing logs and evidence rather than duplicating them.



## Product Safety and Privacy

- Ollama inference is local. Do not transmit athlete records to unapproved external LLMs.
- Intervals.icu is the primary activity source; COROS is supplementary.
- Reconcile synchronized activities to prevent duplicate counting.
- COROS and Intervals.icu integrations remain read-only for the MVP.
- Enforce read-only access in integration code, not just in prompts.
- Never write to third-party services without an explicitly approved scope.
- Missing power, HRV, sleep, or recovery observations must remain missing.
- Do not represent estimated metrics as directly measured.
- Weekly training defaults to nine hours, adjustable by the user; strength frequency depends on training phase.
- **No proposed workout-plan modification may be applied without explicit athlete approval.**
- Store credentials securely and apply least-privilege permissions.
- Keep secrets and personal records out of commits, logs, fixtures, and PR evidence.

## Python Documentation Standards

Public Python modules, classes, methods, and functions should use Google-style docstrings.

Document, where applicable:

- Purpose and behavior.
- `Args`, `Returns`, `Raises`, and `Yields`.
- Units and constraints.
- Side effects.
- Assumptions and limitations.
- External dependencies.

- `uv sync` — when dependencies change or setup requires it.
- `uv run pytest tests/<test_file>.py` — focused verification.
- `uv run pytest` — final regression verification.
- `uv run ruff check .` — final linting.

Keep the final report concise: implemented feature, demonstration command and result, verification results, and blockers. Passing tests alone is not a deliverable.