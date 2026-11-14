# Endurance Coach — Dark Software Factory Instructions

## Mission

Endurance Coach is a Python AI cycling coach for long-distance training and an experiment in **agent-driven software delivery**.

The human acts as **Product Owner and AI Architect**: they define goals, architecture, constraints, and acceptance outcomes. Agents plan, implement, synchronize documentation, verify changes, and produce evidence.

Human code review is optional, not a routine release gate.

The product's runtime skills in `coach_skills/<skill-name>/SKILL.md` are distinct from the development-agent skills that guide Codex.

**Read `docs/process.md` before selecting or executing any work.**

## Commands

- `uv sync` — synchronize dependencies.
- `uv run pytest` — full test suite.
- `uv run pytest tests/<test_file>.py` — focused tests.
- `uv run ruff check .` — linting.

Run only configured commands. Report actual results, never assumed successes.

## Documents

- `docs/architecture.md` — product architecture, components, and boundaries.
- `docs/process.md` — factory lifecycle, autonomy, escalation, and release gates.
- `docs/testing-guidelines.md` — testing requirements.
- `docs/endurance_coach_development_plan_en.md` — product roadmap.
- `docs/agents/pm.md` — PM role.
- `docs/agents/software-engineer.md` — Engineer role.
- `docs/agents/qa-engineer.md` — QA role.
- `.agents/skills/docs-sync/SKILL.md` — Documentation Impact Gate procedure.
- `.agents/validate_docs_impact.py` — exact-commit documentation report validator.

Read only the relevant documents for the assigned work, plus mandatory factory instructions. Avoid loading the entire repository into the agent context unnecessarily.

If a referenced document is missing, report it.

---

## Repository Architecture

### Architectural principle

**Organize code by responsibility, not by implementation sequence or individual GitHub Issues.**

Each Python module must have a clear responsibility and a coherent reason to change.

Separate:

- External connections and APIs.
- Domain models and validation.
- Deterministic calculations.
- LLM communication and inference.
- Agent skills and tool execution.
- Application-level workflows.
- Persistence and state management.
- CLI interfaces and configuration.

Avoid monolithic modules that mix unrelated responsibilities.

Do not create one file per function or class unnecessarily. Prefer cohesive, reasonably sized modules.

### Target repository structure

The following is the **target architecture**, not a claim that every package currently exists.

Create packages incrementally when functionality requires them.

```text
endurance-coach/
├── .agents/                 # Codex / development factory
│   ├── skills/
│   └── validate_docs_impact.py
│
├── coach_skills/            # Runtime coaching skills
│   ├── plan-workout/
│   ├── analyze-training/
│   ├── assess-recovery/
│   └── adjust-plan/
│
├── data/                    # Local data and fixtures
│   └── synthetic_activities.json
│
├── docs/                    # Architecture and process
│   ├── agents/
│   ├── architecture.md
│   ├── process.md
│   └── testing-guidelines.md
│
├── src/
│   └── endurance_coach/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       │
│       ├── domain/
│       │   ├── __init__.py
│       │   └── models.py
│       │
│       ├── integrations/
│       │   ├── __init__.py
│       │   ├── coros_mcp.py
│       │   ├── intervals_icu.py
│       │   └── normalization.py
│       │
│       ├── analysis/
│       │   ├── __init__.py
│       │   └── metrics.py
│       │
│       ├── llm/
│       │   ├── __init__.py
│       │   ├── client.py
│       │   └── runtime.py
│       │
│       ├── skills/
│       │   ├── __init__.py
│       │   └── loader.py
│       │
│       ├── services/
│       │   ├── __init__.py
│       │   └── coaching.py
│       │
│       ├── storage/
│       │   ├── __init__.py
│       │   └── sqlite.py
│       │
│       └── fixtures/
│           ├── __init__.py
│           └── sample_data.py
│
├── tests/
│   ├── domain/
│   ├── integrations/
│   ├── analysis/
│   ├── llm/
│   ├── skills/
│   ├── services/
│   └── storage/
│
├── AGENTS.md
├── README.md
├── pyproject.toml
└── uv.lock
```

This structure represents intended responsibilities. **Do not create empty packages, placeholder files, or unused abstractions merely to match the diagram.**

The current flat modules remain valid until their owning issues justify migration.

### Module responsibilities

#### `domain/` — Business contracts

Contains the application's central Pydantic models, enums, validation rules, and data contracts.

Examples:

- `TrainingActivity`
- `WorkoutRecommendation`
- Workout and recovery data contracts
- Athlete profile and training-plan models

Rules:

- Domain models must not depend on external API clients, LLMs, or storage implementations.
- Units, optional values, constraints, and provenance must be explicit.
- Preserve strict validation at application boundaries.
- Keep domain logic independent of infrastructure.

#### `integrations/` — External connections

Contains clients and adapters for external providers.

Examples:

