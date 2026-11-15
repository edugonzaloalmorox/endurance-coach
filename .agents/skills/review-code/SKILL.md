---
name: review-code
description: Review completed product code and perform proportionate final verification. Use after implementation and functional demonstration, or for an explicit code review.
---

# Review code

Verify the delivered behavior, not compliance with obsolete factory procedures.

1. Inspect the change and its acceptance criteria. Check correctness, regressions, security, privacy and data integrity. For sports metrics, check units, assumptions and missing-data behavior.
2. For delivery verification, add only essential missing regression or behavior tests. Preserve meaningful existing tests. For review-only requests, do not edit files unless asked.
3. During delivery verification, run focused checks only if useful, then run the final checks once: `uv run pytest` and `uv run ruff check .`. Respect any applicable repository requirements. Do not rerun successful checks without a relevant change.
4. Report actual outcomes, including failures, skipped checks and concrete findings with file locations. Never claim independent QA unless an independent reviewer actually participated.
5. Commit if all tests PASS

Return PASS, FAIL or BLOCKED for delivery verification, plus a concise summary. If verification fails, return actionable findings to implement-task; after repair, repeat only affected checks and final verification as needed. Stop after two failed repair cycles and report the blocker. Never weaken product tests to obtain a pass.

Update user-facing documentation only where behavior or usage changed. Do not introduce process tests, governance reports or unrelated cleanup.