---
name: set-dag-stack
description: Use whenever dag.yaml must be written — task status, round, commits, description, target_files, deviations, project_policy items, rounds, adding a task, removing a task or field. Edit it with set.py instead of the Edit tool; set.py replaces only the target field's line range and refuses to write if verification fails. Also use when another DAG skill says to update dag.yaml.
---

# Set DAG Stack

Change one field, or one task, in `dag.yaml`. **Never edit `dag.yaml` with the Edit tool or a
`yaml.safe_load` → `safe_dump` round trip.**

## Why

A large `dag.yaml` (measured: ~13,500 lines) with comments and long block scalars. A load/dump round trip
rewrites **16,147 lines (119% of the file)** — comments gone, every block scalar reflowed, the
diff unreviewable. The Edit tool needs the surrounding text read first, and the file is past
the Read limit.

`set.py` replaces only the target's line range and verifies three things before writing:

1. everything outside the replaced range is byte-identical
2. the result parses as YAML
3. the parsed result differs from the original **only** at the intended path

If any check fails, nothing is written. A single field change lands as a 1-line diff.

## Usage

```bash
python3 ~/.agents/skills/set-dag-stack/scripts/set.py [dag_path] --task <ID> <mode> [options]
```

| Mode | What it does |
|---|---|
| `--set FIELD` | replace the field; creates it if absent |
| `--append-item FIELD` | append one item to a list field, leaving existing items untouched |
| `--remove-field FIELD` | delete the field |
| `--remove-task <ID>` | delete the whole task (no `--task` needed) |
| `--add-task --phase <name>` | append a task to that phase (default: last phase) |
| `--policy-add` | append an item to `project_policy` (value must be a mapping with `key`) |
| `--policy-deprecate KEY [--superseded-by KEY]` | mark a policy `legacy: true`, keeping it in the file |
| `--round-add` | append a round (value must be a mapping with `number`) |
| `--round N --set FIELD` | change one field of round `N` |
| `--top KEY` | set a top-level key other than `phases` (e.g. `schema`, `legacy`) |

`--policy-*`, `--round-*`, and `--top` rewrite their whole top-level block rather than one line.
Those blocks are small, and rewriting them is what makes editing an item's single field safe.
Comments inside `project_policy` and `rounds` do not survive; comments elsewhere do.

Value input: `--value "one line"`, or `--value-file <path>`, or `--value-file -` for stdin.
**Use stdin for anything multi-line** — never try to pass newlines through shell quoting.
Add `--yaml` to parse the input as YAML (lists, mappings, numbers, null) instead of as text.

Multi-line strings are written as literal blocks (`|`), so backticks, quotes, emoji, blank
lines, and YAML metacharacters survive verbatim.

## Always

- **`--dry-run` first** when the change is not a simple scalar. It prints the line range and
  diff and writes nothing.
- **`--expect FIELD=VALUE`** when the change depends on the current value — for example
  `--expect status=pending` before marking a task done. It aborts on mismatch.

## Concurrency

`dag.yaml` is edited by other sessions. `set.py` re-reads the file at write time, so unrelated
concurrent edits are never clobbered, and it re-checks mtime and size immediately before
replacing the file — if it changed since the read, it aborts and asks you to re-query. The
write itself is atomic (temp file + `os.replace`).

If it aborts this way, re-read with `read-dag-stack` and redo the change; do not force it.

## Examples

```bash
# 상태 한 줄
set.py --task T-137 --set status --value done --expect status=in_progress

# 여러 줄 본문
cat draft.md | set.py --task T-137 --set description --value-file -

# 편차 한 건 덧붙이기 (기존 항목은 그대로)
printf '[2026-08-21] 범위를 벗어난 파일 둘을 함께 고쳤다.\n' \
  | set.py --task T-137 --append-item deviations --value-file -

# 새 태스크
set.py --add-task --phase feature --value-file new-task.yaml --yaml
```

## Constraints

- Change only what you were asked to change. One field per call.
- Do not touch code, do not run `gh stack` mutations.
- `track-dag-stack` stays the owner of `status`/`pr_url`/`deviations` decisions — this skill is
  the instrument it writes with, not a licence for other skills to write.

## Related

- `read-dag-stack` queries `dag.yaml` without loading it whole.
- `show-dag-stack` regenerates `dag.md` after a change.
