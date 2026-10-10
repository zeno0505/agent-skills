#!/usr/bin/env python3
"""
query.py — dag.yaml 을 통째로 읽지 않고 필요한 조각만 꺼낸다.

dag.yaml 은 description·deviations 가 무게의 4분의 3을 차지해 전체를 읽으면
수십만 토큰이 든다. 그 둘은 지금 만지는 태스크 하나에만 필요한 산문이므로,
색인과 본문을 분리해 꺼내는 것만으로 대부분의 조회가 100분의 1로 줄어든다.

이 스크립트도 render.py 와 같은 규약을 따른다 — 상태 값을 알지 못한다.
'완료' 로 볼 상태는 --done-status 로 받는 질의 인자이지 검증 규칙이 아니다.

Usage:
  query.py [path] --stats
  query.py [path] --index [--status pending] [--fields id,title,status]
  query.py [path] --ready
  query.py [path] --task T-137 [T-138 ...] [--with-deviations]
  query.py [path] --deps T-063
  query.py [path] --dependents T-059
  query.py [path] --find 자동화
  query.py [path] --policy [--all] [--policy-key base_branch]
  query.py [path] --rounds
  query.py [path] --pr
  query.py [path] --brief
  query.py [path] --coverage
  query.py [path] --key rounds
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[dag-query] Error: PyYAML 이 필요합니다. 실행: pip install pyyaml")
    sys.exit(1)

DEFAULT_PATH = "docs/note/dag.yaml"
DEFAULT_INDEX_FIELDS = ["id", "title", "status", "depends_on", "type"]
SNIPPET_RADIUS = 70
CHECKLIST_NAME = "e2e-checklist.md"


def emit(payload):
    print(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, width=100).rstrip())


def note(message):
    """본문이 아닌 안내는 stderr 로 보내 출력을 그대로 파싱할 수 있게 둔다."""
    print(f"# {message}", file=sys.stderr)


def approx_tokens(text: str) -> int:
    hangul = sum(1 for char in text if "가" <= char <= "힣")
    return int(hangul * 1.2 + (len(text) - hangul) / 3.5)


def load(path: Path):
    if not path.exists():
        print(f"[dag-query] Error: {path} 를 찾을 수 없습니다")
        sys.exit(1)
    raw = path.read_text(encoding="utf-8")
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        print("[dag-query] Error: dag.yaml 이 비었거나 매핑이 아닙니다")
        sys.exit(1)
    tasks = [t for phase in data.get("phases", []) or [] for t in phase.get("tasks", []) or []]
    # Do NOT normalize verification here - let verification_summary() handle it
    # This preserves original malformed data for inspection via --task
    return raw, data, tasks


def resolve(tasks, task_id):
    for task in tasks:
        if task.get("id") == task_id:
            return task
    near = [t["id"] for t in tasks if task_id.lower() in str(t.get("id", "")).lower()]
    print(f"[dag-query] Error: 태스크 {task_id} 를 찾을 수 없습니다")
    if near:
        print(f"[dag-query] 비슷한 id: {', '.join(near[:10])}")
    sys.exit(1)


def slim(task, fields):
    return {key: task[key] for key in fields if key in task}


def normalize_timestamp_query(value):
    """recorded_at를 aware datetime으로 파싱한다 (query.py 버전, render.py와 동일).
    
    ISO 8601 timestamp (date-only, naive, or with offset) 또는 Python date/datetime 객체를
    aware datetime으로 변환하여 chronological comparison 가능하게 한다.
    
    - date-only (2026-10-10) → start of day UTC
    - naive datetime → treat as UTC
    - aware datetime → as-is
    - unparsable → None (oldest)
    
    Returns: aware datetime or None
    """
    from datetime import datetime, timezone
    
    if value is None:
        return None
    
    # Python date object
    if hasattr(value, "year") and not hasattr(value, "hour"):
        from datetime import datetime, timezone
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    
    # Python datetime object
    if hasattr(value, "isoformat") and hasattr(value, "hour"):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    
    # String: parse ISO 8601
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                return dt.replace(tzinfo=timezone.utc)
            return dt
        except (ValueError, AttributeError):
            return None
    
    return None


def verification_summary(entries):
    """태스크의 verification 상태를 요약한다 (render.py와 동일한 로직).
    
    Returns:
    - None: no verification record (missing or null)
    - "invalid": entries exist but malformed (non-list, or all entries invalid)
    - "kind verdict": the latest valid entry's kind and verdict (e.g., "fixed pass")
    
    Valid entry rules (render.py와 동일):
    - kind in {fixed, exploratory}
    - verdict in {pass, fail, blocked}
    - evidence: non-empty string
    - recorded_at: parsable (ISO 8601 or YAML date/datetime)
    - ref: non-empty string when kind=fixed
    """
    from datetime import datetime, timezone
    
    # Missing or null -> no record
    if entries is None:
        return None
    
    # Non-list -> invalid (malformed data)
    if not isinstance(entries, list):
        return "invalid"
    
    # Empty list -> no record
    if not entries:
        return None
    
    has_any_entries = len(entries) > 0
    
    # Filter valid entries
    valid = []
    for idx, entry in enumerate(entries):
        if not isinstance(entry, dict):
            continue
        kind = entry.get("kind", "")
        verdict = entry.get("verdict", "")
        evidence = entry.get("evidence")
        recorded_at = entry.get("recorded_at")
        ref = entry.get("ref")
        
        # Check required fields (same as render.py)
        if kind not in ("fixed", "exploratory"):
            continue
        if verdict not in ("pass", "fail", "blocked"):
            continue
        # evidence must be non-empty string
        if not isinstance(evidence, str) or not evidence:
            continue
        # recorded_at must be parsable
        if normalize_timestamp_query(recorded_at) is None:
            continue
        # ref must be non-empty string when kind=fixed
        if kind == "fixed" and (not isinstance(ref, str) or not ref):
            continue
        
        valid.append((idx, entry))
    
    # If entries exist but none valid → invalid
    if has_any_entries and not valid:
        return "invalid"
    
    if not valid:
        return None
    
    # Sort by (parsed recorded_at, list position)
    latest_idx, latest = max(
        valid,
        key=lambda item: (normalize_timestamp_query(item[1].get("recorded_at", "")) or datetime.min.replace(tzinfo=timezone.utc), item[0])
    )
    
    kind = latest.get("kind", "")
    verdict = latest.get("verdict", "")
    return f"{kind} {verdict}"


def schema_version(data) -> int:
    """2 = 회차(rounds) 모델, 1 = 태스크당 PR 을 쌓던 구 스키마."""
    if data.get("schema") == 2 or isinstance(data.get("rounds"), list):
        return 2
    return 1


def policy_items(data):
    """project_policy 를 항목 리스트로 정규화한다. 구 스키마의 자유 맵도 같은 모양으로 낸다."""
    raw_policy = data.get("project_policy")
    if isinstance(raw_policy, list):
        return [dict(item) for item in raw_policy if isinstance(item, dict)]
    if isinstance(raw_policy, dict):
        return [{"key": k, "decision": v, "legacy": False} for k, v in raw_policy.items()]
    return []


def policy_value(data, key):
    for item in policy_items(data):
        if item.get("key") == key and not item.get("legacy"):
            return item.get("decision")
    return None


def rounds_of(data):
    value = data.get("rounds")
    return [dict(r) for r in value if isinstance(r, dict)] if isinstance(value, list) else []


def current_round(data):
    """지금 열려 있는 회차. merged 가 아닌 것 중 번호가 가장 큰 것."""
    live = [r for r in rounds_of(data) if str(r.get("state")) != "merged"]
    return max(live, key=lambda r: r.get("number") or 0) if live else None


def round_pr_url(data, number):
    for entry in rounds_of(data):
        if entry.get("number") == number:
            return entry.get("pr_url")
    return None


# 대괄호 안이 아이디만은 아니다 — `[CL-024 후속]` 처럼 꼬리가 붙은 줄이 실제로 있어,
# 아이디로 시작하면 그 태스크 것으로 읽는다. `[후속 제안]` 처럼 아이디가 없는 줄은 태그
# 없는 것으로 남겨 따로 센다.
CHECKLIST_LINE = re.compile(r"^\s*- \[([ xX])\]\s*\[([A-Za-z]+-\d+)[^\]]*\]")


def checklist_counts(path: Path, tasks):
    """e2e-checklist.md 의 미해결 줄을 **이 DAG 것과 남의 것으로 갈라** 센다.

    한 노트 디렉터리에 DAG 파일이 여럿 있고 체크리스트를 하나 공유하는 프로젝트가 있다
    (예: dag.yaml·back-dag.yaml·back-dag-extra.yaml 셋이 살아 있고 체크리스트는
    하나다). 줄 수만 세면 back-dag 가 프런트 태스크의 미해결 줄을 자기 것으로 읽어,
    「내 대기열이 비었다」가 영원히 참이 되지 않는다.

    귀속은 줄머리의 태스크 아이디로 한다. 남의 것과 태그 없는 줄도 버리지 않고 따로 세어
    돌려준다 — 조용히 빠지면 그 줄이 어느 DAG 것도 아닌 채 남는다.
    """
    target = path.parent / CHECKLIST_NAME
    if not target.exists():
        # 파일이 없는 것과 미해결이 0인 것은 다르다. null 을 0 으로 읽으면 확인할 것이 없다는
        # 뜻이 되어, 아무것도 검사하지 않은 채 통과하는 것과 같아진다.
        return {"file": "없음"}
    known = {str(t.get("id")) for t in tasks}
    mine = others = untagged = 0
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line.lstrip().startswith("- [ ]"):
            continue
        matched = CHECKLIST_LINE.match(line)
        if matched is None:
            untagged += 1
        elif matched.group(2) in known:
            mine += 1
        else:
            others += 1
    return {"mine": mine, "others": others, "untagged": untagged}


def coverage_report(tasks, done_status):
    """E2E 가 필요하다고 적힌 태스크가 실제로 덮여 있는지 본다.

    판정 자리는 라운드 종료가 아니라 **태스크 완료**다. 회차를 열지 않는 프로젝트가 있어
    (ai 는 PR 을 만들지 않고 verification 통과로 done 이 된다) 라운드에 걸면 그 프로젝트가
    통째로 판정 밖에 놓인다. 완료는 두 모델에 다 있다.

    `e2e` 필드가 없는 태스크는 세지 않는다 — 필드는 선택이고, 없음은 「대상 아님」이 아니라
    「아직 정하지 않음」이다. 그 구별을 여기서 지어내지 않고 declared 로만 알린다.
    """
    required, uncovered_done, uncovered_open, malformed, declared = [], [], [], [], 0
    for task in tasks:
        spec = task.get("e2e")
        if not isinstance(spec, dict):
            continue
        declared += 1
        entry = slim(task, ["id", "title"])
        covered = spec.get("covered_by")
        # 리스트가 아닌 covered_by 를 「덮였다」로 읽으면 위양성 통과다. 문자열 하나가 들어와도
        # 참이라서 그 태스크는 조용히 빠진다. 결정이 아니라 형식 오류이므로 따로 낸다.
        if covered is not None and not isinstance(covered, list):
            malformed.append(entry)
            continue
        if not spec.get("required"):
            continue
        required.append(entry)
        if covered:
            continue
        if str(task.get("status")) == done_status:
            uncovered_done.append(entry)
        else:
            uncovered_open.append(entry)
    return {
        "tasks_total": len(tasks),
        "declared": declared,
        "required": len(required),
        "uncovered_done": uncovered_done,
        "uncovered_open": uncovered_open,
        "malformed": malformed,
    }


def gate_note(data):
    """라운드 종료 보고가 이 프로젝트에서 도는지 한 줄로 말한다.

    조용히 물러나지 않게 하려는 자리다. 회차 없는 프로젝트에서 `current_round: null` 만
    나오면 읽는 쪽이 그게 「아직 안 열었다」인지 「안 쓴다」인지 알 수 없다.
    """
    entries = rounds_of(data)
    numbered = [r for r in entries if isinstance(r, dict) and (r.get("number") or 0) > 0]
    if numbered:
        return None
    if entries:
        return ("회차가 승격 이전 구간(0)뿐입니다 — 라운드 종료 보고는 돌지 않습니다. "
                "E2E 판정은 태스크 완료 기준으로만 돕니다.")
    return ("이 프로젝트에는 rounds 가 없습니다 (schema 1) — 라운드 종료 보고는 돌지 않습니다. "
            "E2E 판정은 태스크 완료 기준으로만 돕니다.")


def cmd_policy(data, args):
    items = policy_items(data)
    if args.policy_key:
        items = [i for i in items if i.get("key") == args.policy_key]
    if not args.all:
        items = [i for i in items if not i.get("legacy")]
    note(f"{len(items)}건" + ("" if args.all else " (현행만 — 폐기분은 --all)"))
    emit(items)


def cmd_rounds(data):
    entries = rounds_of(data)
    if not entries:
        note("rounds 가 없습니다 — 구 스키마이거나 아직 회차를 열지 않았습니다")
    else:
        note(f"{len(entries)}개 회차")
    emit(entries)


def cmd_pr(data, tasks):
    entry = current_round(data)
    if entry is None:
        note("열려 있는 회차가 없습니다")
        emit({})
        return
    number = entry.get("number")
    members = [t.get("id") for t in tasks if t.get("round") == number]
    payload = dict(entry)
    payload["tasks"] = members
    payload["task_counts"] = _counts([t for t in tasks if t.get("round") == number])
    # Include risk assessment fields if present
    for field in ["risk_tier", "risk_reason", "risk_signals", "risk_assessed_by"]:
        if field not in payload:
            payload[field] = None
    emit(payload)


def _counts(tasks):
    counts = {}
    for task in tasks:
        counts[str(task.get("status"))] = counts.get(str(task.get("status")), 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: -kv[1]))


BRIEF_DECISION_CHARS = 140


def _abbrev(value):
    """brief 는 정책의 존재와 요지만 보여 준다 — 전문은 --policy 로 따로 읽는다."""
    if isinstance(value, str) and len(value) > BRIEF_DECISION_CHARS:
        return value[:BRIEF_DECISION_CHARS].replace("\n", " ").rstrip() + " …(--policy)"
    return value


def cmd_brief(path, data, tasks, done_status):
    """세션 시작용 최소 컨텍스트 — 현행 정책·현재 회차·착수 가능 태스크·미해결 체크리스트."""
    status_of = {t.get("id"): str(t.get("status")) for t in tasks}
    ready = []
    for task in tasks:
        if str(task.get("status")) != "pending":
            continue
        blockers = [d for d in task.get("depends_on", []) or [] if status_of.get(d) != done_status]
        if not blockers:
            entry = slim(task, ["id", "title"])
            entry["verification"] = verification_summary(task.get("verification"))
            ready.append(entry)

    entry = current_round(data)
    round_view = None
    if entry is not None:
        number = entry.get("number")
        members = [t for t in tasks if t.get("round") == number]
        round_view = {
            "number": number,
            "branch": entry.get("branch"),
            "base": entry.get("base"),
            "pr_url": entry.get("pr_url"),
            "state": entry.get("state"),
            "approved_sha": entry.get("approved_sha"),
            "tasks": len(members),
            "task_counts": _counts(members),
        }

    payload = {
        "schema": schema_version(data),
        "legacy": bool(data.get("legacy")),
        "tasks_total": len(tasks),
        "status_counts": _counts(tasks),
        "policy": {
            i.get("key"): _abbrev(i.get("decision"))
            for i in policy_items(data)
            if not i.get("legacy")
        },
        "current_round": round_view,
        "ready": ready,
        "e2e_checklist_open": checklist_counts(path, tasks),
        "e2e_coverage": _coverage_digest(coverage_report(tasks, done_status)),
    }
    gate = gate_note(data)
    if gate:
        payload["gate"] = gate
    emit(payload)


def _coverage_digest(report):
    """--brief 는 목록이 아니라 수만 싣는다. 목록은 --coverage 가 낸다."""
    return {
        "declared": report["declared"],
        "required": report["required"],
        "uncovered_done": len(report["uncovered_done"]),
        "uncovered_open": len(report["uncovered_open"]),
        "malformed": len(report["malformed"]),
    }


def cmd_coverage(tasks, done_status):
    report = coverage_report(tasks, done_status)
    if report["declared"] == 0:
        note("e2e 필드를 가진 태스크가 없습니다 — 아직 아무것도 정하지 않은 상태입니다")
    elif report["malformed"]:
        note(f"형식 오류 {len(report['malformed'])}건 — covered_by 가 리스트가 아닙니다. "
             "덮였는지 판정할 수 없습니다")
    elif not report["uncovered_done"] and not report["uncovered_open"]:
        note(f"필요 {report['required']}건 모두 덮여 있습니다")
    else:
        note(f"덮이지 않음 — 완료된 것 {len(report['uncovered_done'])}건, "
             f"진행 중 {len(report['uncovered_open'])}건")
    emit(report)


def cmd_stats(raw, tasks):
    counts = {}
    for task in tasks:
        counts[str(task.get("status"))] = counts.get(str(task.get("status")), 0) + 1
    biggest = sorted(
        tasks, key=lambda t: len(yaml.safe_dump(t, allow_unicode=True)), reverse=True
    )[:5]
    emit(
        {
            "tasks": len(tasks),
            "status_counts": dict(sorted(counts.items(), key=lambda kv: -kv[1])),
            "file_chars": len(raw),
            "file_tokens_approx": approx_tokens(raw),
            "largest_tasks": [
                {
                    "id": t.get("id"),
                    "tokens_approx": approx_tokens(yaml.safe_dump(t, allow_unicode=True)),
                }
                for t in biggest
            ],
        }
    )


def cmd_index(tasks, args):
    fields = [f.strip() for f in args.fields.split(",")] if args.fields else DEFAULT_INDEX_FIELDS
    selected = tasks
    if args.status:
        wanted = set(args.status)
        selected = [t for t in selected if str(t.get("status")) in wanted]
    if args.exclude_status:
        unwanted = set(args.exclude_status)
        selected = [t for t in selected if str(t.get("status")) not in unwanted]
    if args.limit:
        selected = selected[: args.limit]
    # Add verification summary to each task
    output = []
    for t in selected:
        entry = slim(t, fields)
        # Add verification summary (same logic as render.py)
        entry["verification"] = verification_summary(t.get("verification", []))
        output.append(entry)
    note(f"{len(selected)}/{len(tasks)}건, 필드 {', '.join(fields)}")
    emit(output)


def cmd_ready(tasks, done_status):
    status_of = {t.get("id"): str(t.get("status")) for t in tasks}
    ready, waiting = [], []
    for task in tasks:
        if str(task.get("status")) == done_status:
            continue
        blockers = [
            f"{dep}({status_of.get(dep, '없음')})"
            for dep in task.get("depends_on", []) or []
            if status_of.get(dep) != done_status
        ]
        entry = slim(task, ["id", "title", "status"])
        # Add verification summary
        entry["verification"] = verification_summary(task.get("verification", []))
        if blockers:
            entry["blocked_by"] = blockers
            waiting.append(entry)
        else:
            ready.append(entry)
    note(f"준비됨 {len(ready)}건, 대기 중 {len(waiting)}건")
    emit({"ready": ready, "waiting": waiting})


def cmd_task(data, tasks, args):
    payload = []
    dropped = 0
    for task_id in args.task:
        task = dict(resolve(tasks, task_id))
        # Add verification_status for consumers to check validity
        verification = task.get("verification")
        if verification is None:
            task["verification"] = []
            task["verification_status"] = "none"
        elif not isinstance(verification, list):
            # Keep malformed value distinguishable, don't silently convert
            task["verification_status"] = "invalid"
        elif not verification:
            # Empty list
            task["verification_status"] = "none"
        else:
            # Non-empty list
            task["verification_status"] = "ok"
        if "round" in task:
            url = round_pr_url(data, task.get("round"))
            if url:
                task["pr_url_resolved"] = url
        if not args.with_deviations and task.get("deviations"):
            dropped += 1
            task["deviations"] = f"<{len(task['deviations'])}건 생략 — --with-deviations 로 조회>"
        payload.append(task)
    if dropped:
        note(f"{dropped}건의 deviations 를 생략했습니다 (--with-deviations 로 포함)")
    emit(payload)


def _closure(tasks, task_id, downward):
    edges = {}
    for task in tasks:
        for dep in task.get("depends_on", []) or []:
            if downward:
                edges.setdefault(dep, []).append(task["id"])
            else:
                edges.setdefault(task["id"], []).append(dep)
    seen, frontier, order = set(), [task_id], []
    while frontier:
        current = frontier.pop(0)
        for nxt in edges.get(current, []):
            if nxt not in seen:
                seen.add(nxt)
                order.append(nxt)
                frontier.append(nxt)
    return order


def cmd_chain(tasks, task_id, downward, exclude_status):
    resolve(tasks, task_id)
    by_id = {t.get("id"): t for t in tasks}
    chain = _closure(tasks, task_id, downward)
    unwanted = set(exclude_status or [])
    kept = [
        cid for cid in chain if cid in by_id and str(by_id[cid].get("status")) not in unwanted
    ]
    label = "dependents" if downward else "depends_on_closure"
    direction = "을 기다리는" if downward else "이 기다리는"
    hidden = len(chain) - len(kept) - len([c for c in chain if c not in by_id])
    suffix = f" ({hidden}건은 --exclude-status 로 숨김)" if hidden else ""
    note(f"{task_id} {direction} 태스크 {len(kept)}건{suffix}")
    # Add verification summary to each task
    result_list = []
    for cid in kept:
        entry = slim(by_id[cid], ["id", "title", "status", "depends_on"])
        entry["verification"] = verification_summary(by_id[cid].get("verification"))
        result_list.append(entry)
    emit(
        {
            "task": task_id,
            label: result_list,
            "unresolved": [cid for cid in chain if cid not in by_id],
        }
    )


def cmd_find(tasks, keyword):
    needle = keyword.lower()
    hits = []
    for task in tasks:
        where = []
        snippet = None
        for field in ("title", "description", "target_files", "deviations"):
            value = task.get(field)
            if value is None:
                continue
            text = value if isinstance(value, str) else yaml.safe_dump(value, allow_unicode=True)
            position = text.lower().find(needle)
            if position >= 0:
                where.append(field)
                if snippet is None and field != "title":
                    start = max(0, position - SNIPPET_RADIUS)
                    snippet = text[start : position + SNIPPET_RADIUS].replace("\n", " ").strip()
        if where:
            hit = slim(task, ["id", "title", "status"])
            hit["verification"] = verification_summary(task.get("verification"))
            hit["matched_in"] = where
            if snippet:
                hit["snippet"] = snippet
            hits.append(hit)
    note(f'"{keyword}" 일치 {len(hits)}건')
    emit(hits)


def main():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument("path", nargs="?", default=DEFAULT_PATH)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--stats", action="store_true", help="건수·상태 집계·파일 무게")
    mode.add_argument("--index", action="store_true", help="색인 필드만")
    mode.add_argument("--ready", action="store_true", help="착수 가능/의존 대기")
    mode.add_argument("--task", nargs="+", metavar="ID", help="태스크 전체 내용")
    mode.add_argument("--deps", metavar="ID", help="그 태스크가 기다리는 것들")
    mode.add_argument("--dependents", metavar="ID", help="그 태스크를 기다리는 것들")
    mode.add_argument("--find", metavar="KEYWORD", help="제목·본문 검색")
    mode.add_argument("--policy", action="store_true", help="project_policy (기본 현행만)")
    mode.add_argument("--rounds", action="store_true", help="회차 전체")
    mode.add_argument("--pr", action="store_true", help="지금 열려 있는 회차 하나")
    mode.add_argument("--brief", action="store_true", help="세션 시작용 최소 컨텍스트 한 덩어리")
    mode.add_argument("--coverage", action="store_true",
                      help="E2E 가 필요하다고 적혔는데 덮이지 않은 태스크")
    mode.add_argument("--key", metavar="NAME", help="phases 를 뺀 최상위 키 하나 (예: rounds)")
    parser.add_argument("--status", action="append", help="--index 에서 이 상태만 (반복 가능)")
    parser.add_argument("--exclude-status", action="append", help="--index/--deps/--dependents 에서 이 상태 제외")
    parser.add_argument("--fields", help="--index 필드 목록 (쉼표 구분)")
    parser.add_argument("--done-status", default="done", help="완료로 볼 상태 (기본 done)")
    parser.add_argument("--with-deviations", action="store_true", help="--task 에 deviations 포함")
    parser.add_argument("--limit", type=int, help="--index 결과 개수 제한")
    parser.add_argument("--all", action="store_true", help="--policy 에 폐기(legacy) 항목까지 포함")
    parser.add_argument("--policy-key", metavar="KEY", help="--policy 에서 이 key 항목만")
    args = parser.parse_args()

    raw, data, tasks = load(Path(args.path))

    if args.stats:
        cmd_stats(raw, tasks)
    elif args.key:
        if args.key not in data:
            available = ", ".join(k for k in data if k != "phases")
            print(f"[dag-query] Error: 최상위 키 {args.key} 가 없습니다. 있는 키: {available}")
            sys.exit(1)
        emit(data[args.key])
    elif args.policy:
        cmd_policy(data, args)
    elif args.rounds:
        cmd_rounds(data)
    elif args.pr:
        cmd_pr(data, tasks)
    elif args.brief:
        cmd_brief(Path(args.path), data, tasks, args.done_status)
    elif args.coverage:
        cmd_coverage(tasks, args.done_status)
    elif args.index:
        cmd_index(tasks, args)
    elif args.ready:
        cmd_ready(tasks, args.done_status)
    elif args.task:
        cmd_task(data, tasks, args)
    elif args.deps:
        cmd_chain(tasks, args.deps, False, args.exclude_status)
    elif args.dependents:
        cmd_chain(tasks, args.dependents, True, args.exclude_status)
    elif args.find:
        cmd_find(tasks, args.find)


if __name__ == "__main__":
    main()
