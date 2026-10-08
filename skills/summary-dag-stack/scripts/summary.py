#!/usr/bin/env python3
"""Summarize a DAG, optionally with reviewed project context, as text or YAML."""

import argparse
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml


def load_mapping(path):
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"YAML 매핑이 아닙니다: {path}")
    return data


def validate_context(context, path, as_of):
    for key in ("project", "goal", "next_release"):
        if key in context and (not isinstance(context[key], str) or not context[key].strip()):
            raise ValueError(f"context.{key}는 비어 있지 않은 문자열이어야 합니다")
    for key in ("current_flows", "evidence"):
        if key in context and (not isinstance(context[key], list) or
                               any(not isinstance(item, str) or not item.strip()
                                   for item in context[key])):
            raise ValueError(f"context.{key}는 문자열 목록이어야 합니다")
    blockers = context.get("blockers", [])
    if not isinstance(blockers, list) or any(
            not isinstance(item, dict) or
            any(not isinstance(item.get(key), str) or not item[key].strip()
                for key in ("reason", "clears_when")) for item in blockers):
        raise ValueError("context.blockers는 reason과 clears_when이 있는 객체 목록이어야 합니다")
    claims = any(context.get(key) for key in ("goal", "current_flows", "next_release", "blockers",
                                              "next_actions", "user_approval", "discussion"))
    if not claims:
        return
    raw_date = context.get("checked_at")
    try:
        if isinstance(raw_date, datetime):
            raise ValueError
        checked_at = raw_date if isinstance(raw_date, date) else date.fromisoformat(raw_date)
    except (TypeError, ValueError):
        raise ValueError("context.checked_at은 YYYY-MM-DD 날짜여야 합니다") from None
    if not checked_at <= as_of or as_of - checked_at > timedelta(days=7):
        raise ValueError("context.checked_at이 미래이거나 7일 넘게 오래됐습니다")
    evidence = context.get("evidence")
    if not evidence:
        raise ValueError("사업 맥락이 있으면 context.evidence가 필요합니다")
    for entry in evidence:
        source = Path(entry)
        source = source if source.is_absolute() else path.parent / source
        if not source.is_file():
            raise ValueError(f"context.evidence 파일이 없습니다: {entry}")


def summarize(tasks, done_status):
    status_of = {task.get("id"): str(task.get("status")) for task in tasks}
    open_tasks = [task for task in tasks if str(task.get("status")) != done_status]
    counts = {}
    for task in tasks:
        status = str(task.get("status"))
        counts[status] = counts.get(status, 0) + 1

    ready, waiting = [], 0
    for task in open_tasks:
        blockers = [dep for dep in task.get("depends_on", []) or []
                    if status_of.get(dep) != done_status]
        if blockers:
            waiting += 1
        else:
            ready.append({key: task[key] for key in ("id", "title", "status") if key in task})

    open_ids = {task.get("id") for task in open_tasks}
    holds = {}
    for task in open_tasks:
        for dep in task.get("depends_on", []) or []:
            if dep in open_ids:
                holds[dep] = holds.get(dep, 0) + 1
    by_id = {task.get("id"): task for task in tasks}
    chokepoints = []
    for task_id, count in sorted(holds.items(), key=lambda item: (-item[1], item[0]))[:8]:
        task = by_id[task_id]
        item = {key: task[key] for key in ("id", "title", "status") if key in task}
        item["blocks_directly"] = count
        chokepoints.append(item)
    ordered_counts = dict(sorted(counts.items(), key=lambda item: -item[1]))
    return {"tasks": len(tasks), "status_counts": ordered_counts, "open": len(open_tasks),
            "ready_count": len(ready), "waiting_count": waiting,
            "ready": ready, "chokepoints": chokepoints}


def coverage(tasks, done_status):
    declared = required = uncovered_done = uncovered_open = malformed = 0
    for task in tasks:
        e2e = task.get("e2e")
        if not isinstance(e2e, dict):
            continue
        declared += 1
        covered = e2e.get("covered_by")
        if covered is not None and not isinstance(covered, list):
            malformed += 1
            continue
        if e2e.get("required"):
            required += 1
            if not covered:
                if task.get("status") == done_status:
                    uncovered_done += 1
                else:
                    uncovered_open += 1
    return declared, required, uncovered_done, uncovered_open, malformed


