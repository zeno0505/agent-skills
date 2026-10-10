#!/usr/bin/env python3
"""
set.py — dag.yaml 의 한 곳만 외과적으로 고친다.

yaml.safe_load → safe_dump 왕복은 이 파일 13,500줄을 통째로 재포맷하고 주석을 지운다.
그래서 이 도구는 대상 필드(또는 태스크)의 **줄 범위만** 갈아끼우고, 쓰기 전에 세 가지를
검증한다. 하나라도 어긋나면 아무것도 쓰지 않는다.

  1. 교체 구간 밖이 바이트로 동일한가
  2. 새 문서가 YAML 로 파싱되는가
  3. 파싱 결과가 의도한 그 한 경로에서만 원본과 다른가

Usage:
  set.py [path] --task T-137 --set status --value done
  set.py [path] --task T-137 --set description --value-file -      # stdin, 여러 줄
  set.py [path] --task T-137 --set target_files --value-file - --yaml
  set.py [path] --task T-137 --append-item deviations --value-file -
  set.py [path] --task T-137 --remove-field pr_url
  set.py [path] --remove-task T-137
  set.py [path] --add-task --phase feature --value-file - --yaml
  set.py [path] --policy-add --value-file - --yaml
  set.py [path] --policy-deprecate integration_method --superseded-by base_branch
  set.py [path] --round-add --value-file - --yaml
  set.py [path] --round 1 --set state --value merged
  set.py [path] --top schema --value 2 --yaml
옵션: --dry-run(쓰지 않고 diff 만), --expect FIELD=VALUE(현재 값이 다르면 중단)
"""

import argparse
import copy
import difflib
import os
import re
import sys
import tempfile
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[dag-set] Error: PyYAML 이 필요합니다. 실행: pip install pyyaml")
    sys.exit(1)

DEFAULT_PATH = "docs/note/dag.yaml"


class Literal(str):
    """여러 줄 문자열을 리터럴 블록(|)으로 내보내기 위한 표시."""


yaml.add_representer(
    Literal,
    lambda dumper, data: dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|"),
    Dumper=yaml.SafeDumper,
)


def fail(message):
    print(f"[dag-set] 중단: {message}")
    sys.exit(1)


def load(path: Path):
    if not path.exists():
        fail(f"{path} 를 찾을 수 없습니다")
    raw = path.read_text(encoding="utf-8")
    doc = yaml.safe_load(raw)
    if not isinstance(doc, dict):
        fail("dag.yaml 이 비었거나 매핑이 아닙니다")
    stat = path.stat()
    return raw, raw.splitlines(keepends=True), doc, (stat.st_mtime_ns, stat.st_size)


def find_toplevel_range(lines, key):
    """최상위 키 하나의 줄 범위. 없으면 None."""
    head = re.compile(r"^" + re.escape(key) + r":")
    for index, line in enumerate(lines):
        if head.match(line):
            end = index + 1
            while end < len(lines):
                stripped = lines[end].strip()
                # 최상위 시퀀스는 0열에 "- " 로 오므로 들여쓰기만으로는 블록 끝을 못 가른다
                is_item = stripped.startswith("- ")
                if stripped and not lines[end][0].isspace() and not is_item \
                        and not stripped.startswith("#"):
                    break
                end += 1
            return index, end
    return None


def toplevel_insert_point(lines):
    """새 최상위 키를 넣을 자리 — phases 바로 앞(없으면 파일 끝)."""
    for index, line in enumerate(lines):
        if line.startswith("phases:"):
            return index
    return len(lines)


def write_toplevel(path, lines, doc, expected, stat, key, value, dry_run, label):
    """최상위 리스트 블록(project_policy·rounds)을 통째로 다시 쓴다.

    태스크와 달리 이 블록들은 항목 수가 적어 재포맷 비용이 무시할 만하고,
    항목 안에서 한 필드만 고치는 경우가 대부분이라 줄 단위로 찾는 것보다 안전하다."""
    expected[key] = value
    chunk = render({key: value}, 0)
    span = find_toplevel_range(lines, key)
    if span is None:
        point = toplevel_insert_point(lines)
        start = end = point
    else:
        start, end = span
    commit(path, lines, start, end, chunk, expected, stat, dry_run, label)


