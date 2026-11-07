---
name: docs-sync
description: Review substantial repository changes and update only the affected README.md and docs/ documentation. Use before QA when code, interfaces, architecture, configuration, CI, or governance behavior changes; report a justified no-op for non-material changes.
---

# Docs Sync

Keep Endurance Coach documentation aligned with verified repository behavior. This is a **development-agent skill**, not a runtime skill under `coach_skills/`.

## When to run

- Run after the Engineer's implementation stabilizes and **before** independent QA and PR release evidence.
- Re-run if subsequent engineering changes invalidate the documentation review.
- Do not run on every Codex/Ralph iteration or rewrite documents for formatting-only changes.
- The Orchestrator or Engineer should invoke this skill explicitly; merely installing it does not guarantee activation.

## Inputs

- Current issue and its approved acceptance criteria, where available.
- The implementation branch/worktree and its intended base (normally `master`).
- The current repository files, tests, CLI, configuration, and CI workflows.

If the intended comparison base is ambiguous, report `BLOCKED` rather than inventing a diff.

## Workflow

### 1. Establish what actually changed

Read `AGENTS.md` and the relevant sections of `docs/process.md`. Inspect the repository state:

```bash
git status --short
git merge-base HEAD master
git diff --name-status "$(git merge-base HEAD master)"
git diff --stat "$(git merge-base HEAD master)"
```

Use an explicitly supplied base SHA when available. Account for untracked files shown in `git status`. Do not fetch, switch branches, or overwrite existing work. Read the meaningful source and test changes, not just file names. Distinguish implemented behavior from proposed future behavior.

### 2. Decide whether the change is material

Documentation impact is **material** when the change alters at least one of:

- User-visible CLI commands, setup instructions, configuration, dependencies, or supported behavior.
- Public data contracts, validation rules, API/MCP interfaces, error behavior, or compatibility.
- Agent runtime, skills discovery/loading, tool calling, retrieval, data flows, or component boundaries.
- Persistence, authentication, authorization, privacy, safety, or athlete approval requirements.
- CI checks, testing policy, release gates, orchestration states, or development-agent responsibilities.
- Availability, limitations, and status of integrations or other capabilities advertised as working.

A change is **usually not material** when it only reformats code, renames a private helper, adds implementation-only tests without changing documented behavior, or refactors internals without changing a documented contract. Examine the actual effects; never rely only on filenames or change size.

A documentation-only PR may still be material if it changes an approved operational policy.

If nothing material changed, make **no documentation edits** and return a specific `NO_DOC_CHANGE` report explaining why.

### 3. Choose the smallest relevant document set

| Document | Update when |
| --- | --- |
| `README.md` | User/contributor setup, commands, advertised capabilities, maturity, or major limitations change. |
| `docs/architecture.md` | Components, data flow, boundaries, public contracts, or significant technical decisions change. |
| `docs/process.md` | Approved factory lifecycle, handoffs, permissions, QA/CI gates, or escalation process change. |
| `docs/testing-guidelines.md` | Approved testing practices, required checks, evidence policy, or deferred-test rules change. |
| `docs/exercises.md` | Ownership/status of deferred executable specifications changes. |
| `docs/agents/*.md` | An approved change affects that development-agent role or handoff. |

Other active documents under `docs/` may be updated **only when directly impacted**.

Treat `docs/tasks.md` and `docs/endurance_coach_development_plan_en.md` as planning/reference snapshots rather than live implementation status: do not rewrite history, owners, or the roadmap merely to reflect completion. Link a necessary correction to its issue or request an explicit decision.

`AGENTS.md` governs repository instructions: read it, but do **not** change its policy or other files outside `README.md` and `docs/` under this skill without scope approval.

### 4. Make minimal, evidence-based edits

- Inspect existing sections first; update them in place instead of duplicating explanations.
- State only what code, tests, configuration, and approved specifications support at the reviewed commit.
- Separate **implemented**, **partially implemented**, **planned**, and **not verified** behaviors.
- Do not fabricate CLI output, endpoints, permissions, benchmark metrics, test results, or real-athlete data.
- Preserve architectural rationale, existing links, intentional historical records, and agreed terminology.
- Keep commands copyable and paths relative to the repository.
- Prefer concise prose and diagrams already used in the repository.
- If the proposed edit would change product scope, architecture policy, safety rules, or acceptance criteria, stop and escalate to the Orchestrator. Documentation cannot approve its own policy changes.
- Do not edit application code, tests, GitHub issues, or pull-request state to make documentation appear correct.

### 5. Verify documentation

- Review `git diff -- README.md docs/` and `git diff --check`.
- Check relative links and referenced files exist; flag external links that cannot be verified.
- For commands or examples that changed, run safe deterministic verification where feasible; otherwise label them **not verified**.
- Confirm statements about implemented behavior against the current code and tests.
- Confirm that active documents do not contradict one another or `AGENTS.md`.
- Follow any additional required repository verification from `docs/testing-guidelines.md`; report exactly what ran and what did not.

If verification fails, fix only documentation issues within scope or report `BLOCKED`. Never weaken tests, skip checks, or claim CI/QA PASS.

## Required output: Documentation Impact Report

Return:

- **Result:** `UPDATED`, `NO_DOC_CHANGE`, or `BLOCKED`.
- **Compared against:** base ref/SHA and reviewed working-tree or commit state.
- **Material changes:** concise mapping from verified change to documentation impact.
- **Files updated:** paths and what changed (or a specific no-op justification).
- **Validation:** exact commands/checks, results, and limitations.
- **Escalations:** unresolved ambiguity, policy changes, missing evidence, or required follow-up issues.

A report is **engineering evidence**, not independent QA approval. Hand the implementation and documentation changes to QA; the Orchestrator still enforces CI and human merge authorization.