- `coros_mcp.py` — COROS MCP connectivity.
- `intervals_icu.py` — Intervals.icu API client.
- `normalization.py` — mapping external response fields into internal contracts.

Responsibilities:

- Authentication and connection management.
- API/MCP communication.
- Tool discovery and explicit allowlisting.
- Timeouts, pagination, and retries.
- External error handling.
- Source-specific response normalization.
- Provenance preservation.

Rules:

- One provider-specific module or cohesive package per integration.
- Provider SDK types and raw response formats must not leak into domain or analysis modules.
- Do not implement training calculations here.
- Do not embed LLM reasoning here.
- Keep external integrations read-only unless explicitly authorized.
- COROS MCP must expose only verified, explicitly allowed read-only operations.

#### `analysis/` — Deterministic calculations

Contains pure Python functions for training analysis.

Examples:

- Training volume.
- Intensity and load.
- Power metrics.
- Training trends.
- Durability.
- Recovery trends.

Rules:

- No LLM calls.
- No direct API/MCP calls.
- No database access.
- Prefer pure functions with typed inputs and outputs.
- Every calculation must document units, assumptions, missing-data behavior, and limitations.
- Never infer unavailable measurements without explicitly defining a supported estimation method.

#### `llm/` — Model interaction

Contains the product's LLM communication and execution logic.

Examples:

- Ollama client configuration and invocation.
- Agent conversation loop.
- Tool-call handling.
- Context management.
- Structured response generation.
- Output validation and retry policies.

Rules:

- Keep Ollama-specific transport code separate from the application workflow.
- LLMs must not perform calculations already implemented in `analysis/`.
- Do not give the LLM unrestricted access to external provider clients or credentials.
- Expose narrowly scoped tools through validated application interfaces.
- Validate all model-generated outputs with Pydantic.
- Keep model interaction local unless another provider is explicitly approved.
- Bound tool iterations, retries, and context size.

#### `skills/` — Runtime skill management

Contains Python code for discovering, validating, and loading runtime skills.

Examples:

- `SkillLoader`
- Skill metadata validation.
- Progressive skill loading.

Rules:

- Runtime skill instructions remain in `coach_skills/`.
- Discovery should load only necessary metadata.
- Full skill instructions are loaded explicitly on demand.
- Validate paths and prevent directory traversal.
- Never confuse runtime skills with development-agent skills under `.agents/`.

#### `services/` — Application workflows

Coordinates operations across modules.

Examples:

- Training analysis workflow.
- Recovery assessment workflow.
- Workout recommendation workflow.
- Activity synchronization workflow.
- Approval and plan-adjustment workflow.

Responsibilities:

- Coordinate integrations, analysis, storage, and LLM functionality.
- Enforce application-level rules.
- Handle workflows involving multiple components.
- Return validated domain objects.

Rules:

- Services orchestrate functionality; they should not become collections of unrelated business logic.
- Prefer explicit dependencies and testable interfaces.
- Keep provider-specific HTTP/MCP logic inside `integrations/`.
- Keep reusable mathematical calculations inside `analysis/`.
- Never bypass athlete approval requirements.

These are product application services, **not** the Dark Software Factory Orchestrator.

#### `storage/` — Persistence

Contains local database access and persistence adapters.

Examples:

- SQLite database initialization.
- Activity and plan repositories.
- Revision history.
- Approval records.
- Synchronization checkpoints.

Rules:

- Separate persistence operations from domain calculations.
- Use explicit transactions.
- Preserve provenance and auditability.
- Implement idempotent operations where appropriate.
- Never apply proposed training-plan changes without explicit user approval.
- Keep database paths and credentials configurable.

#### `fixtures/` — Synthetic data

Contains deterministic synthetic data generation and development fixtures.

Rules:

- Clearly identify synthetic data.
- Never silently mix synthetic and real athlete records.
- Do not store personal health records in committed fixtures.
- Use repeatable inputs and outputs.

#### `cli.py` and `config.py` — Application boundaries

`cli.py` contains command definitions, argument parsing, and presentation of results.

`config.py` contains typed configuration loaded from approved environment variables or local settings.

Rules:

- Keep the CLI thin; delegate substantial work to services.
- Separate Ollama, COROS, Intervals.icu, and storage configuration.
- Do not put business logic, API clients, or training calculations into CLI handlers.
- Do not hardcode tokens or secrets.
- Never expose secrets through diagnostic output.

### Dependency boundaries

Follow this general dependency direction:

```text
CLI
 |
 v
Application Services
 |          |           |
 v          v           v
Analysis   LLM        Integrations
 |          |           |
 +----------+-----------+
            |
            v
       Domain Models

Storage implements persistence
interfaces used by services.
```

The diagram is conceptual, not a requirement to introduce an interface for every class.

Rules:

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

Avoid redundant docstrings for trivial private helpers.

Keep documentation aligned with implementation.
