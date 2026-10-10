---
name: review-dag-stack
description: Use after a round's PR has been pushed and CodeRabbit has reviewed it; read the bot's latest review and unresolved threads, mark tasks done on approval, triage findings with the user, turn the accepted ones into one fix task, and reply to the rejected threads without resolving them
---

# Review DAG Stack

Collect one round's CodeRabbit review, decide what to act on, and record the outcome.
This is the only DAG skill that writes to GitHub, and the only thing it writes is replies.

## When to use

- Right after `run-dag-stack` pushes a round.
- When a round must reach approval before it can be closed and merged.
- When the user asks what the bot found.

## Preconditions

- The round has an **open** (not draft) PR. CodeRabbit does not review drafts — if the PR is a
  draft, mark it ready (`gh pr ready <n>`) and wait for the bot before going further.
- `gh` is authenticated.

## Reading the review

Only `coderabbitai[bot]`'s **latest** review counts. A human's `@coderabbitai approve` also
arrives under that name, so this covers the case where the bot fails to approve on its own.
A human `CHANGES_REQUESTED` must not hide a finished bot review, which is why `reviewDecision`
is not used here.

```bash
gh api repos/<owner>/<repo>/pulls/<n>/reviews \
  --jq '[.[] | select(.user.login=="coderabbitai[bot]")] | last | {state, commit_id, submitted_at}'
```

Unresolved findings — `isResolved: false` and `isOutdated: false` only. Outdated threads point
at code that has already changed; acting on them re-fixes what is fixed.

```bash
gh api graphql -f query='{repository(owner:"<owner>",name:"<repo>"){pullRequest(number:<n>){
  reviewThreads(first:100){nodes{ id isResolved isOutdated path line
    comments(first:1){nodes{author{login} body}} }}}}}' \
  --jq '.data.repository.pullRequest.reviewThreads.nodes[]
        | select(.isResolved==false and .isOutdated==false)'
```

## Process

1. Read the round: `query.py --pr`.
2. Read the bot's latest review state.
3. If `APPROVED`:
   - `set.py --round <n> --set approved_sha --value <commit_id>` and `--set state --value approved`.
   - Every task of that round whose `commits` are all contained in `approved_sha` becomes `done`
     (`git merge-base --is-ancestor <commit> <approved_sha>`).
   - Report that the round is ready to merge. **Do not merge** — that is the user's call.
4. Collect the unresolved threads.
5. Triage them into a draft and **stop for user approval**:

   | Verdict | Meaning |
   |---|---|
   | 반영 | A real defect or a change worth making |
   | 무효 | Wrong, out of scope, or contradicts a `project_policy` decision |
   | 보류 | Real but belongs to a later task; needs a decision |

   Use the bot's own tags (`🔴 Critical` / `🟡 Minor` / `⚡ Quick win`, `Functional Correctness`
   …) as evidence, not as the verdict.
6. After approval:
   - **반영** — append **one** fix task for this review round via `append-dag-stack`, listing
     each accepted finding in its `description` with file and line. One task per review round,
     not one per finding.
   - **무효** — reply on the thread with the reason. Silence makes the same finding come back
     next round. **Leave the thread open** — resolving is CodeRabbit's call, made after it reads
     the reply.
   - **보류** — reply saying it is deferred and why; leave the thread open.

```bash
gh api repos/<owner>/<repo>/pulls/<n>/comments/<comment_id>/replies -f body='…'
```

7. Record the triage outcome in the round's tasks' `deviations` where a finding contradicted
   the task's stated scope.
8. Read each task's `verification` field when assessing risk. **Mention any task whose touched
   features have no `fixed` verification.** Never treat bot approval (e.g. CodeRabbit APPROVED /
   `approved_sha`) as verification.
9. Drain the checklist for the tasks that just became `done`. A line whose check is now covered
   by an automated TC leaves the checklist and its TC id goes into that task's `e2e.covered_by`.
   A line that is still only a human check stays. The checklist is a queue, and a queue that
   only grows tells you nothing.
10. Call `track-dag-stack` to reconcile. It reports which of the newly `done` tasks finished
   without the coverage they declared.

## Constraints

- Never mark a task `done` on anything other than a bot `APPROVED` review.
- Never resolve a review thread, whatever the verdict. Replying is the whole job; CodeRabbit
  resolves its own threads once it has read the reply.
- Never merge the PR.
- Never file one task per finding — one fix task per review round.
- Never edit `dag.yaml` with the Edit tool; use `set-dag-stack` / `append-dag-stack`.
