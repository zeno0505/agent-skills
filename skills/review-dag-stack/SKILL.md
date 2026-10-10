---
name: review-dag-stack
description: Use after a round's PR has been pushed and CodeRabbit has reviewed it; read the bot's latest review and unresolved threads, assess PR risk tier (상/중/하), mark tasks done on approval, triage findings with the user, turn the accepted ones into one fix task, and reply to the rejected threads without resolving them
---

# Review DAG Stack

Collect one round's CodeRabbit review, assess the round's risk tier, decide what to act on, and record the outcome.
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
3. **Assess risk tier** (상/중/하) if this is the first review of the round (see *Risk Tier Assessment*):
   - Check deterministic signals from `risk_config` (if present).
   - Evaluate reviewer judgment based on changed files, scope, and review findings.
   - Record tier, reason, signals, and assessor with `set.py --round <n>`.
4. If `APPROVED`:
   - `set.py --round <n> --set approved_sha --value <commit_id>` and `--set state --value approved`.
   - Every task of that round whose `commits` are all contained in `approved_sha` becomes `done`
     (`git merge-base --is-ancestor <commit> <approved_sha>`).
   - Generate merge recommendation based on risk tier and review round count (see *Merge Recommendation*).
   - **Do not merge** — that is the user's call.
5. Collect the unresolved threads.
6. Triage them into a draft and **stop for user approval**:

   | Verdict | Meaning |
   |---|---|
   | 반영 | A real defect or a change worth making |
   | 무효 | Wrong, out of scope, or contradicts a `project_policy` decision |
   | 보류 | Real but belongs to a later task; needs a decision |

   Use the bot's own tags (`🔴 Critical` / `🟡 Minor` / `⚡ Quick win`, `Functional Correctness`
   …) as evidence, not as the verdict.
7. After approval:
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

8. Record the triage outcome in the round's tasks' `deviations` where a finding contradicted
   the task's stated scope.
9. Read each task's `verification` field when assessing risk. **Mention any task whose touched
   features have no `fixed` verification.** Never treat bot approval (e.g. CodeRabbit APPROVED /
   `approved_sha`) as verification.
10. Drain the checklist for the tasks that just became `done`. A line whose check is now covered
   by an automated TC leaves the checklist and its TC id goes into that task's `e2e.covered_by`.
   A line that is still only a human check stays. The checklist is a queue, and a queue that
   only grows tells you nothing.
11. Call `track-dag-stack` to reconcile. It reports which of the newly `done` tasks finished
   without the coverage they declared.

## Risk Tier Assessment

Risk tier (상/중/하) is assessed **after the first review** of a round, whether `APPROVED` or
`CHANGES_REQUESTED`. The assessment is never changed once recorded, even if subsequent review
rounds occur.

### Who Assesses

The **reviewer** assesses risk, never the agent or subagent that wrote the code. In this
workflow:
- CodeRabbit (when used) is the assessor
- A local review agent (when used instead of CodeRabbit) is the assessor
- The orchestrator implementing tasks is never the assessor

Record the assessor name in `risk_assessed_by` (e.g., `"CodeRabbit"` or the agent's display name).

### Deterministic Signals (Force 상)

Check `risk_config` at the top level of `dag.yaml`. If absent, skip deterministic signals and
rely solely on reviewer judgment. If present, each signal type is checked:

1. **`critical_paths`** — glob patterns for critical code areas (e.g., `src/payment/**`,
   `src/auth/**`). If any changed file matches, fire this signal.
2. **`critical_files`** — glob patterns for critical files (e.g., `**/schema.sql`,
   `**/*.proto`). If any changed file matches, fire this signal.
3. **`max_diff_lines`** — integer threshold. If the diff's changed lines (additions +
   deletions) exceed this, fire this signal.

```bash
# Check changed files in the round's diff
git diff <base>...<head> --name-only

# Measure diff size
git diff <base>...<head> --shortstat
```

If **any** signal fires, the tier is **`상`** regardless of the reviewer's judgment. Record the
fired signal names in `risk_signals` (e.g., `["critical_paths", "max_diff_lines"]`).

### Reviewer Judgment (중/하, or 상 without signals)

When no deterministic signals fire, the reviewer judges the tier based on:

- **Scope and impact**: Does this change affect shared components, conventions, or data
  contracts?
- **Review findings**: Are there critical issues (`🔴 Critical`, security, data integrity)?
- **Isolation**: Is the change localized to one module or spread across many?

Reviewer judgment can also produce `상` even without signals (e.g., a security flaw in a
non-critical path).

