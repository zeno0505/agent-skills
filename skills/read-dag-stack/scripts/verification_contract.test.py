#!/usr/bin/env python3
"""query.py와 render.py가 verification 필드를 올바르게 처리하는지 본다.

시험 케이스:
1. Same-day fail then pass -> pass (latest by position)
2. Mixed string and YAML date/datetime ordering
3. Mixed offsets (+09:00 vs Z) order correctly
4. All-invalid -> `invalid`
5. Malformed entries don't crash
6. Missing/null verification -> [] in output
7. set.py validation
8. Invalid date only -> invalid
9. Numeric evidence -> invalid
10. --index and --ready include verification summary
11. Append-only bypass blocked
12. Non-list verification -> invalid

실행: python3 verification_contract.test.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUERY = HERE / "query.py"
RENDER = HERE.parents[1] / "show-dag-stack" / "scripts" / "render.py"
SET = HERE.parents[1] / "set-dag-stack" / "scripts" / "set.py"

# (task_id, verification YAML or None, expected_cell, expected_summary)
# expected_summary: None (no record), "invalid", or "kind verdict"
CASES = [
    ("T-001", None, "—", None),  # No field
    ("T-002", "[]", "—", None),  # Empty list
    ("T-003", "null", "—", None),  # null
    ("T-004", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link1, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass"),
    ("T-005", '[{kind: exploratory, verdict: fail, evidence: link2, recorded_at: "2026-10-10"}]', "exploratory fail", "exploratory fail"),
    # Same-day fail then pass -> pass (later position wins)
    ("T-006", '[{kind: fixed, ref: tc.yaml, verdict: fail, evidence: link3, recorded_at: "2026-10-10"}, {kind: fixed, ref: tc.yaml, verdict: pass, evidence: link4, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass"),
    # Mixed string and YAML date
    ("T-007", '[{kind: fixed, ref: tc.yaml, verdict: fail, evidence: link5, recorded_at: "2026-10-09"}, {kind: fixed, ref: tc.yaml, verdict: pass, evidence: link6, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass"),
    # Mixed offsets
    ("T-008", '[{kind: fixed, ref: tc.yaml, verdict: fail, evidence: link7, recorded_at: "2026-10-10T10:00:00Z"}, {kind: fixed, ref: tc.yaml, verdict: pass, evidence: link8, recorded_at: "2026-10-10T20:00:00+09:00"}]', "fixed pass", "fixed pass"),
    # All invalid
    ("T-009", '[{bad: data}, "string", 123]', "invalid", "invalid"),
    # Mixed valid and invalid
    ("T-010", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link9, recorded_at: "2026-10-10"}, {bad: data}]', "fixed pass", "fixed pass"),
    # Missing required fields
    ("T-011", '[{kind: fixed, verdict: pass}]', "invalid", "invalid"),
    # Invalid date only
    ("T-012", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link10, recorded_at: "not-a-date"}]', "invalid", "invalid"),
    # Numeric evidence
    ("T-013", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: 123, recorded_at: "2026-10-10"}]', "invalid", "invalid"),
    # Mixed unparsable and valid
    ("T-014", '[{kind: fixed, ref: tc.yaml, verdict: fail, evidence: link11, recorded_at: "bad-date"}, {kind: fixed, ref: tc.yaml, verdict: pass, evidence: link12, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass"),
    # Non-list string
    ("T-015", '"oops"', "invalid", "invalid"),
    # Non-list mapping
    ("T-016", '{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link13, recorded_at: "2026-10-10"}', "invalid", "invalid"),
]


def build(path: Path):
    lines = [
        "schema: 2",
        "legacy: false",
        "project:",
        '  repo: "owner/repo"',
        "project_policy:",
        "  - key: base_branch",
        '    decision: "develop"',
        "rounds:",
        "- number: 1",
        '  branch: "b"',
        '  base: "develop"',
        "  state: open",
        "phases:",
        "  - name: feature",
        "    tasks:",
    ]
    for task_id, spec, _cell, _summary in CASES:
        lines += [
            f'      - id: "{task_id}"',
            "        type: feature",
            f'        title: "{task_id} 제목"',
            '        description: "설명"',
            "        target_files: []",
            "        depends_on: []",
            "        round: 1",
            "        commits: []",
            "        status: done",
            "        deviations: []",
        ]
        if spec is not None:
            lines.append(f"        verification: {spec}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(cmd, allow_failure=False):
    done = subprocess.run(cmd, capture_output=True, text=True)
    if not allow_failure and done.returncode != 0:
        raise SystemExit(f"실패: {' '.join(str(c) for c in cmd)}\n{done.stderr}")
    return done


def main():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        dag = Path(tmp) / "dag.yaml"
        build(dag)

        import yaml

        # Test render
        render_result = run([sys.executable, str(RENDER), str(dag)])
        if render_result.returncode != 0:
            failures.append(f"render crashed: {render_result.stderr}")
        else:
            table = (Path(tmp) / "dag.md").read_text(encoding="utf-8")
            for task_id, _spec, cell, _summary in CASES:
                row = next((ln for ln in table.splitlines() if ln.startswith(f"| {task_id} ")), None)
                if row is None:
                    failures.append(f"{task_id}: 표에 줄이 없습니다")
                    continue
                if f"| {cell} |" not in row:
                    failures.append(f"{task_id}: 표 칸 기대 {cell!r} — 실제 줄 {row}")

        # Test query doesn't crash
        query_result = run([sys.executable, str(QUERY), str(dag), "--task", "T-001", "T-015", "T-016"])
        if query_result.returncode != 0:
            failures.append(f"query crashed: {query_result.stderr}")

        # Test --index
        index_result = run([sys.executable, str(QUERY), str(dag), "--index"])
        if index_result.returncode != 0:
            failures.append(f"query --index crashed: {index_result.stderr}")
        else:
            index_tasks = yaml.safe_load(index_result.stdout)
            for task in index_tasks:
                task_id = task["id"]
                expected_summary = next((summary for tid, _, _, summary in CASES if tid == task_id), None)
                actual_summary = task.get("verification")
                if actual_summary != expected_summary:
                    failures.append(f"{task_id} --index: verification 기대 {expected_summary!r} 실제 {actual_summary!r}")

        # Test --ready
        ready_result = run([sys.executable, str(QUERY), str(dag), "--ready"])
        if ready_result.returncode != 0:
            failures.append(f"query --ready crashed: {ready_result.stderr}")
        else:
            ready_data = yaml.safe_load(ready_result.stdout)
            all_ready = ready_data.get("ready", []) + ready_data.get("waiting", [])
            for task in all_ready:
                task_id = task["id"]
                expected_summary = next((summary for tid, _, _, summary in CASES if tid == task_id), None)
                actual_summary = task.get("verification")
                if actual_summary != expected_summary:
                    failures.append(f"{task_id} --ready: verification 기대 {expected_summary!r} 실제 {actual_summary!r}")

        # Test set.py validation
        test_dag = Path(tmp) / "test-set.yaml"
        test_dag.write_text("""
