---
name: plan-dag-stack
description: Use when planning a repository project as a DAG whose tasks are committed onto one branch and reviewed as round-sized pull requests; before implementation, create or update docs/note/dag.yaml with project_policy, an empty rounds list, and small implementable tasks
---

# Plan DAG Stack

Produce a `dag.yaml` for one project. Tasks stay small — one task is a **commit**, not a PR.
Pull requests are formed later, one per **round**, by `run-dag-stack`.

## Inputs

```yaml
repo: "owner/repo"
project_path: string   # project identity; docs/note is already linked to this project directory
context_file: "docs/note/context.md"
base_branch: string    # REQUIRED. Ask the user if it cannot be determined — do not guess.
```

`base_branch` is where this project's rounds merge into. It is often a project integration
branch (`feature/profile/main`, `next/payment/main`), not `develop`. Only the developer knows
which — **ask.**

## Outputs

```text
docs/note/dag.yaml
docs/note/dag.md            # via show-dag-stack
docs/note/e2e-checklist.md  # created empty if absent
```

Design-verification assets (spec fingerprints, node mapping, waivers, variants) do **not** live
here. They live in the E2E asset repository under `<feature area>/design/`, because the runner
reads them and QA and CI have no note vault. This skill neither creates nor reads them.

## Process

1. Verify `project_path` is present. Stop if missing.
2. Ensure `docs/note/` (the project note directory, linked by `setup-dag-stack/scripts/setup_note_link.sh`) exists.
3. Read `context.md` and related docs in the project note directory.
4. Explore the repository for relevant files, components, routes, data, and tests.
5. Ask the user for `base_branch` if it is not already stated.
6. Define tasks with `target_files`. Size them so **one subagent can implement and verify one
   task in one sitting** — this is a commit-sized unit, not a PR-sized one.
7. Specify inter-task dependencies with `depends_on`. Stop if there is a cyclic dependency.
8. Propose an `e2e` field for each task and **get the user's approval before writing it**
   (see *Proposing E2E coverage*).
9. Write `dag.yaml` with `schema: 2`, `project_policy`, and an empty `rounds: []`.
10. Create `e2e-checklist.md` with a header if it does not exist.
11. Run `show-dag-stack` to render `dag.md`.

Do **not** estimate whether the project fits in one PR. Deciding that a project is too big and
splitting it is the developer's call, and it cannot be observed from the plan. Round
boundaries are decided later from measured diff size, by `run-dag-stack`.

## Schema (`schema: 2`)

```yaml
schema: 2
legacy: false            # true only when the project has a pre-round segment (see migrate-dag-stack)

project:
  repo: "owner/repo"
  project_path: "acme/web/profile-avatar"
  note_dir: "docs/note"

project_policy:          # an open list. Required keys: base_branch, verification.
  - key: base_branch
    decided_at: "2026-08-27"
    decision: "feature/profile/main"
    rationale: "Why this branch and not develop."
    legacy: false
  - key: verification
    decided_at: "2026-08-27"
    decision: ["pnpm typecheck", "pnpm eslint"]
    legacy: false
  - key: round_line_budget       # optional; default 2500
    decided_at: "2026-08-27"
    decision: 2500
    legacy: false

rounds: []               # one entry per pull request; run-dag-stack opens the first

phases:
  - name: feature
    tasks:
      - id: "T-001"
        type: feature
        title: "Task title"
        description: "Concrete implementation scope."
        target_files: []
        depends_on: []
        round: null      # assigned when the task is committed into a round
        commits: []      # commit hashes; a task may land in more than one
        status: pending
        deviations: []
        e2e:             # optional. Absent means "not decided yet", never "not applicable"
          required: true
          covered_by: []           # TC ids that exercise this task
          variants: []             # variant properties this task must pass, as asset-repo refs
          reason: ""               # why, when required is false
```

### `rounds[]` entry

```yaml
- number: 1
  branch: "feature/profile/avatar-upload"        # free-form, describes the work
  base: "feature/profile/main"                  # base_branch, or the previous round's branch when stacked
  pr_url: null
  state: planned        # planned | open | approved | merged
  approved_sha: null    # commit_id of coderabbitai[bot]'s APPROVED review
  last_pushed_sha: null
```

### Statuses

`pending` → `running` → `committed` (committed, not pushed) → `in_review` (pushed, bot is
looking) → `done` (bot approved). Plus `blocked`, `deferred`, `superseded`.

`review_required` is legacy-only — never use it in a `schema: 2` file.

## Proposing E2E coverage

