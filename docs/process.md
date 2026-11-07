# Endurance Coach — Dark Software Factory Process

## Goal

Turn a GitHub issue into a verified, reproducible change using autonomous PM → Engineer → Documentation Impact Gate → QA work, with human intervention reserved for architecture, risk, policy, or unresolved ambiguity. The human evaluates product behavior and evidence rather than routinely reading implementation details.

**This is a delivery policy, not proof that unattended execution is configured.** A Codex session may orchestrate one issue today. Automated issue triggers, isolated runners, credential scopes, and PR automation must be implemented and validated separately before claiming continuous operation.

## Source of truth

- GitHub Issues: backlog, acceptance criteria, dependencies, discussion, and human decisions.
- `AGENTS.md`: project guardrails.
- Role documents in `docs/agents/`: role-specific responsibilities.
- `master`: integration branch; protection is tracked separately and must not be assumed.
- Documentation Impact Reports: external exact-commit evidence created by the tracked `docs-sync`
  skill and checked by the deterministic validator.
- CI/QA evidence: objective verification for the exact commit being reviewed.

## Lifecycle states

`BACKLOG → READY → SPECIFIED → IMPLEMENTING → DOC_REVIEW → VERIFYING → PR_READY → DONE`

Alternate paths:
- `NEEDS_HUMAN`: decisions or permissions needed; stop work without holding an active worker open.
- `FAILED`: implementation or verification failure; retry within limits or escalate.
- `BLOCKED`: missing dependencies, credentials, or environment support.

State transitions, retry limits, and permissions should ultimately be enforced by deterministic orchestration code rather than model judgment alone.

## One-issue execution loop

1. **Select:** Orchestrator chooses a dependency-ready issue. Do not skip ahead to blocked issues. Start with one implementation issue at a time until isolation is proven.
2. **Groom (PM):** Produce an executable specification: intended outcome, out-of-scope, acceptance scenarios, data contracts, dependencies, assumptions, risk level, and concrete demonstration evidence.
3. **Risk gate:** If the specification requires architecture changes, new credentials/scopes, security-sensitive behavior, or other listed escalations, mark `NEEDS_HUMAN` and present a short decision request. Otherwise proceed autonomously.
4. **Prepare isolated environment:** Create an issue-specific branch/worktree and keep a log of the base commit and environment. Never edit `master` directly.
5. **Implement (Engineer):** Complete the code, tests, fixtures and issue-authorized documentation. Run focused checks and the relevant project commands, commit the work, and identify the exact candidate SHA and explicit comparison base. The Engineer owns core mechanisms, including Agent Skills and Ollama integration.
6. **Review documentation impact:** Invoke `.agents/skills/docs-sync/SKILL.md` against that base and candidate. Update only materially affected `README.md` and `docs/` files, and state only behavior verified in the candidate code, tests, configuration, or approved specification. Commit any documentation edits, treat the new commit as the candidate, and repeat the review until the report describes the stable exact commit.
7. **Validate the Documentation Impact Report:** Store the report outside the candidate commit, normally as durable issue or pull-request evidence, with result `UPDATED`, `NO_DOC_CHANGE`, or `BLOCKED`. Run `.agents/validate_docs_impact.py` with the external JSON artifact and exact candidate SHA. Only a zero exit for a current `UPDATED` or evidence-based `NO_DOC_CHANGE` report permits QA assignment. Missing, unreadable, malformed, unknown, stale, or `BLOCKED` evidence stops progression. Any later commit invalidates the report and requires steps 6–7 again.
8. **Publish the verification candidate:** Push the issue branch and create or update its pull request. Record the exact head commit; automated CI starts from that pull-request event. A draft pull request may be used while verification is incomplete.
9. **Verify (QA and CI):** QA first confirms the documentation validator succeeded for the exact proposed commit, then uses a separate session or worker where possible to independently inspect specification compliance and run tests. QA refuses a missing, stale, malformed, or blocked documentation handoff, outputs `PASS` or `FAIL` with evidence, and never edits code. CI independently checks the exact pull-request head.
10. **On FAIL:** Return Engineer, documentation-gate, QA, or product/configuration CI failures to the Engineer for correction. Any correction creates a new candidate that must repeat documentation review and validation before independent QA and CI can establish current-head evidence. Allow no more than **2 automated fix attempts** by default; escalate after repeated failure or unreproducible checks. Classify CI platform outages and unavailable runners as infrastructure failures: retry when service recovers, but never count missing, cancelled, stale or unavailable CI as success.
11. **On PASS:** Mark the pull request `PR_READY` only when the Documentation Impact Gate, QA, every required CI and policy check, and all acceptance criteria pass for the same current head. A green unit-test run alone is not sufficient proof of the intended outcome.
12. **Integrate:** By default the human authorizes the merge based on specification, demo, documentation-impact evidence, QA evidence and risk summary. The issue can close when the change is integrated and behavior is verified. Automerge for low-risk issues requires a separately approved policy, configured branch protection, and required checks.
13. **Continue:** Orchestrator can select the next ready issue once the prior issue is integrated or the environment has proven safe isolation. It must honor stop conditions, dependencies and escalation states.

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