def all_tasks(doc):
    return [t for phase in doc.get("phases", []) or [] for t in phase.get("tasks", []) or []]


def find_task_block(lines, task_id):
    """태스크 리스트 항목의 줄 범위와 키 들여쓰기를 찾는다."""
    head = re.compile(r"^(\s*)(- )?id:\s*['\"]?" + re.escape(task_id) + r"['\"]?\s*$")
    for index, line in enumerate(lines):
        match = head.match(line)
        if not match:
            continue
        key_indent = len(match.group(1)) + (2 if match.group(2) else 0)
        start = index
        while start > 0 and not lines[start].lstrip().startswith("- "):
            start -= 1
        end = index + 1
        while end < len(lines):
            stripped = lines[end].strip()
            if stripped:
                indent = len(lines[end]) - len(lines[end].lstrip())
                if indent < key_indent or (indent == key_indent - 2 and stripped.startswith("- ")):
                    break
            end += 1
        return start, end, key_indent
    fail(f"태스크 {task_id} 를 찾을 수 없습니다")


def find_field_range(lines, block_start, block_end, key_indent, field):
    """필드의 줄 범위. 시퀀스 항목이 키와 같은 들여쓰기로 오는 표기도 범위에 넣는다."""
    head = re.compile(r"^\s{%d}%s:" % (key_indent, re.escape(field)))
    for index in range(block_start, block_end):
        if head.match(lines[index]):
            end = index + 1
            while end < block_end:
                stripped = lines[end].strip()
                if stripped:
                    indent = len(lines[end]) - len(lines[end].lstrip())
                    is_item = indent == key_indent and stripped.startswith("- ")
                    if indent <= key_indent and not is_item:
                        break
                end += 1
            return index, end
    return None


def as_literal(value):
    """여러 줄 문자열은 리터럴 블록으로 낸다 — 따옴표 이스케이프로 뭉개지지 않게."""
    if isinstance(value, str) and "\n" in value:
        return Literal(value)
    if isinstance(value, list):
        return [as_literal(item) for item in value]
    if isinstance(value, dict):
        return {key: as_literal(item) for key, item in value.items()}
    return value


def render(value, indent):
    text = yaml.safe_dump(as_literal(value), allow_unicode=True, sort_keys=False, width=100)
    pad = " " * indent
    return [pad + line if line.strip() else line for line in text.splitlines(keepends=True)]


def commit(path, lines, start, end, chunk, expected_doc, original_stat, dry_run, label):
    """교체 → 3중 검증 → 원자적 쓰기. 검증에 걸리면 아무것도 쓰지 않는다."""
    new_lines = lines[:start] + chunk + lines[end:]
    new_raw = "".join(new_lines)

    if "".join(lines[:start]) != "".join(new_lines[:start]):
        fail("교체 구간 앞이 변했습니다")
    if "".join(lines[end:]) != "".join(new_lines[start + len(chunk):]):
        fail("교체 구간 뒤가 변했습니다")

    try:
        new_doc = yaml.safe_load(new_raw)
    except yaml.YAMLError as error:
        fail(f"결과가 YAML 로 파싱되지 않습니다 — {error}")
    if new_doc != expected_doc:
        fail("의도하지 않은 값 변화가 있습니다 (파일은 그대로 두었습니다)")

    diff = list(
        difflib.unified_diff(
            [l.rstrip("\n") for l in lines[max(0, start - 2):end + 2]],
            [l.rstrip("\n") for l in new_lines[max(0, start - 2):start + len(chunk) + 2]],
            lineterm="",
            n=1,
        )
    )
    print(f"[dag-set] {label}")
    print(f"[dag-set] 교체 줄범위 {start + 1}~{end}, 줄수 변화 {len(new_lines) - len(lines):+d}")
    for line in diff[2:22]:
        print("  " + line)
    if len(diff) > 22:
        print(f"  … 외 {len(diff) - 22}줄")

    if dry_run:
        print("[dag-set] --dry-run 이라 쓰지 않았습니다")
        return

    current = path.stat()
    if (current.st_mtime_ns, current.st_size) != original_stat:
        fail("읽은 뒤 다른 곳에서 파일이 바뀌었습니다. 다시 조회한 뒤 재시도하세요")

    handle = tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=str(path.parent), prefix=".dag-set-", delete=False
    )
    with handle:
        handle.write(new_raw)
    os.replace(handle.name, path)
    print(f"[dag-set] 기록했습니다: {path}")


