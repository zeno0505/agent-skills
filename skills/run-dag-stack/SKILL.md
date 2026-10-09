---
name: run-dag-stack
description: Use when a dag.yaml exists and its pending tasks must be implemented; commit tasks onto one round branch, push in batches, open one PR per round so CodeRabbit reviews it, and propose closing the round when the measured diff reaches the line budget
---

# Run DAG Stack

Implement the pending tasks of one `dag.yaml`. Tasks are commits; a **round** is one pull
request holding many of them.

## Preconditions

- `docs/note/dag.yaml` exists with `schema: 2`. If it does not, call `migrate-dag-stack` and stop.
- The worktree is bootstrapped with `setup-dag-stack/scripts/setup_note_link.sh <project_path>` (links `docs/note`; see 저장소 README → *DAG 스택: 노트 디렉터리*).
- `gh` is installed and all commands run non-interactively.
- Git config for non-interactive execution:

```bash
git config rerere.enabled true
git config remote.pushDefault origin   # avoid the remote picker when several remotes exist
```

## Process

1. Read state in one call: `query.py --brief`. Use `--task <ID>` for the task you are about to
   implement. Never open `dag.yaml` directly — see `read-dag-stack`.
2. Verify `project_policy` has `base_branch` and `verification`. If `base_branch` is missing,
   **ask the user** and record it with `set.py --policy-add`.
3. Open a round if none is open (`current_round` is null in `--brief`):
   - Branch name is free-form and describes the work (`feature/profile/avatar-upload`).
   - `base` is `base_branch`, or the previous round's branch when stacking on an unmerged round
     (see *Stacked rounds*).
   - `git checkout -b <branch> <base>`, then `set.py --round-add` with `state: planned`.
4. For each `pending` task whose `depends_on` are all `done`, in dependency order:
   - `set.py --task <ID> --set status --value running`
   - Dispatch the implementation to a subagent (one task, its `target_files`, its verification) or implement inline.
     Implement only that task's scope; commit only its files.
   - Record the result: `--set commits` (hash list), `--set round` (the open round's number),
     `--set status --value committed`.
   - Append any browser-only check to `e2e-checklist.md` as `- [ ] [T-XXX] …`. **The task id
     tag is mandatory** — one note directory can hold several DAG files sharing one checklist,
     and an untagged line belongs to no DAG, so nobody ever drains it.
   - The checklist is a **queue of checks that have no TC yet**, not a log. When a check becomes
     an automated TC, put the TC id in that task's `e2e.covered_by` and delete the line. An
     empty checklist means done, which is only true if lines leave it.
5. Push when the run naturally pauses — no ready task remains, or the user must decide
   something. Push is a batch: several `committed` tasks go up together.
   - Run the `verification` commands first. Do not push a failing tree.
   - `git push -u origin <branch>`
   - First push of a round: `gh pr create --base <base> --head <branch> --fill` — **not a
     draft.** CodeRabbit only reviews open PRs. Record `pr_url` and `state: open`.
   - `set.py --round <n> --set last_pushed_sha`, and set every pushed task to `in_review`.
6. Measure the round after each push:

```bash
git diff <base>...HEAD --shortstat
```

   When changed lines reach `round_line_budget` (default 2500), **propose closing the round**
   and stop for approval. Do not close it yourself.

   Include `query.py --coverage` totals in that proposal, and `--brief`'s `mine` checklist count.
   This is a line on the approval you already stop for, not a new gate: the coverage check itself
   hangs on task completion and belongs to `track-dag-stack`. Never refuse to close a round over
   coverage — report it and let the user decide.

   Projects that do not use the round model never reach this step. `--brief` prints a `gate` line
   for those; such a project merges into `base_branch` on verification without opening a PR at all. Do not
   try to open a round there to make the gate fire.
7. On approval to close: hand off to `review-dag-stack` to drive the bot review to approval,
   then ask the user to merge. After merge, `set.py --round <n> --set state --value merged`.
8. If tasks remain, open the next round (step 3) with `number: n+1`.
9. Call `track-dag-stack` to reconcile `dag.yaml` against git and PR state.

## Stacked rounds

When round *n* is open or approved but not merged and there is more work to do, do not wait.
Stack round *n+1* on top of it with plain git — no extra tool is required. The stack node is a
round, so the stack stays 2–4 branches deep — never one per task.

```bash
git checkout -b <round n+1 branch> <round n branch>      # step 3, with base = round n's branch
# … commit tasks …
git push -u origin <round n+1 branch>
gh pr create --base <round n branch> --head <round n+1 branch> --fill   # never --draft
```

**When a lower round changes** (review fixes on round *n*), propagate upward with plain git,
bottom to top:

```bash
git checkout <round n+1 branch>
git merge <round n branch>        # then run verification and a normal `git push`
```

Merge, not rebase, once the upper branch has been pushed: rebasing a pushed branch needs a
force-push, and this skill does not force-push. Rebasing is fine only while the upper branch is
still local.

**When a lower round merges**, retarget the next PR before anything else, so its diff stops
including the merged round:

```bash
gh pr edit <round n+1 PR> --base <base_branch>
```

Record the new base with `set.py --round <n+1> --set base`, then merge `<base_branch>` into the
round *n+1* branch if it no longer applies cleanly.

**Optional: `gh-stack`.** If the `gh stack` extension is installed you may let it manage the chain
instead (`gh stack rebase --upstack` to propagate). Submitting through it **must** be
`gh stack submit --auto --open` — a bare `--auto` creates drafts, and CodeRabbit does not review
drafts, so the round would sit in `in_review` forever with no bot ever looking at it. Never run
`gh stack view` without `--json` (it opens a TUI), and never run `gh stack unstack`
automatically.

## Statuses this skill writes

- `running` while a task is being implemented
- `committed` after its commit lands locally
- `in_review` after the push that carries it

`done` is written by `review-dag-stack` when `coderabbitai[bot]` approves. This skill never
writes `done`.

An earlier round's `done` tasks stay `done` even when a later push dismisses the approval —
the dismissal is a PR-level fact and lives only in `rounds[n].approved_sha`.

## Re-run (idempotent)

- Implement only `pending` tasks. `committed` tasks are push targets; `in_review` tasks are
  waiting on the bot.
- If a round is `open` and its branch already exists, continue on it rather than opening a new one.

## Human approval required

Closing a round · the bot-finding triage from `review-dag-stack` · a missing `base_branch` ·
merging the PR · rewriting the plan.

Everything else — commits, pushes, opening the PR, status writes, checklist lines — is automatic.

## Guardrails

- Never create a draft PR. CodeRabbit does not review drafts. No `--draft` on `gh pr create`;
  with the optional `gh-stack`, `gh stack submit --auto --open`, never bare `--auto`.
- Never force-push. Propagate lower-round changes by merging them into the upper branch.
- Never push without running `verification` first.
- Never close a round without approval, even when the budget is exceeded.
- Never write `dag.yaml` with the Edit tool; use `set-dag-stack`.
- Never append a checklist line without its task id tag.
- Never block a round on E2E coverage. Report it on the approval you already stop for.
- If `gh-stack` is used: never run `gh stack view` without `--json`, and never run `gh stack unstack` automatically.