The `e2e` field is what keeps verification from being skipped. It is **optional**, and its
absence means *not decided yet* — never *not applicable*. Do not omit it to mean "no test
needed"; write `required: false` with a `reason` instead. The two look identical in a file and
only one of them is a decision.

**Propose, do not decide.** Read each task's `target_files` and description and suggest a value,
then stop and let the user correct the list. Deciding `required` on your own goes wrong in both
directions: automatic true nags on every internal task, and automatic false silently drops
screens.

**What to look at.** `target_files` alone is not enough. A backend project's files are all server
code and the paths do not separate anything. Judge by what becomes observable in the product:

| The change is observable as | Cover it with |
|---|---|
| a screen | an ordinary TC |
| only a response payload | a TC using the runner's API verbs |
| nothing outside the code | `required: false` with a reason |

Record the project's own version of that rule as a `project_policy` item so the next planner
does not re-derive it, and so `query.py --policy` shows why this project proposes what it does.

**Write the TC at the same moment, not later.** Proposing `required: true` and moving on is how
coverage stays empty: the field records an intention and nothing turns it into a test. When a
task's coverage is agreed, call your TC-writing step (e.g. a TC-writer skill) from the
requirement right then, with the policy document and the design variants as the material, and
put the resulting TC id in `covered_by`.

The screen does not exist yet at planning time, and that is the normal case for this entry — the
writer leaves what it cannot fill as `notyet` and stops at format review. That is the whole point:
a TC written from the requirement asks what the requirement says, while a TC written afterwards
from the finished screen only asks what the screen already does.

**Variants come from the asset repository, not from here.** When a task touches a component whose
Figma variants are classified as planning branches, list those variant properties in `variants`
as references. Do not copy the variant data into `dag.yaml` — it has the lifetime of the
component, not of this project.

## Deciding the design mapping

A project that verifies its screens against a Figma design needs each design node tied to a DOM
element. That tie is **decided here, at planning time — but only half of it.**

**The Figma tree is not the DOM tree.** It is a drawing tool's tree, so groups that auto-layout
created vanish when the design becomes HTML, and that is correct, not a defect. Measured on one
screen: a design row holding 1 group became 3 sibling elements, a 3-part info group became 2, a
4-button footer became 2. Nine of the twenty-three nodes on that screen had no element at all.

So planning decides the structure, and implementation fills in the selector:

| When | What is decided | Why then |
|---|---|---|
| planning | which design node becomes which component, and **which nodes become no element at all** | it is an answer to *what shall we build*, and it doubles as an instruction to whoever builds it |
| after implementation | the CSS selector | measured: `.comment-item:first-of-type` was expected to match one element and matched five. You cannot count matches on a screen that does not exist |

The component half is nearly free — a task's `target_files` already names it. What planning adds
is the second column: the list of design nodes that deliberately get no element. Write that down,
because a missing element later is otherwise indistinguishable from a mapping mistake.

**Propose, do not decide** applies here exactly as it does to `e2e`. Whether a design node is a
given element depends on design intent, and a fingerprint holds only coordinates and values.

**Use mechanical judgment to choose what to ask, not to answer.** Asking about every node
exhausts the person answering; on the measured screen it would have been nine questions where
three were real:

- nodes whose contract values are character-identical and collapse into one element → propose and
  take a confirmation, do not ask
- nodes whose contract values *differ* yet collapse → this is a finding, not a question. One
  element cannot satisfy 15px and 13px at once
- a group of same-natured nodes (the five inside a design-system button) → one question, not five
- a node carrying only `reference`-grade values and serving as no distance endpoint → contributes
  to no judgment, do not ask

The mapping and fingerprint files themselves live in the asset repository, not here. This skill
decides what goes in them; it does not write them.

## Constraints

- One `project_path` has exactly one `dag.yaml`.
- Never write `dag.yaml` with the Edit tool — use `set-dag-stack`.
- This skill does not run git or `gh` commands and does not implement code.
- Do not overwrite an existing `dag.yaml` without user approval.
- Do not create fix or QA phases. Follow-up work is added later via `append-dag-stack`.
- Do not emit a `stack` block. That was the per-task-PR model; see `migrate-dag-stack`.
- Never write an `e2e` field the user has not approved, and never use its absence to mean the
  task needs no test.
- Never leave `required: true` with an empty `covered_by` as the end of planning. Either the TC is
  written now, or say out loud that it is owed and to whom.
- Do not add design-verification assets to the note directory. They belong to the asset repo.
- Never fix a design mapping by yourself. Propose it, and say which design nodes you expect to
  have no element at all — that list is the part a later reader cannot reconstruct.
