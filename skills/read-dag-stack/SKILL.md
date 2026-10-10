---
name: read-dag-stack
description: Use whenever dag.yaml must be read — task status, dependencies, description, target_files, deviations, project_policy, rounds, the open PR, or what is ready to start. Query it with query.py instead of opening the file; dag.yaml runs to hundreds of thousands of tokens and the Read tool silently truncates it. Also use when another DAG skill says "Read dag.yaml".
---

# Read DAG Stack

Query the smallest slice needed. Never open `dag.yaml` directly; use `query.py` because large DAGs
truncate and waste context.

Run `python3 ~/.agents/skills/read-dag-stack/scripts/query.py [dag_path] <mode>`. Use `--brief` at session
start, `--ready` for startable work, `--task ID` for the
task being implemented, and `--find`/`--deps`/`--dependents` to narrow further. Run `--help` for all
filters and fields. Add `--with-deviations` only when deviation history is required.

For a project-level status summary or human-readable report, use `summary-dag-stack`.

The tool is read-only. It does not infer status semantics; callers choose the done status. If a query
is empty, widen the query instead of reading the whole file. Writes use `set-dag-stack`; human views
use `show-dag-stack`.

## Verification Summary in List Outputs

`--index` and `--ready` outputs include a `verification` field for each task with a compact summary
of the task's verification status, using the same validation logic as `show-dag-stack`:

- `null`: no verification record (empty list or missing field)
- `"invalid"`: entries exist but none are valid (e.g., unparsable date, numeric evidence, missing required fields)
- `"kind verdict"`: the latest valid entry's kind and verdict (e.g., `"fixed pass"`, `"exploratory fail"`)

**Valid entry rules:**
- `kind` ∈ {fixed, exploratory}
- `verdict` ∈ {pass, fail, blocked}
- `evidence`: non-empty string
- `recorded_at`: parsable ISO 8601 (date-only or full timestamp with optional Z/offset), or YAML date/datetime
- `ref`: non-empty string when kind=fixed

Latest entry ordering: chronological comparison of `recorded_at` (parsed to aware datetime), ties broken by list position (append-only).

## Full Task Output (`--task`)

`--task <id>` returns the full task record including the complete `verification` list and a `verification_status` field:

- `verification_status: "none"`: no verification record (missing, null, or empty list `[]`)
- `verification_status: "invalid"`: malformed data (non-list value like string or mapping; kept as-is in output)
- `verification_status: "ok"`: non-empty list (may contain invalid entries; check individual entries)

**Consumers must check `verification_status`, not emptiness**, to distinguish missing data from malformed data.

Examples:
```yaml
# Missing/null -> normalized to []
- id: T-001
  verification: []
  verification_status: none

# Malformed (non-list) -> kept as-is with status
- id: T-002
  verification: "oops"
  verification_status: invalid

# Non-empty list
- id: T-003
  verification: [{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link, recorded_at: "2026-10-10"}]
  verification_status: ok
```
