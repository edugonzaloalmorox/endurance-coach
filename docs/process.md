# Endurance Coach — Dark Software Factory Process

## Goal

Turn a GitHub issue into a verified, reproducible change using autonomous PM → Engineer → QA work, with human intervention reserved for architecture, risk, policy, or unresolved ambiguity. The human evaluates product behavior and evidence rather than routinely reading implementation details.

**This is a delivery policy, not proof that unattended execution is configured.** A Codex session may orchestrate one issue today. Automated issue triggers, isolated runners, credential scopes, and PR automation must be implemented and validated separately before claiming continuous operation.

## Source of truth

- GitHub Issues: backlog, acceptance criteria, dependencies, discussion, and human decisions.
- `AGENTS.md`: project guardrails.
- Role documents in `docs/agents/`: role-specific responsibilities.
- `main`: protected integration branch.
- CI/QA evidence: objective verification for the exact commit being reviewed.

## Lifecycle states

`BACKLOG → READY → SPECIFIED → IMPLEMENTING → VERIFYING → PR_READY → DONE`

Alternate paths:
- `NEEDS_HUMAN`: decisions or permissions needed; stop work without holding an active worker open.
- `FAILED`: implementation or verification failure; retry within limits or escalate.
- `BLOCKED`: missing dependencies, credentials, or environment support.

State transitions, retry limits, and permissions should ultimately be enforced by deterministic orchestration code rather than model judgment alone.

## One-issue execution loop

1. **Select:** Orchestrator chooses a dependency-ready issue. Do not skip ahead to blocked issues. Start with one implementation issue at a time until isolation is proven.
2. **Groom (PM):** Produce an executable specification: intended outcome, out-of-scope, acceptance scenarios, data contracts, dependencies, assumptions, risk level, and concrete demonstration evidence.
3. **Risk gate:** If the specification requires architecture changes, new credentials/scopes, security-sensitive behavior, or other listed escalations, mark `NEEDS_HUMAN` and present a short decision request. Otherwise proceed autonomously.
4. **Prepare isolated environment:** Create an issue-specific branch/worktree and keep a log of the base commit and environment. Never edit `main` directly.
5. **Implement (Engineer):** Complete the code, tests, fixtures and documentation necessary for the issue. Run focused checks and the relevant project commands. The Engineer owns core mechanisms, including Agent Skills and Ollama integration.
6. **Verify (QA):** Use a separate session or worker where possible. Independently inspect spec compliance and run tests against the exact proposed commit. QA outputs `PASS` or `FAIL`, with evidence, and never edits code.
7. **On FAIL:** Return the report to the Engineer for correction, then rerun QA. Allow no more than **2 automated fix attempts** by default; escalate after repeated failure or unreproducible checks.
8. **On PASS:** Prepare or update a PR, attach an evidence report, and mark `PR_READY`. Validate all required CI and policy checks for the final commit. A green unit-test run alone is not sufficient proof of the intended outcome.
9. **Integrate:** By default the human authorizes the merge based on specification, demo, QA evidence and risk summary. The issue can close when the change is integrated and behavior is verified. Automerge for low-risk issues requires a separately approved policy, configured branch protection, and required checks.
10. **Continue:** Orchestrator can select the next ready issue once the prior issue is integrated or the environment has proven safe isolation. It must honor stop conditions, dependencies and escalation states.

## Human escalation policy

**Escalate for:**
- Significant architecture or interface changes.
- New dependencies or model/provider changes outside approved constraints.
- Secrets, OAuth scopes, network permissions or third-party writes.
- Ambiguous/conflicting acceptance criteria affecting behavior.
- Training-safety, athlete approval, or personal-data protections.
- Destructive operations, failing CI that cannot be resolved, or exhausted retry limits.

**Do not escalate for:** naming, routine refactoring inside agreed boundaries, writing ordinary unit tests, or simple implementation tradeoffs covered by the spec.

## Handoff contracts

**PM → Engineer**
- Issue link and dependency status.
- Spec and acceptance scenarios with observable expected results.
- Allowed architecture and interfaces.
- Risk classification, assumptions and explicit out-of-scope.

**Engineer → QA**
- Exact commit SHA and branch.
- Change summary and files affected.
- Commands executed with actual output/exit status.
- Known limitations and deviations.

**QA → Orchestrator**
- Verdict: PASS or FAIL.
- Each acceptance criterion mapped to observed evidence.
- Tests, demos and environment used.
- Unresolved defects or risks and reproducible failures.

**Orchestrator → Human (only as needed)**
- Decision request with options and consequences, or PR-ready evidence summary with the recommended action.
- Never send raw internal chain-of-thought. Include concise rationale and observed facts.

## Required PR evidence

A PR should provide:

1. Issue reference and one-paragraph behavioral summary.
2. Acceptance-criteria checklist with evidence links or logs.
3. Tests/CI run against the current commit, including failures and limitations.
4. Demonstration of user-observable behavior (CLI output, reproducible command, or suitable artifact).
5. Security and data-handling notes for relevant changes.
6. Architecture deviations and decisions escalated to the human.
7. QA verdict and remaining risks.

A PASS is invalid if QA merely repeats the Engineer's claims without checking them.

## Monitoring and factory health

Track per milestone:
- Lead time: READY → PR_READY and READY → DONE.
- First-pass QA rate and mean retries per issue.
- CI failure and regression rate after merge.
- Human escalations per issue, distinguishing necessary and avoidable interruptions.
- Rework, reopened issues, and time spent fixing recurrent failures.
- Time or cost per completed issue where observable.
- Product-level acceptance: does the cycling coach behave as specified with synthetic scenarios and eventually real read-only integrations?

Review the factory process when these metrics deteriorate; do not optimize only for issue throughput.

## Product-specific gates

- Test skill discovery, on-demand skill loading, correct tool use, and structured recommendation validation with deterministic fixtures.
- Test incomplete/missing sports metrics, duplicate activity reconciliation, and unsafe training recommendations.
- Verify that no training-plan changes are applied without explicit athlete approval.
- Use mock COROS/Intervals.icu clients in CI. Live access must use properly scoped credentials and must not be claimed as tested until observed.
- Run `uv run pytest` and `uv run ruff check .` when configured; include security checks appropriate to the change.

## Rollout of factory autonomy

**Stage 1 — Agent-run issue, human merge:** Agents handle PM/Engineer/QA end-to-end for one issue; human inspects evidence and authorizes merging. Establish independent QA and trustworthy artifacts.

**Stage 2 — Repeatable pipeline:** Introduce explicit issue states, isolated runs, PR automation, CI branch protection and measured retry/escalation behavior. Orchestrator automatically selects the next ready issue.

**Stage 3 — Selective autonomous integration:** Consider auto-merging narrowly defined low-risk changes only after the human explicitly enables a tested policy. Retain human approval for architecture, security, training safety and third-party data access.

Do not describe Stage 2 or 3 as operational before the enabling infrastructure has been implemented and tested.