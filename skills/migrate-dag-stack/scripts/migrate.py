#!/usr/bin/env python3
"""
migrate.py — 구 스키마 dag.yaml 을 회차(rounds) 모델로 승격한다.

구 스키마는 태스크 하나가 브랜치·PR 하나였다. 회차 모델에서는 PR 하나가 여러 태스크를
담으므로, 태스크는 `round` 로 자기 회차를 가리키고 PR 정보는 `rounds[]` 가 진다.

이 스크립트는 **파일의 모양만** 승격한다. 열려 있는 PR 을 접는 것(open 은 리뷰를 처리해
머지, 미리뷰 draft 는 하나로 합치기)은 git·gh 를 만지는 일이라 migrate-dag-stack 스킬이
지휘한다. 여기서는 그 대상이 무엇인지 보고만 한다.

쓰기는 set.py 의 줄 찾기·렌더링을 그대로 빌려 쓰되, 편집을 모아 **한 번에** 갈아끼운다.
태스크마다 set.py 를 부르면 1.2MB 파일을 수백 번 다시 파싱해 분 단위로 늘어진다.
검증은 같다 — 다 붙인 결과가 의도한 문서와 정확히 같을 때만 쓴다. 주석은 통째로 다시
쓰는 블록(project_policy·rounds) 안의 것만 사라진다.

Usage:
  migrate.py <dag.yaml> --plan
  migrate.py <dag.yaml> --apply [--map-awaiting-review done] [--base-branch develop]
"""

import argparse
import copy
import importlib.util
import os
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[dag-migrate] Error: PyYAML 이 필요합니다. 실행: pip install pyyaml")
    sys.exit(1)

SET_PY = Path(__file__).resolve().parents[2] / "set-dag-stack" / "scripts" / "set.py"


def _load_set_module():
    spec = importlib.util.spec_from_file_location("dag_set", SET_PY)
    if spec is None or spec.loader is None:
        print(f"[dag-migrate] Error: {SET_PY} 를 불러올 수 없습니다")
        sys.exit(1)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


dag_set = _load_set_module()

# 구 어휘 → 신 어휘. review_required 는 일부러 넣지 않는다 — 그 태스크들은 실제로 열린
# PR 을 갖고 있어서, 접는 방식이 정해진 뒤에야 회차와 상태가 결정된다.
STATUS_MAP = {"in_progress": "running"}
NEW_STATUSES = {
    "pending", "running", "committed", "in_review",
    "done", "blocked", "deferred", "superseded",
}
ROUND_ZERO_NOTE = "승격 이전 구간 — 태스크당 PR 또는 직접 병합으로 이미 들어갔다"


def load(path: Path):
    if not path.exists():
        print(f"[dag-migrate] Error: {path} 를 찾을 수 없습니다")
        sys.exit(1)
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        print("[dag-migrate] Error: dag.yaml 이 비었거나 매핑이 아닙니다")
        sys.exit(1)
    tasks = [t for p in data.get("phases", []) or [] for t in p.get("tasks", []) or []]
    return raw, data, tasks


def policy_as_items(data):
    """자유 맵을 항목 리스트로 옮긴다. 정한 날을 모르므로 decided_at 은 비운다."""
    raw = data.get("project_policy")
    if isinstance(raw, list):
        return None
    if not isinstance(raw, dict):
        return []
    return [
        {"key": key, "decided_at": None, "decision": value, "legacy": False}
        for key, value in raw.items()
    ]


def build_plan(data, tasks, args):
    steps, notes = [], []

    if data.get("schema") == 2:
        print("[dag-migrate] 이미 승격된 파일입니다 (schema: 2). 할 일이 없습니다.")
        sys.exit(0)

    items = policy_as_items(data)
    if items is None:
        notes.append("project_policy 는 이미 항목 리스트입니다 — 그대로 둡니다.")
    else:
        steps.append(("policy", items))
        if items:
            notes.append(
                f"project_policy {len(items)}건을 항목으로 옮깁니다. decided_at 은 비어 있으니, "
                "승격 뒤 폐기할 정책은 set.py --policy-deprecate 로 접으세요."
            )

    if not isinstance(data.get("rounds"), list):
        steps.append(("rounds", [{"number": 0, "state": "merged", "note": ROUND_ZERO_NOTE}]))

    remap, unknown, round_zero, undecided = [], [], [], []
    for task in tasks:
        status = str(task.get("status"))
        target = STATUS_MAP.get(status)
        if status == "awaiting_review":
            if args.map_awaiting_review:
                target = args.map_awaiting_review
            else:
                unknown.append((task.get("id"), status))
        if target:
            remap.append((task.get("id"), status, target))
            status = target
        elif status not in NEW_STATUSES and status not in ("review_required",):
            unknown.append((task.get("id"), status))

        if task.get("round") is not None:
            continue
        if status == "done":
            round_zero.append(task.get("id"))
        else:
            undecided.append((task.get("id"), status))

    for task_id, _, target in remap:
        steps.append(("status", task_id, target))
    for task_id in round_zero:
        steps.append(("round", task_id, 0))

    steps.append(("top", "legacy", True))
    steps.append(("top", "schema", 2))

    if remap:
        notes.append(f"상태 어휘 {len(remap)}건을 바꿉니다: " + ", ".join(
            f"{i}({a}→{b})" for i, a, b in remap[:8]
        ) + (" …" if len(remap) > 8 else ""))
    if round_zero:
        notes.append(f"이미 들어간 {len(round_zero)}건을 round: 0 으로 표시합니다.")
    if undecided:
        by_status = {}
        for task_id, status in undecided:
            by_status.setdefault(status, []).append(task_id)
        notes.append(
            "회차를 정하지 않은 태스크 "
            f"{len(undecided)}건: "
            + ", ".join(f"{s} {len(v)}건" for s, v in sorted(by_status.items()))
            + " — 이들의 회차는 열린 PR 을 접는 방식이 정해진 뒤에 배정합니다."
        )
    if unknown:
        notes.append(
            "신 어휘에 없는 상태가 있습니다: "
            + ", ".join(f"{i}({s})" for i, s in unknown[:8])
            + (" …" if len(unknown) > 8 else "")
            + " — awaiting_review 는 --map-awaiting-review 로 지정하세요."
        )
    if args.base_branch:
        steps.append(("policy-add", {
            "key": "base_branch",
            "decided_at": None,
            "decision": args.base_branch,
            "rationale": "승격 시점에 지정",
            "legacy": False,
        }))
    else:
        notes.append(
            "base_branch 정책이 필요합니다 — --base-branch 로 주거나 승격 뒤 "
            "set.py --policy-add 로 넣으세요."
        )
    return steps, notes


