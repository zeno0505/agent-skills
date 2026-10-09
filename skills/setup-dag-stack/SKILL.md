---
name: setup-dag-stack
description: Use when dag.yaml exists but the current workspace has no local branches for its rounds; reconstruct the not-yet-merged rounds locally from the remote so existing work can be continued or reviewed — does not implement code, verify, or submit PRs
---

# Setup DAG Stack

Reconstruct the not-yet-merged **rounds** of a `dag.yaml` in this workspace, without
implementing anything.

Use it when a project was planned and partly run, but this workspace (a fresh worktree — e.g. a Conductor
workspace — or a new clone) has none of its branches.

## Preconditions

- `docs/note/dag.yaml` exists with `schema: 2`. For a `schema: 1` file, call `migrate-dag-stack`.
- The worktree is bootstrapped with `scripts/setup_note_link.sh <project_path>` from this skill (links `docs/note` to the project's note directory under `$NOTE_ROOT`; see 저장소 README → *DAG 스택: 노트 디렉터리*).
- `gh` is installed; all commands run non-interactively.

```bash
git config rerere.enabled true
git config remote.pushDefault origin
```

## What this skill does NOT do

- Does not implement task code.
- Does not push, create, or update PRs.
- Does not write `dag.yaml` directly — reconciliation belongs to `track-dag-stack`.

## Process

1. Read `query.py --rounds` and `query.py --brief`.
2. Compute the target: rounds whose `state` is not `merged`, in ascending `number`. If there are
   none, report "all rounds merged, nothing to reconstruct" and stop.
3. `git fetch` so remote branches resolve.
4. For each target round, in order:
   - If its `branch` resolves locally (`git rev-parse --verify --quiet <branch>`), leave it.
   - Else if `origin/<branch>` resolves, `git checkout -b <branch> origin/<branch>`.
   - Else if the round has a `pr_url`, `gh pr checkout <number>`.
   - Else the round was never pushed: `git checkout -b <branch> <base>` — where `<base>` is the
     round's recorded `base`, which must itself resolve first. If it does not, stop and report.
5. Stacked rounds (round *n+1*'s `base` is round *n*'s branch) need nothing extra: the chain is
   just the recorded `base` of each round, and step 6 checks it. *Optional:* if the `gh stack`
   extension is installed and the project uses it, register the chain with it so
   `rebase --upstack` / `sync` work. Never run `gh stack unstack` automatically.
6. Verify: each target round's branch exists and its recorded `base` is its actual merge base.
   On mismatch, stop and report drift — do not auto-correct.
7. Call `track-dag-stack` to reconcile `dag.yaml` against what is now local.
8. Report: which rounds were materialized, which were skipped as merged, which tasks are still
   `pending`, and which branch is checked out. State explicitly that nothing was implemented or
   pushed.

## Guardrails

- Never force-push during reconstruction.
- If `gh-stack` is used: never run `gh stack view` without `--json`, never run `gh stack unstack`.
- Never `git push` from this skill — a stale local branch would clobber remote work.
- Stop and report on any drift instead of rebuilding.

## Boundary with other skills

- `plan-dag-stack` creates `dag.yaml`.
- `setup-dag-stack` (this skill) makes the unmerged rounds exist locally, then stops.
- `run-dag-stack` implements and pushes.
- `review-dag-stack` drives the bot review.
- `migrate-dag-stack` promotes a `schema: 1` file and folds an old per-task PR stack.
