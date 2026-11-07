# Endurance Coach — Dark Software Factory Instructions

## Mission

Endurance Coach is a Python AI cycling coach for long-distance training and an experiment in **agent-driven software delivery**. The human acts as **Product Owner and AI Architect**: they set goals, architecture, constraints, and acceptance outcomes; agents plan, implement, synchronize affected documentation, verify, and produce evidence. Human code review is optional, not a routine release gate.

The product's runtime skills in `coach_skills/<skill-name>/SKILL.md` are distinct from development-agent skills that guide Codex. Do not confuse these two systems.

Read `docs/process.md` before selecting or executing any work.

## Commands

- `uv sync` — synchronize dependencies.
- `uv run pytest` — full test suite.
- `uv run pytest tests/<test_file>.py` — focused tests.
- `uv run ruff check .` — linting.

Use only commands actually configured in the repository. Report exact command results; never claim tests or integrations passed without executing them.

## Documents

- `docs/process.md` — factory lifecycle, autonomy, escalation, and release gates.
- `docs/testing-guidelines.md` — read before writing or modifying tests.
- `docs/design-system.md` — read for UI-affecting work, if applicable.
- `docs/agents/pm.md` — PM role definition.
- `docs/agents/software-engineer.md` — Engineer role definition.
- `docs/agents/qa-engineer.md` — QA role definition.
- `.agents/skills/docs-sync/SKILL.md` — pre-QA Documentation Impact Gate procedure.
- `.agents/validate_docs_impact.py` — deterministic exact-commit report validator.

If a referenced document is missing, report it. Do not pretend to have read it. Preserve repo conventions when they are compatible with these rules.

## Roles

- **Orchestrator:** Coordinates the lifecycle, selects only dependency-ready issues, records states, delegates role tasks, validates the exact-commit Documentation Impact Report before assigning QA, and enforces retry limits and escalations. Does **not** groom, implement, review documentation, or verify code. Prefer a deterministic state machine for routing and permissions; an LLM may assist in prioritization but must not override gates.
- **PM:** Transforms a GitHub issue into an executable specification: scope, acceptance scenarios, dependencies, risk classification, assumptions, and out-of-scope. Escalates consequential ambiguity. Follows `docs/agents/pm.md`.
- **Engineer:** Implements the approved specification, identifies an exact candidate commit for documentation review, adds appropriate tests, runs checks, and opens or updates a PR if authorized by the execution environment. Owns all implementation, including skill loading, agent loop, MCP connectors, and approval workflows. Follows `docs/agents/software-engineer.md`.
- **Documentation Impact Gate:** The `docs-sync` development-agent skill reviews the exact candidate against its explicit base after Engineering and before QA. It updates only materially affected `README.md`/`docs/` content, records `UPDATED`, `NO_DOC_CHANGE`, or `BLOCKED`, and produces an external report validated by `.agents/validate_docs_impact.py`. This evidence is not independent QA.
- **QA Engineer:** Reviews the implementation independently in a separate context when possible; refuses a handoff without a successfully validated current Documentation Impact Report, checks acceptance scenarios, executes objective tests, and outputs PASS/FAIL with evidence. Does not modify code, weaken tests, or accept self-reported success. Follows `docs/agents/qa-engineer.md`.
- **Human Product Owner / AI Architect:** Sets product direction, decides architecture, approves high-impact deviations and permissions, and assesses demos, reports, and runtime outcomes. May inspect code selectively when risks justify it, but is not expected to review every diff.

Use real subagents only when supported. Otherwise, perform clearly separated sequential role passes and disclose the limitation; never claim independence that was not achieved.

## Autonomy boundaries

Agents **may execute without per-step approval** when an issue is ready, its specification is unambiguous, dependencies are satisfied, the change stays within the agreed architecture, and permissions permit it. They may update code, run tests, and prepare evidence and PRs.

**Escalate to the human** before proceeding when:
- A new architectural direction, framework, model provider, deployment platform, or significant dependency is proposed.
- Requirements or acceptance criteria conflict, are materially ambiguous, or require changing product behavior beyond the issue.
- New external credentials, OAuth scopes, data sharing, permissions, or writes to COROS/Intervals.icu are required.
- A change affects training safety constraints, human approval requirements, or sensitive athlete data handling.
- QA cannot establish correctness, required tests are unavailable, or retry limits are reached.
- A destructive migration, irreversible operation, or a change to GitHub/CI branch-protection policy is needed.

Do not ask for human approval for trivial implementation choices already allowed by the specification.

## Execution and release rules

- GitHub Issues are the backlog and acceptance source of truth. Follow the lifecycle in `docs/process.md`.
- Work only on ready issues with satisfied dependencies. Prefer one active implementation issue initially; expand concurrency only with isolated worktrees and reliable CI.
- Each change must occur in an issue-specific branch or isolated worktree. Never implement directly on `master`.
- Do not change acceptance criteria after implementation to manufacture a PASS.
- Before QA PASS, complete applicable unit/integration tests, linting, safety and secret checks. Verify actual behavior, not just exit codes.
- After Engineering stabilizes and before QA starts, invoke `.agents/skills/docs-sync/SKILL.md`, record a Documentation Impact Report for the exact candidate commit, and run `.agents/validate_docs_impact.py`. Only a valid current `UPDATED` or `NO_DOC_CHANGE` report permits QA assignment; missing, stale, malformed, or `BLOCKED` evidence stops progression.
- Any later implementation or documentation commit changes the candidate SHA and invalidates the earlier documentation report. Re-run `docs-sync` and its validator before assigning or resuming QA.
- Preserve a reproducible **evidence package** with: spec/acceptance mapping, commands and outputs, changed behavior, QA PASS/FAIL, unresolved risks, and human decisions.
- Agents may commit and push an isolated issue branch and create/update a PR only when repository tooling and credentials explicitly authorize it. Do not infer permission from these written instructions alone.
- **Merging and closing issues remain human-controlled by default.** Low-risk auto-merge may be enabled later only through an explicit human-approved policy backed by protected branches and required CI. No agent may bypass branch protection.
- If QA FAILs, return evidence to the Engineer for fixes. Cap automatic retries (default: 2) and escalate persistent failures.

## Product safety and privacy

- Ollama inference is local. Do not send athlete data to unapproved external LLMs.
- Intervals.icu is the primary source for training activities; COROS is complementary. Reconcile synchronized activities to prevent double counting.
- Treat COROS and Intervals.icu access as read-only for the MVP. Never write to third-party platforms without a new approved scope.
- Missing power, HRV, sleep, or recovery metrics remain missing; never invent values or represent proxies as directly measured.
- Weekly training is planned around a default 9-hour schedule, adjustable by the user; strength is variable by training phase.
- **No proposed workout-plan modification may be applied without the athlete's explicit approval.** The factory's authority to change source code never grants the product agent authority to change an athlete's plan.
- Store tokens securely, use least-privilege scopes, and keep secrets and personal records out of commits, logs, fixtures, and PR evidence.

## Python documentation standards

For public Python modules, classes, methods, and functions, write complete Google-style docstrings explaining purpose and behavior, including `Args`, `Returns`, `Raises`, and `Yields` where applicable. Document units, constraints, side effects, assumptions, and limits. Keep docstrings aligned with implementation. Avoid redundant docstrings on trivial private helpers.

## Completion report

For each issue, produce a concise factory report with: issue ID, specification version, implementation summary, Documentation Impact Report result and exact candidate SHA, acceptance-criteria evidence, tests and their actual outcomes, QA verdict, risks, deviations, links to PR/artifacts, and whether human input is needed. Reports should enable product-level decisions without requiring routine code inspection
