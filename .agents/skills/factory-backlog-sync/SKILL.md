---
name: factory-backlog-sync
description: Audit optional GitHub issues and pull requests against local branches and commits, and safely push already-committed changes to an explicitly authorized branch when requested.
---

# Backlog Sync

Use this optional skill when the user asks to reconcile GitHub issues, pull requests, branches, or
unpushed commits. Issues, issue-linked branches, and pull requests are not required for ordinary
development.

## Audit

Inspect repository status, branches, worktrees, remotes, open issues, and pull requests. Report only
relationships supported by branch, commit, PR, or issue evidence; do not infer ownership from a
branch name alone. Never stage, commit, stash, reset, discard, or modify uncommitted work during an
audit.

## Authorized push

Push only when the user explicitly authorizes the exact branch or task. Before pushing, confirm the
working tree is clean, the remote target is correct, no force push is needed, no secrets or private
athlete data are included, and the mandatory final checks passed:

```bash
uv run pytest
uv run ruff check .
```

Never force push, rewrite history, merge pull requests, close issues, delete branches, or push to a
protected branch in violation of repository permissions. A successful push proves only that the
remote received the commit.
