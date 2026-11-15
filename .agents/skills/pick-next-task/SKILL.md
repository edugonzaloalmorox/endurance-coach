---
name: pick-next-task
description: Select the next actionable development task from product objectives, current implementation, dependencies, and functional value. Use when deciding what to implement next.
---

# Pick Next Task

Identify the single highest-value actionable task that advances current product objectives. Prioritize working software and vertical functional slices over governance, documentation, or architectural completeness.

## Gather context

Inspect only what is needed to decide: the roadmap, current implementation, recent commits, current milestone, unfinished functionality, and open GitHub issues when available. Issues are informative, not prerequisites.

Do not perform a comprehensive audit or run tests during selection.

## Select

Consider up to three candidates, then choose exactly one that:

1. Delivers directly usable functionality.
2. Advances the current milestone or unblocks later work.
3. Has essential dependencies satisfied.
4. Is achievable with reasonable effort.

Prefer finishing incomplete functionality. Deprioritize governance, documentation-only work, testing infrastructure, speculative abstractions, non-functional refactoring, and out-of-scope features unless they directly block delivery or mitigate material risk.

## Output

In fewer than 300 words, return:

- Selected task and existing issue number, if applicable.
- Why it is the best next task.
- Expected functional deliverable.
- Relevant implementation files.
- Up to three acceptance criteria.

Define the task directly when no issue covers it. Do not create issues, planning documents, or backlog changes; spawn PM or QA agents; run verification commands; repeatedly reassess requirements; or request approval for routine selection.

When explicitly asked to select and implement the next task, proceed immediately after selection and follow the implementation-first workflow in `AGENTS.md`.

Selection is complete once one actionable functional deliverable is identified.
