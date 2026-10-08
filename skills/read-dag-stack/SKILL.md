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