schema: 2
project: {repo: "owner/repo"}
project_policy: [{key: base_branch, decision: develop}]
rounds: []
phases:
  - name: feature
    tasks:
      - id: "T-TEST"
        type: feature
        title: "Test"
        description: "Test"
        target_files: []
        depends_on: []
        status: pending
        verification: [{kind: fixed, ref: tc.yaml, verdict: pass, evidence: 'https://example.com/run1', recorded_at: '2026-10-10'}]
""", encoding="utf-8")

        # Valid append
        proc = subprocess.run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST", 
                      "--append-item", "verification", 
                      "--value", "{kind: fixed, ref: tc.yaml, verdict: pass, evidence: 'https://example.com/run2', recorded_at: '2026-10-10T14:30:00+09:00'}", 
                      "--yaml", "--dry-run"],
                     capture_output=True, text=True)
        if proc.returncode != 0:
            failures.append(f"set.py valid append failed: {proc.stderr}")

        # Invalid kind
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--append-item", "verification", 
                      "--value", "{kind: bad, verdict: pass, evidence: x, recorded_at: '2026-10-10'}", 
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should reject invalid kind")

        # Numeric evidence
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--append-item", "verification",
                      "--value", "{kind: fixed, ref: tc.yaml, verdict: pass, evidence: 123, recorded_at: '2026-10-10'}",
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should reject numeric evidence")

        # Bad recorded_at
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--append-item", "verification",
                      "--value", "{kind: fixed, ref: tc.yaml, verdict: pass, evidence: x, recorded_at: 'not-a-date'}",
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should reject invalid recorded_at format")

        # Test append-only bypass blocked
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--set", "verification",
                      "--value", "[]",
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should block --set verification (append-only)")
        # Check stdout (fail() prints to stdout)
        output = result.stdout + result.stderr
        if "append-only" not in output.lower():
            failures.append(f"set.py should mention append-only in error: {output}")

        # Test --remove-field blocked
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--remove-field", "verification"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should block --remove-field verification")

        # Test --force-verification-rewrite allows bypass
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--set", "verification",
                      "--value", "[]",
                      "--yaml", "--dry-run", "--force-verification-rewrite"],
                     allow_failure=False)

    if failures:
        print("어긋남:")
        for line in failures:
            print(f"  - {line}")
        raise SystemExit(1)
    print(f"통과 — 사례 {len(CASES)}건, verification 처리 일치 (render + query CLI + append-only + non-list)")


if __name__ == "__main__":
    main()
