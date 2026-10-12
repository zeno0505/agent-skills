#!/usr/bin/env python3
"""set.py --init / --add-phase / 빈 phase 의 --add-task 를 본다.

1. 빈 파일·없는 파일 → --init 으로 schema 2 골격 (필수 정책 키 포함)
2. 필수 인자 누락 → 중단
3. 비어 있지 않은 파일 → --force 없이는 덮어쓰지 않음
4. 빈 phase 에 --add-task (IndexError 회귀)
5. 손으로 넣은 `phases: [{name, tasks: []}]` 블록 표기에도 --add-task
6. --add-phase: 기존 phases 뒤, phases 없음, 중복 거절
7. 생성 파일이 query.py / render.py 로 읽힘
8. 없는 --phase 는 마지막 phase 로 새지 않고 중단
9. 기존 동작(태스크가 있는 phase 에 --add-task) 유지

실행: python3 init_contract.test.py
"""

import subprocess
import sys
import tempfile
from pathlib import Path

import yaml

HERE = Path(__file__).resolve().parent
SET = HERE / "set.py"
QUERY = HERE.parent.parent / "read-dag-stack" / "scripts" / "query.py"
RENDER = HERE.parent.parent / "show-dag-stack" / "scripts" / "render.py"
INIT = ["--init", "--repo", "owner/repo", "--project-path", "sample-project",
        "--base-branch", "feature/sample/main", "--verification", "npm test",
        "--verification", "npm run lint"]
TASK = "id: T-001\ntitle: first\nstatus: pending\ndepends_on: []\n"
TASK2 = "id: T-002\ntitle: second\nstatus: pending\ndepends_on: [T-001]\n"
failures = []


def run(*args, stdin=None):
    return subprocess.run([sys.executable, str(SET), *map(str, args)], input=stdin,
                          capture_output=True, text=True)


def check(name, cond, detail=""):
    print(("ok   " if cond else "FAIL ") + name)
    if not cond:
        failures.append(name)
        if detail:
            print("     " + detail.replace("\n", "\n     "))


with tempfile.TemporaryDirectory() as tmp:
    tmp = Path(tmp)

    # 1
    empty = tmp / "a" / "dag.yaml"
    empty.parent.mkdir()
    empty.write_text("")
    r = run(empty, *INIT)
    doc = yaml.safe_load(empty.read_text())
    keys = [p["key"] for p in doc.get("project_policy", [])] if isinstance(doc, dict) else []
    check("init on empty file", r.returncode == 0 and doc["schema"] == 2 and doc["rounds"] == []
          and keys == ["base_branch", "verification"]
          and doc["phases"] == [{"name": "feature", "tasks": []}], r.stdout + r.stderr)
    missing = tmp / "new" / "slug" / "dag.yaml"
    r = run(missing, *INIT, "--phase", "build")
    check("init creates missing file", r.returncode == 0 and
          yaml.safe_load(missing.read_text())["phases"][0]["name"] == "build", r.stdout)

    # 2
    r = run(tmp / "b.yaml", "--init", "--repo", "o/r", "--project-path", "p")
    check("init without base_branch fails", r.returncode != 0 and not (tmp / "b.yaml").exists())

    # 3
    before = empty.read_text()
    r = run(empty, *INIT)
    check("init refuses non-empty", r.returncode != 0 and empty.read_text() == before)
    r = run(empty, *INIT, "--force")
    check("init --force overwrites", r.returncode == 0)

    # 4
    r = run(empty, "--add-task", "--value-file", "-", "--yaml", stdin=TASK)
    r2 = run(empty, "--add-task", "--value-file", "-", "--yaml", stdin=TASK2)
    doc = yaml.safe_load(empty.read_text())
    ids = [t["id"] for t in doc["phases"][0]["tasks"]]
    check("add-task into empty phase", r.returncode == 0 and r2.returncode == 0
          and ids == ["T-001", "T-002"], r.stdout + r.stderr + r2.stdout + r2.stderr)

    # 5
    hand = tmp / "hand.yaml"
    hand.write_text("schema: 2\nrounds: []\nphases:\n- name: feature\n  tasks: []\n")
    r = run(hand, "--add-task", "--phase", "feature", "--value-file", "-", "--yaml", stdin=TASK)
    check("add-task into hand-written empty phase", r.returncode == 0 and
          yaml.safe_load(hand.read_text())["phases"][0]["tasks"][0]["id"] == "T-001",
          r.stdout + r.stderr)

    # 6
    r = run(empty, "--add-phase", "cleanup")
    r2 = run(empty, "--add-task", "--phase", "cleanup", "--value-file", "-", "--yaml",
             stdin="id: T-003\ntitle: third\nstatus: pending\n")
    doc = yaml.safe_load(empty.read_text())
    check("add-phase after existing", r.returncode == 0 and r2.returncode == 0
          and [p["name"] for p in doc["phases"]] == ["feature", "cleanup"]
          and doc["phases"][1]["tasks"][0]["id"] == "T-003", r.stdout + r.stderr + r2.stdout)
    check("add-phase duplicate refused", run(empty, "--add-phase", "cleanup").returncode != 0)
    nophase = tmp / "nophase.yaml"
    nophase.write_text("schema: 2\nrounds: []\n")
    r = run(nophase, "--add-phase", "feature")
    r2 = run(nophase, "--add-task", "--value-file", "-", "--yaml", stdin=TASK)
    check("add-phase when phases missing", r.returncode == 0 and r2.returncode == 0 and
          yaml.safe_load(nophase.read_text())["phases"][0]["tasks"][0]["id"] == "T-001",
          r.stdout + r.stderr + r2.stdout + r2.stderr)
    inline = tmp / "inline.yaml"
    inline.write_text("schema: 2\nphases: []\n")
    r = run(inline, "--add-phase", "feature")
    check("add-phase on phases: []", r.returncode == 0 and
          yaml.safe_load(inline.read_text())["phases"] == [{"name": "feature", "tasks": []}],
          r.stdout + r.stderr)

    before = empty.read_text()
    r = run(empty, "--add-task", "--phase", "nope", "--value-file", "-", "--yaml",
            stdin="id: T-099\ntitle: x\n")
    check("add-task to unknown phase refused", r.returncode != 0 and empty.read_text() == before,
          r.stdout)

    # 7
    q = subprocess.run([sys.executable, str(QUERY), str(empty), "--task", "T-002"],
                       capture_output=True, text=True)
    check("query.py reads generated file", q.returncode == 0 and "T-002" in q.stdout,
          q.stdout + q.stderr)
    out = empty.parent / "dag.md"
    rr = subprocess.run([sys.executable, str(RENDER), str(empty)],
                        capture_output=True, text=True)
    check("render.py renders generated file", rr.returncode == 0 and out.exists()
          and "T-003" in out.read_text(), rr.stdout + rr.stderr)

    # 8
    r = run(empty, "--task", "T-001", "--set", "status", "--value", "done",
            "--expect", "status=pending")
    check("existing --set still works", r.returncode == 0 and
          yaml.safe_load(empty.read_text())["phases"][0]["tasks"][0]["status"] == "done")

print()
print("FAILED: " + ", ".join(failures) if failures else "all passed")
sys.exit(1 if failures else 0)
