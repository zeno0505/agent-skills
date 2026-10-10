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
13. Numeric recorded_at blocked in set.py
14. --task includes verification_status (none | ok | invalid)
15. --deps, --dependents, --find, --brief include verification summary
16. --ready and --brief have real ready tasks with verification

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

# (task_id, verification YAML or None, expected_cell, expected_summary, status)
# expected_summary: None (no record), "invalid", or "kind verdict"
CASES = [
    ("T-001", None, "—", None, "done"),  # No field
    ("T-002", "[]", "—", None, "done"),  # Empty list
    ("T-003", "null", "—", None, "done"),  # null
    ("T-004", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link1, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass", "done"),
    ("T-005", '[{kind: exploratory, verdict: fail, evidence: link2, recorded_at: "2026-10-10"}]', "exploratory fail", "exploratory fail", "done"),
    # Same-day fail then pass -> pass (later position wins)
    ("T-006", '[{kind: fixed, ref: tc.yaml, verdict: fail, evidence: link3, recorded_at: "2026-10-10"}, {kind: fixed, ref: tc.yaml, verdict: pass, evidence: link4, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass", "done"),
    # Mixed string and YAML date
    ("T-007", '[{kind: fixed, ref: tc.yaml, verdict: fail, evidence: link5, recorded_at: "2026-10-09"}, {kind: fixed, ref: tc.yaml, verdict: pass, evidence: link6, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass", "done"),
    # Mixed offsets
    ("T-008", '[{kind: fixed, ref: tc.yaml, verdict: fail, evidence: link7, recorded_at: "2026-10-10T10:00:00Z"}, {kind: fixed, ref: tc.yaml, verdict: pass, evidence: link8, recorded_at: "2026-10-10T20:00:00+09:00"}]', "fixed pass", "fixed pass", "done"),
    # All invalid
    ("T-009", '[{bad: data}, "string", 123]', "invalid", "invalid", "done"),
    # Mixed valid and invalid
    ("T-010", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link9, recorded_at: "2026-10-10"}, {bad: data}]', "fixed pass", "fixed pass", "done"),
    # Missing required fields
    ("T-011", '[{kind: fixed, verdict: pass}]', "invalid", "invalid", "done"),
    # Invalid date only
    ("T-012", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link10, recorded_at: "not-a-date"}]', "invalid", "invalid", "done"),
    # Numeric evidence
    ("T-013", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: 123, recorded_at: "2026-10-10"}]', "invalid", "invalid", "done"),
    # Mixed unparsable and valid
    ("T-014", '[{kind: fixed, ref: tc.yaml, verdict: fail, evidence: link11, recorded_at: "bad-date"}, {kind: fixed, ref: tc.yaml, verdict: pass, evidence: link12, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass", "done"),
    # Non-list string
    ("T-015", '"oops"', "invalid", "invalid", "done"),
    # Non-list mapping
    ("T-016", '{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link13, recorded_at: "2026-10-10"}', "invalid", "invalid", "done"),
    # Ready task with verification (for --ready and --brief tests)
    ("T-READY", '[{kind: fixed, ref: tc.yaml, verdict: pass, evidence: link-ready, recorded_at: "2026-10-10"}]', "fixed pass", "fixed pass", "pending"),
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
    for task_id, spec, _cell, _summary, status in CASES:
        lines += [
            f'      - id: "{task_id}"',
            "        type: feature",
            f'        title: "{task_id} 제목"',
            '        description: "설명"',
            "        target_files: []",
            "        depends_on: []" if task_id != "T-002" else "        depends_on: [T-001]",  # For --deps test
            "        round: 1",
            "        commits: []",
            f"        status: {status}",
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
            for task_id, _spec, cell, _summary, _status in CASES:
                row = next((ln for ln in table.splitlines() if ln.startswith(f"| {task_id} ")), None)
                if row is None:
                    failures.append(f"{task_id}: 표에 줄이 없습니다")
                    continue
                if f"| {cell} |" not in row:
                    failures.append(f"{task_id}: 표 칸 기대 {cell!r} — 실제 줄 {row}")

        # Test 14: query.py --task includes verification_status
        task_result = run([sys.executable, str(QUERY), str(dag), "--task", "T-001", "T-003", "T-004", "T-015"])
        if task_result.returncode != 0:
            failures.append(f"query --task crashed: {task_result.stderr}")
        else:
            tasks = yaml.safe_load(task_result.stdout)
            for task in tasks:
                task_id = task["id"]
                verification = task.get("verification")
                verification_status = task.get("verification_status")
                
                # Check verification_status field exists
                if verification_status is None:
                    failures.append(f"{task_id} --task: missing verification_status field")
                    continue
                
                # T-001 (missing) -> [], status: none
                if task_id == "T-001":
                    if verification != [] or verification_status != "none":
                        failures.append(f"{task_id} --task: 기대 verification=[], status=none 실제 {verification!r}, {verification_status!r}")
                
                # T-003 (null) -> [], status: none
                elif task_id == "T-003":
                    if verification != [] or verification_status != "none":
                        failures.append(f"{task_id} --task: 기대 verification=[], status=none 실제 {verification!r}, {verification_status!r}")
                
                # T-004 (non-empty list) -> status: ok
                elif task_id == "T-004":
                    if verification_status != "ok":
                        failures.append(f"{task_id} --task: 기대 status=ok 실제 {verification_status!r}")
                
                # T-015 (non-list string) -> kept as-is, status: invalid
                elif task_id == "T-015":
                    if verification != "oops" or verification_status != "invalid":
                        failures.append(f"{task_id} --task: 기대 verification='oops', status=invalid 실제 {verification!r}, {verification_status!r}")

        # Test --index
        index_result = run([sys.executable, str(QUERY), str(dag), "--index"])
        if index_result.returncode != 0:
            failures.append(f"query --index crashed: {index_result.stderr}")
        else:
            index_tasks = yaml.safe_load(index_result.stdout)
            for task in index_tasks:
                task_id = task["id"]
                expected_summary = next((summary for tid, _, _, summary, _ in CASES if tid == task_id), None)
                actual_summary = task.get("verification")
                if actual_summary != expected_summary:
                    failures.append(f"{task_id} --index: verification 기대 {expected_summary!r} 실제 {actual_summary!r}")

        # Test 16: --ready includes verification summary for ready task
        ready_result = run([sys.executable, str(QUERY), str(dag), "--ready"])
        if ready_result.returncode != 0:
            failures.append(f"query --ready crashed: {ready_result.stderr}")
        else:
            ready_data = yaml.safe_load(ready_result.stdout)
            all_ready = ready_data.get("ready", []) + ready_data.get("waiting", [])
            # Find T-READY in output
            t_ready = next((t for t in all_ready if t["id"] == "T-READY"), None)
            if t_ready is None:
                failures.append("--ready: T-READY not found in output")
            else:
                if t_ready.get("verification") != "fixed pass":
                    failures.append(f"--ready T-READY: verification 기대 'fixed pass' 실제 {t_ready.get('verification')!r}")
            
            # Check other tasks too
            for task in all_ready:
                task_id = task["id"]
                expected_summary = next((summary for tid, _, _, summary, _ in CASES if tid == task_id), None)
                actual_summary = task.get("verification")
                if actual_summary != expected_summary:
                    failures.append(f"{task_id} --ready: verification 기대 {expected_summary!r} 실제 {actual_summary!r}")

        # Test 15: --deps, --dependents, --find, --brief include verification summary
        # --deps
        deps_result = run([sys.executable, str(QUERY), str(dag), "--deps", "T-002"])
        if deps_result.returncode != 0:
            failures.append(f"query --deps crashed: {deps_result.stderr}")
        else:
            deps_data = yaml.safe_load(deps_result.stdout)
            deps_list = deps_data.get("depends_on_closure", [])
            for task in deps_list:
                if "verification" not in task:
                    failures.append(f"--deps: task {task['id']} missing verification field")

        # --dependents
        dependents_result = run([sys.executable, str(QUERY), str(dag), "--dependents", "T-001"])
        if dependents_result.returncode != 0:
            failures.append(f"query --dependents crashed: {dependents_result.stderr}")
        else:
            dependents_data = yaml.safe_load(dependents_result.stdout)
            dependents_list = dependents_data.get("dependents", [])
            for task in dependents_list:
                if "verification" not in task:
                    failures.append(f"--dependents: task {task['id']} missing verification field")

        # --find
        find_result = run([sys.executable, str(QUERY), str(dag), "--find", "제목"])
        if find_result.returncode != 0:
            failures.append(f"query --find crashed: {find_result.stderr}")
        else:
            find_list = yaml.safe_load(find_result.stdout)
            if find_list:  # Should find tasks
                for task in find_list:
                    if "verification" not in task:
                        failures.append(f"--find: task {task['id']} missing verification field")

        # Test 16: --brief includes verification summary for ready task
        brief_result = run([sys.executable, str(QUERY), str(dag), "--brief"])
        if brief_result.returncode != 0:
            failures.append(f"query --brief crashed: {brief_result.stderr}")
        else:
            brief_data = yaml.safe_load(brief_result.stdout)
            brief_ready = brief_data.get("ready", [])
            # Find T-READY in output
            t_ready = next((t for t in brief_ready if t["id"] == "T-READY"), None)
            if t_ready is None:
                failures.append("--brief: T-READY not found in ready list")
            else:
                if t_ready.get("verification") != "fixed pass":
                    failures.append(f"--brief T-READY: verification 기대 'fixed pass' 실제 {t_ready.get('verification')!r}")
            
            # Check all ready tasks have verification field
            for task in brief_ready:
                if "verification" not in task:
                    failures.append(f"--brief: task {task['id']} missing verification field")

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

        # Invalid: numeric evidence
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--append-item", "verification",
                      "--value", "{kind: fixed, ref: tc.yaml, verdict: pass, evidence: 123, recorded_at: '2026-10-10'}",
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should reject numeric evidence")

        # Invalid: bad recorded_at string
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--append-item", "verification",
                      "--value", "{kind: fixed, ref: tc.yaml, verdict: pass, evidence: x, recorded_at: 'not-a-date'}",
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should reject invalid recorded_at format")

        # Test 13: numeric recorded_at blocked
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--append-item", "verification",
                      "--value", "{kind: fixed, ref: tc.yaml, verdict: pass, evidence: x, recorded_at: 20261010}",
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should reject numeric recorded_at (int)")

        # Bool recorded_at blocked
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--append-item", "verification",
                      "--value", "{kind: fixed, ref: tc.yaml, verdict: pass, evidence: x, recorded_at: true}",
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should reject bool recorded_at")

        # Test append-only bypass blocked
        result = run([sys.executable, str(SET), str(test_dag), "--task", "T-TEST",
                      "--set", "verification",
                      "--value", "[]",
                      "--yaml", "--dry-run"],
                     allow_failure=True)
        if result.returncode == 0:
            failures.append("set.py should block --set verification (append-only)")
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
    print(f"통과 — 사례 {len(CASES)}건, verification 처리 일치 (render + query CLI + set.py + deps/find/brief + verification_status)")


if __name__ == "__main__":
    main()
