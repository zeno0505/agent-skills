---
name: migrate-dag-stack
description: Use when a dag.yaml still uses the per-task-PR schema and must be promoted to the round model, or when a project's open per-task stacked PRs must be folded into one round PR; promotes the file with migrate.py and directs the fold — never runs on its own initiative
---

# Migrate DAG Stack

Promote a `schema: 1` `dag.yaml` to the round model, and fold what is left of its per-task PR
stack into one round.

**Migration is lazy and explicit.** Run it only when the user asks for this project, or when
another DAG skill hits a `schema: 1` file and stops. Never migrate a project on your own
initiative, and never migrate a project that is finished — a fully `done` DAG gains nothing.

## Part 1 — promote the file

```bash
python3 ~/.agents/skills/migrate-dag-stack/scripts/migrate.py <dag_path> --plan
python3 ~/.agents/skills/migrate-dag-stack/scripts/migrate.py <dag_path> --apply \
    --base-branch <branch> [--map-awaiting-review done]
```

`--plan` first, always. It reports what changes and what it refuses to decide.

What `--apply` does:

- `project_policy` map → item list (`key` / `decided_at` / `decision` / `legacy`).
  `decided_at` comes out empty — the old file never recorded it.
- `rounds: [{number: 0, state: merged}]` — the pre-round segment.
- Status vocabulary: `in_progress` → `running`. `awaiting_review` needs
  `--map-awaiting-review done`, because the E2E check it represented is no longer a status.
- Every already-merged task gets `round: 0`.
- `schema: 2`, `legacy: true` at the top level.
- Writes `<dag_path>.pre-migrate` before touching anything.

It deliberately does **not** touch `review_required` tasks: those have real open PRs, and their
round and status follow from how the stack is folded (Part 2).

Writes are line-surgical and batched into one splice with the same three-way verification as
`set.py`, so comments survive except inside `project_policy` and `rounds`. A 1.2 MB / 217-task
file takes about a second.

### After `--apply`

1. Move each `awaiting_review` task's outstanding browser check into `e2e-checklist.md` as
   `- [ ] [T-XXX] …` — that is where the information now lives.
2. Deprecate policies the round model replaces, e.g.:

```bash
python3 ~/.agents/skills/set-dag-stack/scripts/set.py <dag_path> \
    --policy-deprecate integration_method --superseded-by base_branch
python3 ~/.agents/skills/set-dag-stack/scripts/set.py <dag_path> \
    --policy-deprecate review_policy --superseded-by base_branch
```

   Deprecated policies stay in the file with `legacy: true`. Never delete them — "why did this
   project merge 183 tasks without a PR?" is a question that gets asked later.
3. Fill in `decided_at` for policies still in force where the date is known.
4. Add `verification` if the old file kept it under another name.
5. Run `show-dag-stack`.

## Part 2 — fold the open PR stack

Only for projects that still have open per-task PRs. **Ask before touching any PR.**

Read the stack:

```bash
gh pr list --repo <owner/repo> --state open --limit 100 \
  --json number,headRefName,baseRefName,isDraft,reviewDecision,additions,deletions
```

The rule, top of the stack downward:

| PR | Action |
|---|---|
| **open** (not draft) | Finish it as it stands — resolve its review, get approval, merge into its base. It already consumed review effort. |
| **draft with a review** (`reviewDecision` is not empty) | Same — handle the review first, then merge. |
| **draft with no review** | Fold. These become one round. |

`isDraft` alone is not the test: CodeRabbit used to review drafts, so some drafts carry
`CHANGES_REQUESTED`. `reviewDecision` is the evidence.

Folding:

1. The PRs to fold must be **contiguous at the top of the stack**. If a reviewed PR sits above
   an unreviewed one, stop and report — the lower one cannot be collapsed out from under it.
2. Create the round branch from the base of the lowest folded PR, with a free-form descriptive
   name, and bring the folded commits onto it (`git merge --ff-only` up the chain, or
   `git rebase --onto`). Keep the commits — they are the tasks.
3. `set.py --round-add` a round with that branch, `base`, `state: planned`, and set each folded
   task's `round` to it and `status` to `committed`.
4. Close the folded PRs with a comment naming the new PR. Do not delete their branches until the
   new round PR is open and its diff has been checked against them.
5. Hand off to `run-dag-stack` from step 5 (push, open PR) onward.

## Constraints

- Never migrate without being asked for that specific project.
- Never fold PRs that carry a review.
- Never delete a deprecated policy, and never delete `round: 0` history.
- Never force-push while folding.
- If the fold looks ambiguous — non-contiguous reviews, a PR whose base moved, commits that do
  not replay cleanly — stop and report. A human untangles it.
