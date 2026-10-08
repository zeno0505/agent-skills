#!/usr/bin/env python3
"""Render a validated development portfolio from the active HQ project registry."""

import argparse
from datetime import date
from pathlib import Path

import yaml

from summary import load_mapping, summarize, validate_context


def required_text(mapping, key, location):
    value = mapping.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{location}.{key}는 비어 있지 않은 문자열이어야 합니다")
    return value.strip()


def required_list(mapping, key, location):
    value = mapping.get(key)
    if not isinstance(value, list) or not value or any(
            not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"{location}.{key}는 비어 있지 않은 문자열 목록이어야 합니다")
    return [item.strip() for item in value]


def approval_or_discussion(context, key, states):
    value = context.get(key)
    if not isinstance(value, dict) or value.get("state") not in states:
        raise ValueError(f"context.{key}.state는 {', '.join(states)} 중 하나여야 합니다")
    if key == "user_approval" or value["state"] != "none":
        required_text(value, "reason" if key == "user_approval" else "topic", f"context.{key}")
    return value


def open_decisions(root):
    directory = root / "inbox" / "open"
    if not directory.is_dir():
        raise ValueError(f"열린 안건 디렉터리가 없습니다: {directory}")
    decisions = []
    for path in sorted(directory.glob("*.md")):
        parts = path.read_text(encoding="utf-8").split("---", 2)
        if len(parts) != 3 or parts[0].strip():
            raise ValueError(f"열린 안건의 YAML 머리말이 없습니다: {path}")
        item = yaml.safe_load(parts[1])
        if not isinstance(item, dict):
            raise ValueError(f"열린 안건의 YAML 머리말이 잘못됐습니다: {path}")
        if item.get("kind") == "decision" and item.get("severity") == "blocking" and not item.get("decision"):
            required_text(item, "id", str(path))
            required_text(item, "title", str(path))
            decisions.append(item)
    return decisions


def collect(root, as_of):
    registry = load_mapping(root / "company" / "policies" / "hq-sweep.yaml")
    manifest = load_mapping(root / "company" / "development-status.yaml")
    if manifest.get("schema") != 1:
        raise ValueError("development-status.yaml의 schema는 1이어야 합니다")
    registered = registry.get("projects")
    paths = manifest.get("projects")
    if not isinstance(registered, list) or not isinstance(paths, dict):
        raise ValueError("프로젝트 등록 목록 또는 상태 맥락 목록이 잘못됐습니다")
    development = [item for item in registered if isinstance(item, dict) and item.get("id") != "hq"]
    ids = [required_text(item, "id", "hq-sweep.projects") for item in development]
    if len(ids) != len(set(ids)) or set(paths) != set(ids):
        raise ValueError("활성 개발 프로젝트와 development-status.yaml의 프로젝트 목록이 다릅니다")

    projects = []
    for item in development:
        project_id = item["id"]
        relative = paths[project_id]
        if not isinstance(relative, str) or not relative.strip():
            raise ValueError(f"{project_id}의 context 경로가 없습니다")
        context_path = root / relative
        context = load_mapping(context_path)
        required_text(context, "project", f"{project_id} context")
        validate_context(context, context_path, as_of)
        actions = required_list(context, "next_actions", f"{project_id} context")
        approval = approval_or_discussion(context, "user_approval", ("none", "now"))
        discussion = approval_or_discussion(context, "discussion", ("none", "optional", "needed"))
        dag_path = item.get("dag_path")
        if dag_path is None:
            dag_summary = None
        else:
            if not isinstance(dag_path, str) or not dag_path.strip():
                raise ValueError(f"{project_id}의 활성 DAG 경로가 잘못됐습니다")
            dag = load_mapping(root / dag_path)
            phases = dag.get("phases")
            if not isinstance(phases, list):
                raise ValueError(f"{project_id}의 DAG phases가 잘못됐습니다")
            tasks = [task for phase in phases for task in phase.get("tasks", [])]
            dag_summary = summarize(tasks, "done")
        projects.append((project_id, context, actions, approval, discussion, dag_summary))

    separate = manifest.get("separate_approvals", [])
    if not isinstance(separate, list):
        raise ValueError("separate_approvals는 목록이어야 합니다")
    for item in separate:
        if not isinstance(item, dict) or not isinstance(item.get("blocks_development"), bool):
            raise ValueError("별도 실행 전 승인 항목의 형식이 잘못됐습니다")
        required_text(item, "id", "separate_approvals")
        required_text(item, "action", "separate_approvals")
        required_list(item, "needs", "separate_approvals")
        evidence = root / required_text(item, "evidence", "separate_approvals")
        if not evidence.is_file():
            raise ValueError(f"별도 승인 근거 파일이 없습니다: {evidence}")
    return projects, open_decisions(root), separate


