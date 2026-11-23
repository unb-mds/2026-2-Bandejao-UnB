---
name: review-status
description: Show status of all active review-to-pr fix branches and PRs. Use when user says 'review status', 'show fix status', 'what PRs are pending', or '/review-status'.
allowed-tools:
  - Bash
  - Read
metadata:
  mcpmarket-version: 1.0.0
---
# Review-to-PR Status

Display the current state of all active fix branches, PRs, and worktrees. Automatically cleans up worktrees for merged/closed PRs.

## Usage

```
/review-status
```

## Process

### 1. Run Status Check

```bash
bash "${CLAUDE_PLUGIN_ROOT}/lib/autofix.sh" --status
```

This will:
- Check all entries in `.review-to-pr/active.json`
- Query GitHub for current PR state (open/merged/closed)
- Automatically clean up worktrees for merged/closed PRs (lazy cleanup)
- Display remaining active entries

### 2. Present Results

Format the output clearly:
- For each active PR: show PR number, severity, URL, branch name, worktree path
- Highlight PRs that need attention (long-open, CI failing)
- Show count summary: "N active, M cleaned up this run"

### 3. Suggest Actions

Based on status:
- If there are old open PRs: suggest reviewing and merging
- If all clean: confirm "no active fix tasks"
- If worktree issues: suggest `/review-cleanup`
