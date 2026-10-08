---
name: append-dag-stack
description: Use when adding a follow-up, QA fix, CodeRabbit review fix, or requirement change to an existing DAG; append a new leaf task to dag.yaml so the current round picks it up — it creates no branch and no PR
---

# Append DAG Stack

Add new work to an existing `dag.yaml`. **Appending a task creates no branch and no PR** — the
task is implemented as a commit on whatever round is open when `run-dag-stack` reaches it.

## When to use

- CodeRabbit findings accepted in `review-dag-stack` (one fix task per review round)
- QA fixes and review follow-ups
- Requirement changes
- Newly discovered tasks

## Inputs

```yaml
repo: "owner/repo"
project_path: string
description: string
target_files: string[]
because: string        # REQUIRED. Why this task exists now (see *Every task carries its reason*)
```

## Process

1. Read the DAG: `query.py --brief`, and `--index` if you need to see existing ids.
2. Assign the next task id. For a review fix, name it after the round
   (`T-031` … or a `T-031-fix` style id if the project already uses one).
3. Append it to the active feature phase with `set.py --add-task --phase <name> --value-file - --yaml`.
   Never edit `dag.yaml` directly.
4. `depends_on` defaults to the tasks the new work builds on — for a review fix, the tasks whose
   code the findings point at.
5. Leave `round: null` and `status: pending`. `run-dag-stack` assigns the round when it commits
   the task, so a task appended while round 2 is open lands in round 2 automatically.
6. Propose an `e2e` field the same way `plan-dag-stack` does, and get it approved before
   writing. A fix task that changes a screen needs coverage as much as the task it fixes.
7. If `because` is a requirement change, record it in the context document in the same action
   (see *Every task carries its reason*).
8. Do **not** run `gh stack add`, do not create a branch, do not open a PR.

## Default task shape

```yaml
- id: "T-031"
  type: fix
  title: "1회차 봇 리뷰 반영"
  description: |
    CodeRabbit 1회차 리뷰에서 반영하기로 한 것.
    - src/components/…/index.vue:58 — 변경 전 이미지 세트가 남는다
    - …
  target_files: []
  depends_on:
    - "T-028"
  round: null
  commits: []
  status: pending
  deviations: []
  e2e:
    required: true
    covered_by: []
```

## Every task carries its reason

The most common way this workflow rots is a task appended to `dag.yaml` while the context
document stays as it was. Then two files disagree about what the project is for, and the file
nobody edits is the one people read first.

So this skill does not append a task without a reason, and when the reason is a requirement
change it writes both files or neither.

| `because` | What else you write |
|---|---|
| a review finding, a QA fix, newly discovered work | nothing — the task's own description is the record |
| a requirement change, a decision that moves scope | an entry appended to the context document, dated, with its source |

The context document is **appended to, never overwritten.** The newest entry is at the bottom,
the same shape `project_policy` already uses with `decided_at`. Overwriting is what makes two
readers disagree about which version is current.

Write the task's `description` so it names the context entry it rests on. A task with no
traceable reason then stands out in the list, which is the point.

## Constraints

- Never append a task without a reason. If the reason is a requirement change, the context
  document is updated in the same action — not later, not "next time".
- Never overwrite the context document. Append with a date and a source.
- Append only. Never insert into the middle of a phase's task list.
- Do not create a separate QA or fix phase.
- Do not classify severity — that judgment already happened in `review-dag-stack`.
- If the work belongs to an already-merged round, it is still a new task; never rewrite a
  merged round's history.
