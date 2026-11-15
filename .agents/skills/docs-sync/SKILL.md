---
name: docs-sync
description: Review repository changes and update only materially affected README.md and docs/ documentation when documentation maintenance is requested or useful.
---

# Docs Sync

Keep Endurance Coach documentation aligned with implemented repository behavior. This is an
optional development skill, not a release gate and not a runtime skill under `coach_skills/`.

## Workflow

1. Inspect the relevant implementation and current documentation.
2. Identify user-visible behavior, setup, architecture, configuration, safety, or testing guidance
   that materially changed.
3. Update only the smallest affected set under `README.md` and `docs/`.
4. Check claims against working code and review the documentation diff.

Do not require a GitHub issue, base SHA, candidate SHA, external report, validator, PM,
Orchestrator, independent QA, or pull request. Do not edit product code or tests merely to make the
documentation look correct. Preserve historical roadmap entries unless they are actively
misleading.

Summarize files updated, verified behavior, and any known limitation. A separate documentation
impact artifact is not required.
