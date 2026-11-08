---
name: factory-backlog-sync
description: Audit and synchronize the Endurance Coach development backlog with local Git branches, commits, and GitHub pull requests. Use this skill when reviewing repository progress, identifying unpushed commits, detecting stale or inconsistent issue/PR states, or cleaning up pending development work. It can safely push already-committed changes to explicitly authorized feature branches after verification. Never merge PRs, close issues, delete branches, rewrite history, or modify uncommitted work.
---

# Factory Backlog Sync

## Purpose

Keep the GitHub backlog and local repository state consistent without bypassing the Dark Software Factory's quality gates.

Follow `AGENTS.md` and `docs/process.md`.

## Operating Modes

- **AUDIT (default):** Inspect repository state and report inconsistencies without modifying anything.
- **PUSH_AUTHORIZED:** Audit and push eligible commits from an explicitly authorized feature branch.

## Workflow

### 1. Inspect Git State

Run:

```bash
git status --short --branch
git branch -vv
git remote -v
git worktree list
```

Identify:
- Unpushed commits
- Uncommitted changes
- Divergent branches
- Missing upstream branches
- Branches already synchronized with origin

Never automatically stage, commit, stash, reset, or discard changes.

### 2. Audit GitHub Backlog

Use GitHub CLI or the available GitHub integration to inspect open issues and pull requests.

```bash
gh issue list --state open --limit 200
gh pr list --state all --limit 200
```

Identify:
- Open issues associated with merged PRs
- PRs awaiting QA, CI, or human approval
- Issues with missing or unpublished implementation branches
- Potentially stale or inconsistent issue states

Use verified issue-to-branch and PR relationships. Do not infer ownership from naming alone.

### 3. Identify Pending Commits

For each relevant branch, inspect its upstream:

```bash
git log --oneline @{upstream}..HEAD
git rev-list --left-right --count @{upstream}...HEAD
```

Classify branches as:

- `SYNCED`
- `AHEAD`
- `BEHIND`
- `DIVERGED`
- `NO_UPSTREAM`
- `DIRTY`

Only branches that are ahead of their verified upstream and not behind are candidates for automatic publication.

### 4. Validate Before Push

Before pushing, verify that:

1. The specific feature branch is explicitly authorized.
2. The branch is associated with an approved GitHub Issue.
3. The working tree is clean.
4. The remote and upstream are correct and current.
5. No force push or history rewrite is required.
6. Commits remain within the approved issue scope.
7. No secrets or sensitive data are included.
8. Required tests and linting pass.

```bash
git diff --check @{upstream}..HEAD
uv run pytest
uv run ruff check .
```

If any condition fails, stop and report `BLOCKED` or `NEEDS_HUMAN`.

### 5. Push Authorized Commits

Only in `PUSH_AUTHORIZED` mode, push the verified current feature branch:

```bash
git push origin HEAD:refs/heads/<verified-feature-branch>
```

Replace the placeholder with the verified branch name.

Never:
- Force push
- Push directly to `master`
- Automatically create an upstream
- Merge pull requests
- Close GitHub Issues
- Delete branches
- Rewrite Git history

Verify the remote SHA after pushing.

### 6. Generate Report

Produce a concise **Factory Backlog Sync Report** containing:

- Repository and current branch
- Backlog inconsistencies
- Branches with pending commits
- Related GitHub issues and PRs
- Commits pushed, if any
- Test and verification results
- Remaining blockers
- Actions requiring human approval

Use one of the following outcomes:

`AUDIT_ONLY`, `PUSHED`, `NOTHING_TO_PUSH`, `BLOCKED`, `NEEDS_HUMAN`.

## Factory Integration

Invoke this skill after Engineering has committed its changes, before the PR verification handoff, or during periodic backlog maintenance.

The Orchestrator owns issue selection, QA handoffs, CI verification, and lifecycle transitions.

A successful push does not imply QA approval, CI success, or merge eligibility.