def set_task_field(doc, task_id, field, value):
    for phase in doc.get("phases", []) or []:
        for task in phase.get("tasks", []) or []:
            if task.get("id") == task_id:
                task[field] = value


def apply(path, raw, doc, steps):
    lines = raw.splitlines(keepends=True)
    expected = copy.deepcopy(doc)
    edits = []  # (start, end, chunk) — 전부 원본 줄 번호 기준

    top_values = {}
    for step in steps:
        kind = step[0]
        if kind == "policy":
            top_values["project_policy"] = step[1]
        elif kind == "rounds":
            top_values["rounds"] = step[1]
        elif kind == "top":
            top_values[step[1]] = step[2]
        elif kind == "policy-add":
            base = top_values.get("project_policy")
            if base is None:
                base = list(doc.get("project_policy") or [])
            top_values["project_policy"] = list(base) + [step[1]]
        elif kind in ("status", "round"):
            task_id, value = step[1], step[2]
            field = "status" if kind == "status" else "round"
            block_start, block_end, key_indent = dag_set.find_task_block(lines, task_id)
            span = dag_set.find_field_range(lines, block_start, block_end, key_indent, field)
            chunk = dag_set.render({field: value}, key_indent)
            edits.append(span + (chunk,) if span else (block_end, block_end, chunk))
            set_task_field(expected, task_id, field, value)

    insert_at = dag_set.toplevel_insert_point(lines)
    appended = []
    for key, value in top_values.items():
        expected[key] = value
        chunk = dag_set.render({key: value}, 0)
        span = dag_set.find_toplevel_range(lines, key)
        if span is None:
            appended.extend(chunk)
        else:
            edits.append((span[0], span[1], chunk))
    if appended:
        edits.append((insert_at, insert_at, appended))

    overlap = sorted(edits, key=lambda e: e[0])
    for previous, current in zip(overlap, overlap[1:]):
        if current[0] < previous[1]:
            print("[dag-migrate] 중단: 편집 구간이 겹칩니다 (파일은 그대로 두었습니다)")
            sys.exit(1)

    for start, end, chunk in sorted(edits, key=lambda e: e[0], reverse=True):
        lines = lines[:start] + chunk + lines[end:]
    new_raw = "".join(lines)

    try:
        new_doc = yaml.safe_load(new_raw)
    except yaml.YAMLError as error:
        print(f"[dag-migrate] 중단: 결과가 YAML 로 파싱되지 않습니다 — {error}")
        sys.exit(1)
    if new_doc != expected:
        print("[dag-migrate] 중단: 의도하지 않은 값 변화가 있습니다 (파일은 그대로 두었습니다)")
        sys.exit(1)

    backup = path.with_suffix(path.suffix + ".pre-migrate")
    backup.write_text(raw, encoding="utf-8")
    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), prefix=".dag-migrate-", delete=False
    )
    with handle:
        handle.write(new_raw)
    os.replace(handle.name, path)
    print(f"[dag-migrate] {len(edits)}곳을 한 번에 적용했습니다: {path}")
    print(f"[dag-migrate] 승격 전 원본: {backup}")


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("path")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--plan", action="store_true", help="바꿀 내용만 보고 쓰지 않는다")
    mode.add_argument("--apply", action="store_true", help="실제로 승격한다")
    parser.add_argument("--map-awaiting-review", metavar="STATUS",
                        help="awaiting_review 를 어느 상태로 옮길지 (보통 done)")
    parser.add_argument("--base-branch", metavar="BRANCH",
                        help="base_branch 정책으로 넣을 브랜치")
    args = parser.parse_args()

    path = Path(args.path)
    raw, data, tasks = load(path)
    steps, notes = build_plan(data, tasks, args)

    print(f"[dag-migrate] 태스크 {len(tasks)}건, 적용할 단계 {len(steps)}개")
    for line in notes:
        print(f"  - {line}")

    if args.plan:
        print("[dag-migrate] --plan 이라 쓰지 않았습니다")
        return
    apply(path, raw, data, steps)
    print("[dag-migrate] 열린 PR 을 접는 일은 하지 않았습니다 — migrate-dag-stack 스킬이 지휘합니다.")


if __name__ == "__main__":
    main()
