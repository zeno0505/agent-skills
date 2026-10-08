#!/usr/bin/env python3
"""query.py 와 render.py 가 같은 입력에서 같은 판정을 내는지 본다.

시험이 도는 이유는 둘이다.

1. **판정 규칙이 두 파일에 있다.** `--coverage` 의 세는 규칙과 표의 E2E 칸이 같은 술어를
   따로 구현하고 있어, 한쪽만 고치면 조용히 갈린다. 여기서 어긋나면 실패한다.
2. **픽스처가 실제 입력 범위를 덮는지 본다.** 이 프로젝트의 리뷰가 「픽스처가 좁아
   통과한 것들」을 반복 패턴으로 지적했다. e2e 필드가 매핑이 아닌 경우, covered_by 가
   리스트가 아닌 경우, required 가 참 같은 값인 경우를 일부러 넣는다.

실행: python3 coverage_contract.test.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUERY = HERE / "query.py"
RENDER = HERE.parents[1] / "show-dag-stack" / "scripts" / "render.py"

# (태스크 id, e2e 블록 YAML, 상태, 기대하는 표 칸, 커버리지 분류)
CASES = [
    ("T-001", None, "done", "—", None),
    ("T-002", '{required: false, reason: "서버 전용"}', "done", "불필요", None),
    ("T-003", '{required: true, covered_by: ["TC-A-001"]}', "done", "TC-A-001", None),
    ("T-004", '{required: true, covered_by: []}', "done", "**미충족**", "uncovered_done"),
    ("T-005", '{required: true, covered_by: []}', "pending", "**미충족**", "uncovered_open"),
    ("T-006", '{required: true}', "done", "**미충족**", "uncovered_done"),
    # 매핑이 아닌 값 — 필드가 있다고 판정에 끌어들이면 죽는다
    ("T-007", '"필요함"', "done", "—", None),
    ("T-008", "[]", "done", "—", None),
    # covered_by 가 리스트가 아닌 경우 — 덮였다고 읽으면 위양성 통과다
    ("T-009", '{required: true, covered_by: "TC-A-002"}', "done", "**형식오류**", "malformed"),
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
    for task_id, spec, status, _cell, _bucket in CASES:
        lines += [
            f'      - id: "{task_id}"',
            "        type: feature",
            f'        title: "{task_id} 제목"',
            '        description: "설명"',
            "        target_files: []",
            "        depends_on: []",
            "        round: 1",
            "        commits: []",
            f"        status: {status}",
            "        deviations: []",
        ]
        if spec is not None:
            lines.append(f"        e2e: {spec}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run(cmd):
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"실패: {' '.join(str(c) for c in cmd)}\n{done.stderr}")
    return done.stdout


def main():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        dag = Path(tmp) / "dag.yaml"
        build(dag)

        import yaml

        report = yaml.safe_load(run([sys.executable, str(QUERY), str(dag), "--coverage"]))
        run([sys.executable, str(RENDER), str(dag)])
        table = (Path(tmp) / "dag.md").read_text(encoding="utf-8")

        expected = {"uncovered_done": set(), "uncovered_open": set(), "malformed": set()}
        for task_id, _spec, _status, _cell, bucket in CASES:
            if bucket:
                expected[bucket].add(task_id)

        for bucket, want in expected.items():
            got = {entry["id"] for entry in report[bucket]}
            if got != want:
                failures.append(f"{bucket}: 기대 {sorted(want)} 실제 {sorted(got)}")

        declared = sum(1 for _i, spec, _s, _c, _b in CASES if spec and spec.startswith("{"))
        if report["declared"] != declared:
            failures.append(f"declared: 기대 {declared} 실제 {report['declared']}")

        # 표의 칸이 커버리지 판정과 어긋나지 않는지
        for task_id, _spec, _status, cell, _bucket in CASES:
            row = next((ln for ln in table.splitlines() if ln.startswith(f"| {task_id} ")), None)
            if row is None:
                failures.append(f"{task_id}: 표에 줄이 없습니다")
                continue
            if f"| {cell} |" not in row:
                failures.append(f"{task_id}: 표 칸 기대 {cell!r} — 실제 줄 {row}")

    if failures:
        print("어긋남:")
        for line in failures:
            print(f"  - {line}")
        raise SystemExit(1)
    print(f"통과 — 사례 {len(CASES)}건, 두 스크립트 판정 일치")


if __name__ == "__main__":
    main()
