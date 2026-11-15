---
name: implement-task
description: Implement a selected functional task as a usable vertical slice before formal testing. Use for concrete product development requests.
---

# Implement task

Deliver working product code, not another plan.

1. Read applicable AGENTS.md, inspect relevant files and check git status. Preserve existing user changes and respect repository permissions.
2. Implement the smallest complete solution using existing code. Avoid empty scaffolding, speculative abstractions and unrelated refactors.
3. Run a functional demonstration (CLI, sample import, query or equivalent). Fix defects until the core scenario works. If real local data is unavailable, use a clearly labelled synthetic fixture and disclose the limitation.
4. Hand the completed change to review-code for final verification. If invoked standalone, perform that verification before declaring the task complete.

During implementation, do not write new tests or run the full suite. Targeted diagnostic commands are allowed when genuinely needed to unblock coding. Do not create PM reports, governance tests, or new issues. Do not repeatedly revisit acceptance criteria.

Keep credentials, personal activities and GPS data out of Git and logs. Preserve nulls and provenance, avoid duplicates, use read-only external integrations, and never apply training-plan changes without explicit athlete approval. Do not add unapproved dependencies or perform destructive operations.

Report the working command, observed result, files changed and remaining blockers. If a demonstration cannot succeed, report incomplete rather than claiming delivery.