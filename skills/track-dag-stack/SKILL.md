---
name: track-dag-stack
description: Use after task implementation, a push, or a merge to reconcile dag.yaml with actual git and PR state; verify commits, rounds, statuses and record scope deviations — reads only, never changes code, never mutates GitHub
---

# Track DAG Stack

Reconcile `dag.yaml` with what git and GitHub actually say. **Verify and record only — do not
change code, do not mutate the stack, do not write to GitHub.**

## When to use

- Right after `run-dag-stack` pushes, or after `review-dag-stack` finishes a triage.
- After committing directly to a round branch.
- After a round's PR is merged.

## Inputs

```yaml
repo: "owner/repo"
project_path: string
task_id: string   # (optional) reconcile only this task; otherwise the whole DAG
round: integer    # (optional) reconcile only this round
```

## Process

1. Read state with `query.py --brief`, `--rounds`, and `--task <ID>` as needed. Never open
   `dag.yaml` directly.

   `--brief` prints a `gate` line when the project does not use the round model. If it is there,
   **skip steps 2 and 3** and say so in the report. Some projects integrate without pull
   requests at all — they record in `project_policy` that they merge into `base_branch` once
   verification passes, and their only round is the pre-promotion segment. Running the PR
   reconciliation there reports failures that are not failures.

2. Read PR state read-only:

```bash
gh pr view <n> --repo <owner/repo> --json state,mergedAt,baseRefName,headRefName
gh api repos/<owner>/<repo>/pulls/<n>/reviews \
  --jq '[.[] | select(.user.login=="coderabbitai[bot]")] | last | {state, commit_id}'
```

3. Reconcile each round: `state` (`open` / `approved` / `merged`), `pr_url`, `approved_sha`,
   `last_pushed_sha`. Write each change through `set.py --round <n> --set <field>`.
4. Reconcile each task:
   - `commits` — every hash must exist (`git cat-file -e <sha>^{commit}`).
   - `round` — must match the round whose branch contains those commits.
   - `status` — derive it from facts, not from what the file says:

     | Fact | Status |
     |---|---|
     | no commits | `pending` (or `running` if being worked on) |
     | commits exist, none in `origin/<round branch>` | `committed` |
     | commits pushed, round not approved past them | `in_review` |
     | all commits are ancestors of `approved_sha` | `done` |

   - `depends_on` must all be `done` before a task may be `done`.
5. Compare each task's committed diff against `target_files` and `description`. Record
   added/missing files, scope overrun, and overlap with another task's `target_files`
   (entry-point files excluded) in `deviations` via `set.py --append-item deviations`.
6. Report E2E coverage with `query.py --coverage` (see *Reporting E2E coverage*). This runs on
   every project, round model or not.
7. At a round boundary only, check the external sources against the fingerprints in
   `context.md` (see *Checking the sources have not moved*).
8. Append an event to `docs/note/execution-log.md` if the project keeps one.
9. Run `show-dag-stack` to refresh `dag.md`.

## Reporting E2E coverage

```bash
python3 ~/.agents/skills/read-dag-stack/scripts/query.py <dag_path> --coverage
```

`uncovered_done` is the finding: a task that was declared to need an E2E check finished without
one. Report those by id and ask the user what to do. `uncovered_open` is not yet a problem — it
is work still in progress.

**This is the only place the check runs, and it hangs on task completion, not on closing a
round.** Projects that never open a round still complete tasks, so completion is the one moment
both integration models share. `run-dag-stack` echoes the same query's totals when it proposes
closing a round; that is a summary of this fact, not a second rule.

**Report, never block.** A task that is `done` without coverage stays `done`. Turning this into
a gate would reverse a decision some projects made deliberately — a no-PR project chooses its
model precisely because waiting on review chain-blocks downstream tasks.

`declared: 0` means the project has not decided anything yet, which is different from having
decided that nothing needs a test. Say which one it is; do not read silence as a decision.

### The checklist count is attributed, not just counted

`--brief` splits `e2e_checklist_open` into `mine`, `others`, and `untagged`. One note directory
can hold several DAG files sharing one `e2e-checklist.md` (one measured project had three live ones). Report
`mine`; mention `untagged` when it is non-zero, because those lines belong to no DAG and nobody
will drain them.

## Checking the sources have not moved

`context.md` carries a `sources` list: for each Notion page, Figma node, or thread it copied
from, the reference and the fingerprint of what was read. Recompute those and report any that no
longer match. A mismatch means *the requirement may have changed*, not that anything is broken —
report it and let the user decide.

**Only at a round boundary**, meaning when a round opens and when closing one is proposed.
Checking on every task costs external calls for nothing; anything that moved in between is caught
at the next boundary anyway.

**Figma MCP is assumed to be connected. If it is not, stop and say so — do not skip the check
and report success.** Saying a design was compared when it was not is the worst outcome
available here, worse than stopping. The same applies to a Notion page that no longer resolves.

Recompute a Notion fingerprint over the blocks that were actually quoted, not the whole page —
that is how the fingerprint was made, and hashing the whole page reports a change every time
someone fixes a typo.

This skill does not update the fingerprints. Re-collecting is `collect-dag-stack`'s job and
recording why a change was accepted belongs in the context document's change log, written by
`append-dag-stack` along with whatever task the change produced.

## Outputs

```text
docs/note/dag.yaml          # status / round / commits / rounds[] / deviations — via set-dag-stack
docs/note/execution-log.md  # append-only, when the project uses one
```

## Constraints

- Do not modify files other than `dag.yaml`, `dag.md`, and `execution-log.md`.
- Do not change code. Record scope drift in `deviations` and report it; do not fix it.
- Do not run mutating `gh` commands. Read-only `gh pr view` / `gh api` GET only.
- Do not mark a task `done` whose `depends_on` are not `done`.
- A `done` task stays `done` when a later push dismisses the PR approval — that fact belongs to
  `rounds[n].approved_sha`, not to the task.
- Stop and report if a round's branch no longer exists or its PR base has changed underneath it.
- Never change a task's status because of E2E coverage. Coverage is reported, not enforced.
- Do not run the PR reconciliation on a project whose `--brief` prints a `gate` line.
- Never report a source as unchanged when you could not read it. Stop instead.
- Do not rewrite fingerprints in `context.md`. Report the mismatch; re-collection is not yours.