def render(projects, decisions, separate, as_of):
    explicit = [(project_id, context) for project_id, context, _, approval, _, _ in projects
                if approval["state"] == "now"]
    decision_ids = {item["id"] for item in decisions}
    for project_id, context in explicit:
        approval_id = context["user_approval"].get("inbox_id")
        if approval_id and approval_id not in decision_ids:
            raise ValueError(f"{project_id}의 승인 안건 {approval_id}가 열린 inbox에 없습니다")
    standalone = [pair for pair in explicit if pair[1]["user_approval"].get("inbox_id") not in decision_ids]
    approval_count = len(decisions) + len(standalone)
    lines = [f"개발 프로젝트 현황 — {as_of.isoformat()}", f"지금 필요한 사장 승인: {approval_count}건"]
    for item in decisions:
        lines.append(f"- {item['id']} {item['title']} (열린 blocking 결정)")
    for project_id, context in standalone:
        lines.append(f"- {context['project']} — {context['user_approval']['reason']}")
    lines.append("")
    for project_id, context, actions, approval, discussion, dag in projects:
        lines.append(f"[{context['project']}] ({project_id})")
        lines.append(f"목표: {context.get('goal') or '확인 필요'}")
        lines.append(f"현재 흐름: {'; '.join(context.get('current_flows') or []) or '확인 필요'}")
        lines.append(f"다음 공개 기준: {context.get('next_release') or '확인 필요'}")
        if dag is None:
            lines.append("DAG 없음")
        else:
            counts = ", ".join(f"{key} {value}" for key, value in dag["status_counts"].items())
            lines.append(f"DAG: 전체 {dag['tasks']}건; {counts}; 완료 기준 done")
        for action in actions:
            lines.append(f"다음 작업: {action}")
        if context.get("blockers"):
            for blocker in context["blockers"]:
                lines.append(f"막힌 이유: {blocker['reason']}")
                lines.append(f"해제 조건: {blocker['clears_when']}")
        else:
            lines.extend(("막힌 이유: 없음", "해제 조건: 해당 없음"))
        matching = [item for item in decisions if item.get("product") in (project_id, context.get("product"))]
        if matching:
            lines.append("사장 승인: 필요 — " + "; ".join(f"{item['id']} {item['title']}" for item in matching))
        elif approval["state"] == "now":
            lines.append(f"사장 승인: 필요 — {approval['reason']}")
        else:
            lines.append(f"사장 승인: 불필요 — {approval['reason']}")
        if discussion["state"] == "none":
            lines.append("논의: 없음")
        else:
            label = "선택" if discussion["state"] == "optional" else "필요"
            lines.append(f"논의: {label} — {discussion['topic']}")
        lines.append("")
    for item in separate:
        gate = "개발 선행" if item["blocks_development"] else "개발 비차단"
        lines.append(f"별도 실행 전 승인: {item['id']} {item['action']} ({gate})")
        lines.append(f"필요한 결정값: {', '.join(item['needs'])}")
    lines.append("해석: committed는 구현 커밋이며, DAG의 done은 공개 또는 운영 사용을 뜻하지 않습니다.")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="본사 개발 프로젝트와 승인·논의 현황을 출력")
    parser.add_argument("root", type=Path, help="본사 저장소 경로")
    parser.add_argument("--as-of", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    try:
        print(render(*collect(args.root, args.as_of), args.as_of))
    except (OSError, ValueError, yaml.YAMLError) as error:
        parser.exit(1, f"[development-status] {error}\n")


if __name__ == "__main__":
    main()
