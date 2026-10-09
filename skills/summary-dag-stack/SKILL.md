---
name: summary-dag-stack
description: Use when reporting what remains in a DAG project or producing a consistent human-readable project status summary for CLI, chat, or Telegram. Use read-dag-stack for individual task details.
---

# Summary DAG Stack

Summarize one active project DAG or the whole HQ development portfolio without treating implementation commits, dependency readiness, or deferred work as verified product progress.

Run:

```bash
python3 ~/.agents/skills/summary-dag-stack/scripts/summary.py <dag_path> [--context <reviewed-context.yaml>]
python3 ~/.agents/skills/summary-dag-stack/scripts/portfolio.py <hq_root> [--as-of YYYY-MM-DD]
```

The default output is a fixed Korean text report: project and checked date, goal, confirmed usable flows, next release criterion, blockers and release conditions, DAG state counts, E2E gaps, dependency chokepoints, and evidence. `--yaml` emits the former `read-dag-stack --summary` fields (`tasks`, `status_counts`, `open`, `ready_count`, `waiting_count`, `ready`, `chokepoints`) for machine consumers. Set `--done-status` when this project's completed state differs from `done`.

The optional context file is a YAML mapping. Its evidence paths are relative to the context file directory unless absolute:

```yaml
project: 포토 클라이언트
checked_at: 2026-09-28
goal: 받은 사람이 사진을 선택하고 업로더가 결과를 확인한다
current_flows:
  - 검증된 수신자 웹 흐름
next_release: 실제 API와 브라우저 QA 및 필요한 E2E 통과
blockers:
  - reason: 실제 API 검증 미완료
    clears_when: 격리 환경에서 브라우저 QA 통과
evidence:
  - context.md
```

For the HQ portfolio command, `company/policies/hq-sweep.yaml` is the active project and DAG registry; `company/development-status.yaml` maps every development project to a reviewed context file. The mapping must cover every registered project except `hq`, including products without a DAG. Each portfolio context also needs `next_actions` (nonempty string list), `user_approval` (`state: none|now` and `reason`), and `discussion` (`state: none|optional|needed`, plus `topic` unless `none`). Add `product` when several DAGs belong to one product, so open inbox decisions attach to both. `separate_approvals` in the manifest records execution gates outside current development work, with `id`, `action`, `needs`, `blocks_development`, and an existing `evidence` file.

The portfolio command combines those contexts with live DAG counts and unresolved `blocking` `decision` items in `inbox/open/`. It prints a fixed Korean report with next work, blocker and clearing condition, user approval, and discussion for each project. It refuses to print a report if a project mapping, required classification, evidence file, or reviewed date is missing or stale; this prevents a misleading `0건` approval result. Refresh the reviewed context when product facts or decisions change. The script verifies paths and dates, not the truth of a written claim. Sending text through Telegram remains a separate action.

Use the project's configured active DAG path, not an archival copy. If several DAGs exist and no authoritative path is configured, establish the active one before reporting. Populate context from current product decisions and verified QA or release evidence. A `done` task alone does not prove that a flow is usable or deployed. If a field lacks evidence, leave it absent so the report says `확인 필요`; never infer the business claim from a task title. When business claims are present, the script requires an existing evidence file and a `checked_at` date within seven days of `--as-of` (default today). It validates file existence and recency, not the truth of the claim; review the source. The script only reads files and prints output; sending the report through Telegram is a separate action.

`chokepoints` counts direct unfinished dependents. `ready` in `--yaml` means only that dependencies reached `--done-status`; it can include `committed`, `in_review`, or `deferred`. Neither field by itself authorizes dispatch or determines business priority. Check the project's approval, QA, resource, and release gates before describing an action as ready.
