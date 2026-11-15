# Endurance Coach development process

## Purpose

Deliver working product behavior with the smallest process that preserves correctness, athlete
safety, privacy, and data integrity.

## Default workflow

1. Implement the requested functionality.
2. Demonstrate it through a representative CLI command or end-to-end use case.
3. Add essential automated tests for the implemented behavior and important failure paths.
4. Run final verification once the work is stable:

```bash
uv run pytest
uv run ruff check .
```

Intermediate diagnostics and focused tests are optional. They may be used when useful, but no
intermediate test execution is a release requirement.

## Optional collaboration and repository artifacts

GitHub issues, feature branches, worktrees, pull requests, specifications, PM review, orchestration,
independent QA, and documentation review are optional. Use them when they help the work or when
actual repository permissions require them. They are not prerequisites for implementation and do
not form a mandatory lifecycle.

Repository permissions and branch protection remain authoritative. Never bypass them. External
writes, commits, pushes, pull requests, merges, and issue changes require the relevant authorization.

## Documentation

Update affected documentation when product behavior, setup, architecture, or safety constraints
materially change. Documentation review does not require a separate gate, report, validator, exact
commit handoff, or independent role.

## Escalation

Proceed autonomously on routine implementation choices within the documented architecture. Ask for
direction before destructive operations, new external write permissions, disclosure of private
athlete data, changes to athlete-approval safeguards, or a consequential product or architecture
decision that the request does not resolve.

## Evidence

The final report should state what was implemented, how it was demonstrated, the actual outcomes of
the two final verification commands, and any limitations. Do not claim commands or behavior that
were not run or observed.
