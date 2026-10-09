---
name: show-dag-stack
description: Use when dag.md is stale, out of sync with dag.yaml, or the current DAG state must be shown — regenerates dag.md (round table, current policy, mermaid graph, status legend, task table) from dag.yaml and reports status counts, ready-to-start tasks, and schema warnings. Also use right after any dag.yaml edit, or when asked to render/refresh/show the DAG graph or task stack.
---

# Show DAG Stack

Regenerate `dag.md` from `dag.yaml` and report the current state of the stack.
**Render and report only — never edit `dag.yaml` and never touch code.**

## When to use

- `dag.md` looks older than `dag.yaml`, or the graph does not match the tasks.
- Right after `track-dag-stack`, `run-dag-stack`, `append-dag-stack`, `review-dag-stack`, or
  `migrate-dag-stack` changes `dag.yaml`.
- The user asks to see the DAG, the task graph, or what is ready to start.

## Inputs

```yaml
dag_path: string   # (optional) path to dag.yaml, default docs/note/dag.yaml
full: boolean      # (optional) draw every node instead of collapsing large status groups
```

## Process

1. Locate the target `dag.yaml`. Default `docs/note/dag.yaml`; if it is missing, look for
   `**/dag.yaml` under `docs/note/` and ask which one when several exist.
2. Run the renderer:
   ```bash
   python3 ~/.agents/skills/show-dag-stack/scripts/render.py <dag_path>
   ```
   Add `--full` to disable node collapsing, `--max-nodes N` to change the collapse threshold
   (default 60).
3. Read the renderer's stdout: task count, per-status counts, and any schema warnings.
4. Read `dag.yaml` to work out what the statuses mean **in this project** — the renderer
   deliberately does not know. Determine which tasks are ready to start: every id in
   `depends_on` is in a completed state, and the task itself is not.
5. Report to the user, in Korean:
   - status counts, one line
   - tasks ready to start now (id + title)
   - anything stalled or failed, if the project's status vocabulary marks such a state
   - schema warnings, verbatim, with the affected task ids
   - E2E coverage: run `query.py --coverage` and name the `uncovered_done` ids. Say
     `declared: 0` plainly as "nothing decided yet" rather than treating it as clean.
   - the `gate` line from `query.py --brief`, if present, so the reader knows the round-close
     report does not run in this project
6. If warnings appeared, say what would fix them but do not fix `dag.yaml` yourself unless asked.

## Outputs

```text
<dag_path 와 같은 디렉터리>/dag.md   # regenerated: warnings, status legend, graph, task table
```

The task table carries an `E2E` column with four values. `—` means no `e2e` field, which is
*not decided yet*; `불필요` is a decision that no test is needed; TC ids mean covered;
`**미충족**` means required and uncovered. The first two look alike in prose and must not be
collapsed into one cell — one of them is a decision and the other is a gap.

## Renderer contract

- **It does not know status names.** Statuses are read from `dag.yaml` at run time and each
  gets a palette color from a stable hash of its own name, so the same status keeps the same
  color across runs and repositories, and adding a status never recolors the others.
  Never add a status list to the renderer.
- **It never fails on schema problems.** Missing fields and unknown `depends_on` ids become
  warnings in `dag.md` and on stdout; the graph is still drawn. Rendering is an observation
  tool, not a validation gate — a validating renderer is what let `dag.md` go stale for weeks.
- **It collapses by group size, not by status name.** Above the node threshold, the largest
  status groups fold into one node each until the graph fits.
- **The task table links resolvable ids, the mermaid graph never does.** For each `dag.yaml`
  it walks up from the yaml's directory to find an Obsidian vault (`.obsidian`), then borrows
  that vault's `scripts/wikilink_resolve.py` to turn resolvable task ids into alias
  wikilinks (`[[path|T-001]]`, pipe escaped as `\|` for the table). Ids without an
  `inbox/<id>/` folder stay plain text. If no vault is found or the import fails, every id
  stays plain and rendering still succeeds — resolution is best-effort, never a gate. The
  mermaid graph always keeps plain ids: Obsidian does not parse `[[...]]` inside mermaid node
  labels, and the alias `|` would collide with mermaid syntax.

## Constraints

- Modify nothing but the generated `dag.md`.
- Do not edit `dag.yaml`, do not change code, do not run any branch or stack mutation (`git branch`/`rebase`/`push`, `gh pr`, `gh-stack`).
- Do not "fix" statuses the renderer reports as unfamiliar — an unfamiliar status is expected.