| Tier | Criteria |
|---|---|
| **상** | Shared component changes, convention/config changes affecting the project, data integrity or security concerns, or any deterministic signal |
| **중** | Major logic changes but isolated, multi-file changes within one feature, test coverage present but edge-case concerns |
| **하** | Small scope, isolated bug fixes, doc/test/style-only changes, clean review |

### Recording Risk Tier

```bash
# All four fields are written together after the first review
python3 ~/.agents/skills/set-dag-stack/scripts/set.py docs/note/dag.yaml \
  --round <n> --set risk_tier --value "중"
python3 ~/.agents/skills/set-dag-stack/scripts/set.py docs/note/dag.yaml \
  --round <n> --set risk_reason --value "여러 파일 변경, 주요 비즈니스 로직"
python3 ~/.agents/skills/set-dag-stack/scripts/set.py docs/note/dag.yaml \
  --round <n> --set risk_signals --value-file - --yaml   # pass [] or ["signal_name", ...]
python3 ~/.agents/skills/set-dag-stack/scripts/set.py docs/note/dag.yaml \
  --round <n> --set risk_assessed_by --value "CodeRabbit"
```

The `risk_reason` field is a **one-line summary** (not multi-paragraph). It should state the key
factors that led to the tier, including which signals fired if any.

## Merge Recommendation

After a round reaches `APPROVED` and tasks are marked `done`, generate a merge recommendation
based on the risk tier and review round count. **This is a recommendation, not an automatic
merge.**

### Review Round Count

Track how many review rounds this PR has gone through. A round is defined as:
1. Push with new commits → bot reviews → findings triaged

If fixes are pushed and the bot reviews again, that is round 2, and so on.

### Recommendation Rules

| Tier | Round | Critical Issues Remaining? | Recommendation |
|---|---|---|---|
| **하** | 1 | No or minor findings | **Recommend merge** |
| **하** | 1 | Yes (unlikely with APPROVED) | Fix and re-review |
| **중** | 1 | Critical issues | Fix and re-review |
| **중** | 2 | No critical issues | **Recommend merge**, defer minor findings |
| **중** | 2 | Critical issues remain | Continue review (exception to 2-round cap) |
| **상** | Any | Any | **Human review required** — do not recommend merge without explicit human approval |

"Critical issues" are findings tagged `🔴 Critical` or judged by the reviewer to be functional
correctness, security, or data-integrity defects. Minor findings (`🟡 Minor`, style suggestions,
`⚡ Quick win` refactors) do not block merge recommendations past round 2.

### Phrasing the Recommendation

When `APPROVED` and the tier + round count produce a merge recommendation:

```
라운드 <n> 승인됨 (risk_tier: 하, 1라운드). 마이너 파인딩 없음 → **머지 권장**
```

```
라운드 <n> 승인됨 (risk_tier: 중, 2라운드). 크리티컬 이슈 해결, 마이너 제안 2건은 보류 처리 → **머지 권장**
```

When `상` tier:

```
라운드 <n> 승인됨 (risk_tier: 상, 결제 경로 변경). **사람 리뷰 필수** — 머지 전 사람의 직접 승인 필요
```

Do not merge on your own; report the recommendation and stop for the user's decision.

## Backward Compatibility

`risk_config` and the four risk fields in `rounds[]` are **optional**. Existing `dag.yaml` files
without them continue to work:
- `risk_config` absent → deterministic signals are skipped, reviewer judgment only
- `risk_tier` / `risk_reason` / `risk_signals` / `risk_assessed_by` all `null` → indicates the
  round was reviewed before this feature was added, or risk assessment was not performed

Old rounds with `null` risk fields are treated as "not assessed" and do not produce merge
recommendations based on tier. The existing 2-round cap still applies as a fallback.

## Constraints

- Assess risk tier only after the **first review** of a round, never before review, never on
  subsequent re-reviews of the same round.
- The **reviewer** (CodeRabbit or review agent) assesses risk, never the code author.
- Deterministic signals in `risk_config` **force** 상 tier regardless of reviewer judgment.
- Risk tier generates a **recommendation**, not an automatic merge. Always stop for user
  approval.
- Never mark a task `done` on anything other than a bot `APPROVED` review.
- Never resolve a review thread, whatever the verdict. Replying is the whole job; CodeRabbit
  resolves its own threads once it has read the reply.
- Never merge the PR.
- Never file one task per finding — one fix task per review round.
- Never edit `dag.yaml` with the Edit tool; use `set-dag-stack` / `append-dag-stack`.