**Engineer → Documentation Impact Gate**
- Exact commit SHA and branch.
- Explicit base SHA used for comparison.
- Change summary and files affected.
- Commands executed with actual output/exit status.
- Known limitations and deviations.

**Documentation Impact Gate → QA**
- Human-readable report and external JSON artifact for the exact candidate SHA.
- Result: `UPDATED`, `NO_DOC_CHANGE`, or `BLOCKED`.
- Material-change assessment, affected documentation paths, verification performed, and any
  escalation or blocker.
- Successful `.agents/validate_docs_impact.py` output for the exact candidate; `BLOCKED` or failed
  validation does not proceed to QA.

**QA → Orchestrator**
- Verdict: PASS or FAIL.
- Validated Documentation Impact Report result and exact candidate SHA received.
- Each acceptance criterion mapped to observed evidence.
- Tests, demos and environment used.
- Unresolved defects or risks and reproducible failures.

**Orchestrator → Human (only as needed)**
- Decision request with options and consequences, or PR-ready evidence summary with the recommended action.
- Never send raw internal chain-of-thought. Include concise rationale and observed facts.

## Evidence layers and merge eligibility

- **Engineer evidence** records implementation-local commands and observed results. It demonstrates
  what the implementer checked, but is not independent verification.
- **Documentation-impact evidence** records a `docs-sync` review of the exact stable candidate and
  its explicit base. The deterministic validator proves report shape, outcome consistency, and SHA
  currency; it does not prove the review's judgment or replace QA.
- **Independent QA evidence** maps every acceptance criterion to behavior observed by a separate
  verifier at an exact commit. QA does not rely on the Engineer's report and does not modify code.
- **Automated CI evidence** is the repository-hosted result of required checks against the exact
  current pull-request head. CI provides a reproducible gate, but does not interpret product intent
  or replace QA.

A pull request is merge-eligible only when all acceptance criteria are satisfied, the Documentation
Impact Gate has a valid current `UPDATED` or `NO_DOC_CHANGE` report, independent QA is `PASS` for its
current head, every required CI check is successful for that same head, no blocker is unresolved,
and the human has explicitly authorized the merge. Any new commit invalidates prior documentation,
QA, and CI merge eligibility; all three gates must run again on the new head. Missing, cancelled,
stale, skipped or unavailable required evidence is not success. Required-check bypass is forbidden.

## Required PR evidence

A PR should provide:

1. Issue reference and one-paragraph behavioral summary.
2. Documentation Impact Report result, exact base/candidate SHAs, validator output, and artifact link.
3. Acceptance-criteria checklist with evidence links or logs.
4. Tests/CI run against the current commit, including failures and limitations.
5. Demonstration of user-observable behavior (CLI output, reproducible command, or suitable artifact).
6. Security and data-handling notes for relevant changes.
7. Architecture deviations and decisions escalated to the human.
8. QA verdict and remaining risks.

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

**Stage 1 — Agent-run issue, human merge:** Agents handle PM, Engineering, the Documentation Impact Gate, and QA end-to-end for one issue; human inspects evidence and authorizes merging. Establish current documentation, independent QA and trustworthy artifacts.

**Stage 2 — Repeatable pipeline:** Introduce explicit issue states, isolated runs, PR automation, CI branch protection and measured retry/escalation behavior. Orchestrator automatically selects the next ready issue.

**Stage 3 — Selective autonomous integration:** Consider auto-merging narrowly defined low-risk changes only after the human explicitly enables a tested policy. Retain human approval for architecture, security, training safety and third-party data access.

Do not describe Stage 2 or 3 as operational before the enabling infrastructure has been implemented and tested.