def value(context, key):
    item = context.get(key)
    return item.strip() if isinstance(item, str) and item.strip() else "확인 필요"


def joined(context, key):
    items = context.get(key)
    if not isinstance(items, list):
        return "확인 필요"
    texts = [item.strip() for item in items if isinstance(item, str) and item.strip()]
    return "; ".join(texts) if texts else "확인 필요"


def render_text(path, tasks, summary, context, done_status):
    title = value(context, "project")
    if title == "확인 필요":
        title = path.parent.name
    raw_date = context.get("checked_at")
    checked_at = raw_date.isoformat() if isinstance(raw_date, date) else value(context, "checked_at")
    heading = (f"{title} — {checked_at} 확인" if checked_at != "확인 필요"
               else f"{title} — 확인 시각 미기재")
    lines = [heading, f"목표: {value(context, 'goal')}",
             f"현재 사용 가능한 흐름: {joined(context, 'current_flows')}",
             f"다음 공개 기준: {value(context, 'next_release')}"]
    blockers = context.get("blockers")
    if isinstance(blockers, list) and blockers:
        for item in blockers:
            if isinstance(item, dict):
                lines.append(f"막힌 이유: {value(item, 'reason')}")
                lines.append(f"해제 조건: {value(item, 'clears_when')}")
    else:
        lines.extend(("막힌 이유: 확인 필요", "해제 조건: 확인 필요"))
    counts = ", ".join(f"{status} {count}" for status, count in summary["status_counts"].items())
    lines.append(f"원장: 전체 {summary['tasks']}건; {counts}; 완료 기준 {done_status}")
    declared, required, uncovered_done, uncovered_open, malformed = coverage(tasks, done_status)
    if declared:
        e2e_line = (f"E2E: 판정 {declared}건, 필수 {required}건, 완료 미충족 {uncovered_done}건, "
                    f"열린 미충족 {uncovered_open}건")
        if malformed:
            e2e_line += f", 형식 오류 {malformed}건"
        lines.append(e2e_line)
    else:
        lines.append("E2E: 판정 미기재")
    if summary["chokepoints"]:
        points = ", ".join(f"{item['id']}({item.get('status', '상태 없음')}, 후속 {item['blocks_directly']}건)"
                           for item in summary["chokepoints"][:3])
        lines.append(f"의존성 길목: {points}")
    else:
        lines.append("의존성 길목: 없음")
    lines.append("상태 해석: committed는 구현 커밋이며, 의존성 충족은 작업 승인·검증·공개 판정이 아닙니다.")
    lines.append(f"근거: {joined(context, 'evidence')}")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="DAG 집계와 검토된 맥락으로 프로젝트 현황을 출력")
    parser.add_argument("dag_path", type=Path)
    parser.add_argument("--context", type=Path, help="검토된 프로젝트 설명 YAML")
    parser.add_argument("--done-status", default="done")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today(),
                        help="맥락 확인 시각의 기준일 (YYYY-MM-DD, 기본 오늘)")
    parser.add_argument("--yaml", action="store_true", help="기존 --summary 필드의 기계 판독 출력")
    args = parser.parse_args()
    try:
        dag = load_mapping(args.dag_path)
        context = load_mapping(args.context) if args.context else {}
        if args.context:
            validate_context(context, args.context, args.as_of)
        tasks = [task for phase in dag.get("phases", []) or []
                 for task in phase.get("tasks", []) or []]
        summary = summarize(tasks, args.done_status)
        if args.yaml:
            print(yaml.safe_dump(summary, allow_unicode=True, sort_keys=False, width=100).rstrip())
        else:
            print(render_text(args.dag_path, tasks, summary, context, args.done_status))
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.exit(1, f"[dag-summary] {error}\n")


if __name__ == "__main__":
    main()