def read_value(args):
    if args.value is not None:
        text = args.value
    elif args.value_file:
        text = sys.stdin.read() if args.value_file == "-" else Path(args.value_file).read_text("utf-8")
    else:
        fail("--value 또는 --value-file 로 값을 주세요")
    if args.yaml:
        return yaml.safe_load(text)
    return text.rstrip("\n")


def validate_verification_entry(entry):
    """verification 항목의 필수 조건을 검증한다. 실패 시 fail() 호출."""
    if not isinstance(entry, dict):
        fail("verification 항목은 매핑이어야 합니다 (--yaml 과 함께 쓰세요)")
    
    kind = entry.get("kind")
    if kind not in ("fixed", "exploratory"):
        fail(f"kind 는 'fixed' 또는 'exploratory' 여야 합니다 (받은 값: {kind!r})")
    
    verdict = entry.get("verdict")
    if verdict not in ("pass", "fail", "blocked"):
        fail(f"verdict 는 'pass', 'fail', 'blocked' 중 하나여야 합니다 (받은 값: {verdict!r})")
    
    if "evidence" not in entry or not entry["evidence"]:
        fail("evidence 는 필수입니다")
    
    recorded_at = entry.get("recorded_at")
    if not recorded_at:
        fail("recorded_at 는 필수입니다 (ISO 8601: YYYY-MM-DD 또는 YYYY-MM-DDTHH:MM:SS+offset)")
    
    # Validate recorded_at is parsable ISO 8601
    from datetime import datetime
    try:
        # Try parsing as ISO 8601
        datetime.fromisoformat(str(recorded_at).replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        fail(f"recorded_at 가 유효한 ISO 8601 형식이 아닙니다: {recorded_at!r} ({exc})")
    
    # ref는 exploratory일 때만 선택
    if kind != "exploratory" and "ref" not in entry:
        fail("ref 는 kind='fixed' 일 때 필수입니다")


def check_expect(task, expect):
    if not expect:
        return
    field, _, wanted = expect.partition("=")
    actual = task.get(field)
    if str(actual) != wanted:
        fail(f"--expect 불일치: {field} 가 {actual!r} 입니다 (기대 {wanted!r})")


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("path", nargs="?", default=DEFAULT_PATH)
    parser.add_argument("--task", metavar="ID", help="대상 태스크")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--set", metavar="FIELD", help="필드를 통째로 바꾼다 (없으면 새로 넣는다)")
    mode.add_argument("--append-item", metavar="FIELD", help="리스트 필드에 항목 하나를 덧붙인다")
    mode.add_argument("--remove-field", metavar="FIELD", help="필드를 지운다")
    mode.add_argument("--remove-task", metavar="ID", help="태스크를 통째로 지운다")
    mode.add_argument("--add-task", action="store_true", help="phase 끝에 태스크를 새로 넣는다")
    mode.add_argument("--policy-add", action="store_true", help="project_policy 에 항목을 넣는다")
    mode.add_argument("--policy-deprecate", metavar="KEY", help="정책 항목을 legacy: true 로 접는다")
    mode.add_argument("--round-add", action="store_true", help="rounds 에 회차를 넣는다")
    mode.add_argument("--top", metavar="KEY", help="최상위 키 하나를 넣거나 바꾼다 (phases 제외)")
    parser.add_argument("--phase", help="--add-task 대상 phase 이름 (기본: 마지막 phase)")
    parser.add_argument("--round", type=int, metavar="N", help="--set 대상 회차 번호")
    parser.add_argument("--superseded-by", metavar="KEY", help="--policy-deprecate 가 가리킬 후속 정책")
    parser.add_argument("--value", help="값 (한 줄일 때)")
    parser.add_argument("--value-file", help="값을 읽을 파일. '-' 는 stdin")
    parser.add_argument("--yaml", action="store_true", help="값을 YAML 로 해석 (리스트·매핑·숫자·null)")
    parser.add_argument("--expect", metavar="FIELD=VALUE", help="현재 값이 다르면 중단")
    parser.add_argument("--dry-run", action="store_true", help="쓰지 않고 바뀔 내용만 본다")
    args = parser.parse_args()

    path = Path(args.path)
    raw, lines, doc, stat = load(path)
    expected = copy.deepcopy(doc)

    if args.top:
        if args.top == "phases":
            fail("phases 는 이 모드로 바꾸지 않습니다")
        value = read_value(args)
        write_toplevel(path, lines, doc, expected, stat, args.top, value,
                       args.dry_run, f"최상위 {args.top} 설정")
        return

    if args.policy_add:
        item = read_value(args)
        if not isinstance(item, dict) or "key" not in item:
            fail("--policy-add 값은 key 를 가진 매핑이어야 합니다 (--yaml 과 함께 쓰세요)")
        items = list(doc.get("project_policy") or [])
        if not isinstance(doc.get("project_policy"), (list, type(None))):
            fail("project_policy 가 리스트가 아닙니다 — 먼저 migrate.py 로 승격하세요")
        item.setdefault("legacy", False)
        items.append(item)
        write_toplevel(path, lines, doc, expected, stat, "project_policy", items,
                       args.dry_run, f"정책 {item['key']} 추가")
        return

    if args.policy_deprecate:
        items = doc.get("project_policy")
        if not isinstance(items, list):
            fail("project_policy 가 리스트가 아닙니다 — 먼저 migrate.py 로 승격하세요")
        # project_policy 는 평문 문자열 규칙과 key 매핑이 섞인 리스트다. 문자열에는 key 가 없다.
        target = next((i for i in items
                       if isinstance(i, dict) and i.get("key") == args.policy_deprecate), None)
        if target is None:
            fail(f"정책 {args.policy_deprecate} 를 찾을 수 없습니다")
        updated = []
        for entry in items:
            if not isinstance(entry, dict):
                updated.append(entry)
                continue
            entry = dict(entry)
            if entry.get("key") == args.policy_deprecate:
                entry["legacy"] = True
                if args.superseded_by:
                    entry["superseded_by"] = args.superseded_by
            updated.append(entry)
        write_toplevel(path, lines, doc, expected, stat, "project_policy", updated,
                       args.dry_run, f"정책 {args.policy_deprecate} 폐기")
        return

    if args.round_add:
        entry = read_value(args)
        if not isinstance(entry, dict) or "number" not in entry:
            fail("--round-add 값은 number 를 가진 매핑이어야 합니다 (--yaml 과 함께 쓰세요)")
        entries = list(doc.get("rounds") or [])
        if any(r.get("number") == entry["number"] for r in entries):
            fail(f"회차 {entry['number']} 는 이미 있습니다")
        entries.append(entry)
        write_toplevel(path, lines, doc, expected, stat, "rounds", entries,
                       args.dry_run, f"회차 {entry['number']} 추가")
        return

    if args.round is not None:
        if not args.set:
            fail("--round 는 --set FIELD 와 함께 씁니다")
        entries = doc.get("rounds")
        if not isinstance(entries, list):
            fail("rounds 가 없습니다 — 먼저 --round-add 로 회차를 여세요")
        if not any(r.get("number") == args.round for r in entries):
            fail(f"회차 {args.round} 를 찾을 수 없습니다")
        value = read_value(args)
        updated = []
        for entry in entries:
            entry = dict(entry)
            if entry.get("number") == args.round:
                entry[args.set] = value
            updated.append(entry)
        write_toplevel(path, lines, doc, expected, stat, "rounds", updated,
                       args.dry_run, f"회차 {args.round}.{args.set} 갱신")
        return

    if args.add_task:
        new_task = read_value(args)
        if not isinstance(new_task, dict) or "id" not in new_task:
            fail("--add-task 값은 id 를 가진 매핑이어야 합니다 (--yaml 과 함께 쓰세요)")
        if any(t.get("id") == new_task["id"] for t in all_tasks(doc)):
            fail(f"{new_task['id']} 는 이미 있습니다")
        phases = doc.get("phases", [])
        target = next((p for p in phases if p.get("name") == args.phase), phases[-1] if phases else None)
        if target is None:
            fail("phase 를 찾을 수 없습니다")
        last = target["tasks"][-1]
        block_start, block_end, key_indent = find_task_block(lines, last["id"])
        chunk = render([new_task], key_indent - 2)
        for phase in expected["phases"]:
            if phase.get("name") == target.get("name"):
                phase["tasks"].append(new_task)
        commit(path, lines, block_end, block_end, chunk, expected, stat, args.dry_run,
               f"{new_task['id']} 를 phase '{target.get('name')}' 에 추가")
        return

    if args.remove_task:
        block_start, block_end, _ = find_task_block(lines, args.remove_task)
        for phase in expected["phases"]:
            phase["tasks"] = [t for t in phase.get("tasks", []) if t.get("id") != args.remove_task]
        commit(path, lines, block_start, block_end, [], expected, stat, args.dry_run,
               f"{args.remove_task} 삭제")
        return

    if not args.task:
        fail("--task 로 대상 태스크를 지정하세요")
    task = next((t for t in all_tasks(doc) if t.get("id") == args.task), None)
    if task is None:
        fail(f"태스크 {args.task} 를 찾을 수 없습니다")
    check_expect(task, args.expect)

    block_start, block_end, key_indent = find_task_block(lines, args.task)
    field = args.set or args.append_item or args.remove_field
    span = find_field_range(lines, block_start, block_end, key_indent, field)

    if args.remove_field:
        if span is None:
            fail(f"{args.task} 에 {field} 가 없습니다")
        for phase in expected["phases"]:
            for entry in phase.get("tasks", []):
                if entry.get("id") == args.task:
                    entry.pop(field, None)
        commit(path, lines, span[0], span[1], [], expected, stat, args.dry_run,
               f"{args.task}.{field} 삭제")
        return

    item = None
    if args.append_item:
        current = task.get(field)
        if current is not None and not isinstance(current, list):
            fail(f"{field} 는 리스트가 아닙니다")
        item = read_value(args)
        # verification 필드일 때 validation
        if field == "verification":
            validate_verification_entry(item)
        value = list(current or []) + [item]
    else:
        value = read_value(args)

    for phase in expected["phases"]:
        for entry in phase.get("tasks", []):
            if entry.get("id") == args.task:
                entry[field] = value

    # 인라인 표기(`commits: []`, `depends_on: ["T-1"]`)에는 블록 항목을 끼워 넣을 수 없다 —
    # 그 아래에 `- x` 를 붙이면 파싱 불가한 YAML 이 된다. 그럴 때는 필드를 통째로 다시 쓴다.
    can_splice = bool(span) and any(
        lines[i].strip().startswith("- ") for i in range(span[0], span[1])
    )
    if args.append_item and can_splice:
        # 기존 항목은 한 글자도 건드리지 않고 새 항목만 끼워 넣는다
        chunk = render([item], key_indent)
        start = end = span[1]
        verb = "덧붙임"
    else:
        chunk = render({field: value}, key_indent)
        start, end = span if span else (block_end, block_end)
        verb = "교체" if span else "신규"
    commit(path, lines, start, end, chunk, expected, stat, args.dry_run,
           f"{args.task}.{field} {verb}")


if __name__ == "__main__":
    main()
