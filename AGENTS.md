# Endurance Coach — Issue Development Process

## Purpose

Develop Endurance Coach **one GitHub issue at a time** while preserving the guided-learning model. Codex prepares scaffolding, contracts, fixtures, and tests; the human developer implements core agent/skill mechanisms and approves consequential actions.

Do not treat the backlog as permission to autonomously complete all issues.

## Source of truth

- **GitHub Issues** define tasks, ownership, dependencies, and acceptance criteria.
- **`AGENTS.md`** defines project-wide instructions and learning boundaries.
- **The current issue** is the unit of implementation and review.
- **`main`** is the stable integration branch; use a short-lived branch per issue when working with Git.

Read the issue's acceptance criteria **before implementation and again before verification**.

## Roles

**Orchestrator**
- Coordinates PM → Engineer → QA for a single selected issue.
- Records handoffs and blockers; does not groom, implement, or verify on behalf of those roles.
- Uses actual subagents where supported; otherwise makes role handoffs explicit.
- Does not close an issue or launch another one without the human's authorization.

**PM** (`docs/agents/pm.md`)
- Checks milestone dependencies and ensures the issue is small enough to verify.
- Defines the scope, acceptance criteria, deliverables, and out-of-scope work.
- Identifies **Codex-owned** vs. **human-owned** implementation steps.
- Flags new dependencies, external permissions, and unclear requirements.

**Engineer** (`docs/agents/software-engineer.md`)
- Works only on a groomed and human-approved issue.
- For human-owned learning tasks, prepares interfaces and tests or offers review; **does not implement the core exercise** without an explicit request.
- Implements supporting code, runs focused checks, and reports limitations.
- Commits meaningful increments on the issue branch after authorization; does not push/merge/close issues automatically.

**QA Engineer** (`docs/agents/qa-engineer.md`)
- Checks behavior against the issue's acceptance criteria and executes relevant tests.
- Produces **PASS** or **FAIL**, with reproducible evidence.
- Does not modify code, weaken tests, or redefine acceptance criteria to force a PASS.

## Lifecycle — one issue

1. **Select:** Human selects the next ready GitHub issue. Verify dependencies and branch state; do not automatically select the entire backlog.
2. **Groom (PM):** Read the issue, determine scope, acceptance criteria, dependencies, and whether the task contains a human-learning exercise.
3. **Approve scope (human):** The human approves the groomed plan. If unclear, resolve ownership before coding.
4. **Prepare branch:** Update local `main` and create a branch such as `feat/m1-05-skill-loader`; avoid mixing unrelated issues.
5. **Implement (Engineer + human):** Execute only the approved work. Codex may write scaffolding, fixtures, and tests; the human implements reserved mechanisms. Work in small steps and commit regularly **with authorization**.
6. **Verify (QA):** Run relevant checks, review tests and acceptance criteria, and report evidence-backed **PASS** or **FAIL**.
7. **On FAIL:** Return the QA findings to the Engineer/human as appropriate. Fix the issue and repeat step 6. Never bypass failing tests or assign fixes to QA.
8. **On PASS:** Summarize results, outstanding limitations, and learning outcomes. Present the changes to the human for review. QA PASS does not grant permission to merge or close.
9. **Integrate and close (human-approved):** Create/review a PR as appropriate; merge only after explicit authorization. Close the GitHub issue only once QA has passed, the required review is complete, and the change is integrated (or the human explicitly authorizes another closure path).
10. **Stop:** Await human selection of the next issue. Do not automatically repeat the lifecycle for all remaining issues.

## Required handoff information

**PM → Engineer:** issue ID/link; task goal; acceptance criteria; dependencies; implementation boundaries; owner of each learning-critical step; files likely affected.

**Engineer → QA:** summary of changes; changed files; commands executed and real results; tests added; known limitations; human-owned tasks still incomplete.

**QA → Orchestrator/human:** `PASS` or `FAIL`; acceptance-criteria checklist; commands and outcomes; concrete defect reports or unresolved blockers.

## Testing and learning gates

- Read `_docs/testing-guidelines.md` **before writing or modifying tests**.
- Run focused tests during development and `uv run pytest` plus `uv run ruff check .` when the issue is ready for final QA, if available.
- Offline fixtures and mocks should test agent logic without requiring Ollama, COROS, or Intervals.icu.
- Do not claim live integrations were validated unless they were actually called successfully.
- If tests intentionally fail because a human-owned exercise is incomplete, report that state honestly; the issue remains **in progress**, not PASS.
- For a human-learning issue, the developer should be able to explain inputs, outputs, failure modes, and the boundary between a skill, a tool, and Python business logic before closure.

## Safeguards

- No new dependencies without asking the human first.
- No remote source writes to COROS or Intervals.icu during the MVP.
- No autonomous plan changes. Proposals must be reviewed and explicitly approved before changing local plans.
- No secrets or sensitive athlete information in commits, debug traces, or test fixtures.
- Do not commit to `main` directly unless the human explicitly requests it.

## Example: M1-05 — SkillLoader

- **PM:** Groom discovery, frontmatter parsing, safe paths, and progressive-loading acceptance criteria.
- **Codex Engineer:** Create the loader interface, fixtures, and tests; leave core discovery/loading methods for the developer.
- **Human developer:** Implement discovery and `load_skill()`.
- **QA:** Check valid metadata, unknown names, malformed files, traversal protections, and that full instructions are loaded only on activation.
- **Orchestrator:** Report QA result; await human review and authorization before closing the issue.