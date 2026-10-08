#!/usr/bin/env python3
"""
render.py — dag.yaml 을 mermaid 그래프가 담긴 dag.md 로 변환한다.

Usage: python render.py <dag_yaml_path> [--full] [--max-nodes N]
  dag_yaml_path : dag.yaml 경로. dag.md 는 같은 디렉터리에 쓴다.
  --full        : 노드 축약을 끄고 모든 태스크를 그린다.
  --max-nodes N : 그래프 노드 상한 (기본 60). 넘으면 큰 상태 그룹부터 접는다.

이 스크립트는 상태(status) 값을 알지 못한다. dag.yaml 에 등장한 문자열을 그대로
받아 색만 배정하므로, 상태 체계가 바뀌어도 스크립트를 고칠 일이 없다.
스키마 문제는 실행을 끊지 않고 경고로 남긴다 — 렌더는 검증 게이트가 아니라 관측 도구다.
"""

import colorsys
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path

try:
    import yaml
except ImportError:
    print("[dag-render] Error: PyYAML 이 필요합니다. 실행: pip install pyyaml")
    sys.exit(1)

DEFAULT_MAX_NODES = 60

# 상태 이름이 아니라 팔레트만 정의한다. 배정은 실행 시점에 이름 해시로 결정한다.
# 색상환을 균등 분할해 만들므로 어떤 두 색도 최소 30도 벌어진다 — 손으로 고른 목록과 달리
# 비슷한 파랑 둘이 나란히 뽑히는 일이 없다.
PALETTE_HUE_COUNT = 12
NEUTRAL_FILLS = ["#64748b", "#78716c"]


def _hsl_hex(hue_deg: float, saturation: float, lightness: float) -> str:
    red, green, blue = colorsys.hls_to_rgb(hue_deg / 360.0, lightness, saturation)
    return "#{:02x}{:02x}{:02x}".format(round(red * 255), round(green * 255), round(blue * 255))


def _text_on(fill_hex: str) -> str:
    """배경 밝기에 따라 글자색을 고른다. 노랑·라임 위의 흰 글자를 막는다."""
    red, green, blue = (int(fill_hex[i : i + 2], 16) / 255 for i in (1, 3, 5))
    luminance = 0.2126 * red + 0.7152 * green + 0.0722 * blue
    return "#1f2937" if luminance > 0.55 else "#ffffff"


def _build_palette():
    """색상은 150도씩 건너뛰며 채우고 밝기는 한 칸씩 번갈아 준다.
    해시가 어느 두 칸을 뽑든 색상 차이나 밝기 차이 중 하나는 크게 벌어진다."""
    fills = []
    for index in range(PALETTE_HUE_COUNT):
        lightness = 0.45 if index % 2 == 0 else 0.63
        fills.append(_hsl_hex((index * 150) % 360, 0.68, lightness))
    fills.extend(NEUTRAL_FILLS)
    return [(fill, _text_on(fill)) for fill in fills]


PALETTE = _build_palette()

MISSING_STATUS = "(상태 없음)"


def stable_hash(value: str) -> int:
    """실행마다 같은 값을 주는 해시. 파이썬 hash() 는 프로세스마다 달라 쓸 수 없다."""
    return int(hashlib.md5(value.encode("utf-8")).hexdigest()[:8], 16)


def assign_colors(statuses):
    """상태 이름 → 팔레트 색. 이름만으로 정해지므로 상태가 늘어도 기존 색이 안 변한다."""
    taken = {}
    for status in sorted(statuses):
        slot = stable_hash(status) % len(PALETTE)
        if len(taken) < len(PALETTE):
            while slot in taken.values():
                slot = (slot + 1) % len(PALETTE)
        taken[status] = slot
    return {status: PALETTE[slot] for status, slot in taken.items()}


def sanitize(value: str) -> str:
    """mermaid 식별자로 쓸 수 있게 정리한다.

    한글처럼 통째로 지워지는 글자가 있으면 해시를 덧붙인다 — 서로 다른 상태명이
    같은 식별자로 뭉개져 색이 뒤섞이는 것을 막는다. 하이픈·공백처럼 지워도
    구분이 남는 문자는 그대로 떼어내 T-001 → T001 의 읽기 쉬운 형태를 지킨다.
    """
    cleaned = re.sub(r"[^0-9A-Za-z_]", "", value)
    without_separators = re.sub(r"[-.:/\s]", "", value)
    if not cleaned or cleaned != without_separators:
        cleaned = f"{cleaned}x{stable_hash(value) % 1000000}"
    if not cleaned[0].isalpha():
        cleaned = "n" + cleaned
    return cleaned


def class_name(status: str) -> str:
    return "st_" + sanitize(status)


def escape_label(value: str) -> str:
    """mermaid 인용 라벨을 끊는 문자를 막는다."""
    return str(value).replace('"', "#quot;")


def escape_cell(value: str) -> str:
    return str(value).replace("|", "\\|")


def find_vault_root(start: Path):
    """start 에서 위로 올라가며 .obsidian 디렉터리를 가진 지점을 볼트 루트로 본다.

    `scripts/wikilink_resolve.py` 의 동명 함수와 같은 방식이다. 여기서 다시 구현하는
    이유는 그 함수를 쓰려면 먼저 그 파일이 있는 볼트 루트를 알아야 하는 순환
    때문이다 — 이 탐색 자체는 해소 규칙이 아니라 경로 찾기라 중복이 아니다.
    """
    for candidate in [start, *start.parents]:
        if (candidate / ".obsidian").is_dir():
            return candidate
    return None


def resolve_wikilinks(dag_path: Path):
    """dag.yaml 위치를 기준으로 볼트의 wikilink_resolve 를 빌려 태스크 id -> 링크 경로를 얻는다.

    볼트를 찾지 못하거나(예: 볼트 밖 저장소의 dag.yaml) import 에 실패하면 빈 dict 를
    낸다 — dag.md 생성은 wikilink 해소와 무관하게 항상 성공해야 하므로 여기서 예외를
    올리지 않는다. 해소 규칙 자체(우선순위, 실패 판정)는 다시 구현하지 않고
    `scripts/wikilink_resolve.py` 를 그대로 가져다 쓴다.
    """
    project_dir = dag_path.parent.resolve()
    vault_root = find_vault_root(project_dir)
    if vault_root is None:
        print("[dag-render] 볼트(.obsidian)를 찾지 못해 태스크 id 를 평문으로 렌더합니다.")
        return {}

    vault_root_str = str(vault_root)
    inserted = vault_root_str not in sys.path
    if inserted:
        sys.path.insert(0, vault_root_str)
    try:
        from scripts.wikilink_resolve import STATUS_RESOLVED, resolve_ids
    except ImportError as exc:
        print(f"[dag-render] wikilink_resolve import 실패로 태스크 id 를 평문으로 렌더합니다: {exc}")
        return {}
    finally:
        if inserted and vault_root_str in sys.path:
            sys.path.remove(vault_root_str)

    try:
        results = resolve_ids(project_dir, vault_root)
    except Exception as exc:  # noqa: BLE001 — 렌더는 절대 실패하면 안 된다
        print(f"[dag-render] wikilink 해소 중 오류로 태스크 id 를 평문으로 렌더합니다: {exc}")
        return {}

    return {r["id"]: r["path"] for r in results if r["status"] == STATUS_RESOLVED}


def format_task_ref(task_id: str, links: dict) -> str:
    """id 를 표에 넣을 문자열로 만든다. 해소됐으면 별칭 wikilink, 아니면 평문 그대로."""
    path = links.get(task_id)
    if path is None:
        return task_id
    return f"[[{path}|{task_id}]]"


def collect(data: dict):
    """phases → (tasks, warnings). 결함은 경고로 남기고 그릴 수 있는 만큼 살린다."""
    warnings = []
    tasks = []

    phases = data.get("phases")
    if not isinstance(phases, list):
        warnings.append("최상위 'phases' 키가 없거나 리스트가 아닙니다. 그래프를 그릴 수 없습니다.")
        return tasks, warnings

    for phase_index, phase in enumerate(phases):
        phase_name = str(phase.get("name") or f"phase{phase_index}")
        for task in phase.get("tasks", []) or []:
            task_id = task.get("id")
            if not task_id:
                warnings.append(f'phase "{phase_name}" 에 id 없는 태스크가 있어 건너뜁니다.')
                continue
            status = task.get("status")
            if not status:
                warnings.append(f'태스크 "{task_id}" 에 status 가 없습니다.')
                status = MISSING_STATUS
            if "title" not in task:
                warnings.append(f'태스크 "{task_id}" 에 title 이 없습니다.')
            if "target_files" not in task:
                warnings.append(f'태스크 "{task_id}" 에 target_files 가 없습니다.')
            depends_on = task.get("depends_on")
            if depends_on is None:
                warnings.append(f'태스크 "{task_id}" 에 depends_on 이 없습니다.')
                depends_on = []
            tasks.append(
                {
                    "phase": phase_name,
                    "id": str(task_id),
                    "title": str(task.get("title", "")),
                    "status": str(status),
                    "depends_on": [str(d) for d in depends_on],
                    "target_files": [str(f) for f in (task.get("target_files") or [])],
                    "round": task.get("round"),
                    "e2e": task.get("e2e"),
                }
            )

    known_ids = {t["id"] for t in tasks}
    for task in tasks:
        for dep in task["depends_on"]:
            if dep not in known_ids:
                warnings.append(f'태스크 "{task["id"]}" 의 depends_on 이 모르는 id 를 가리킵니다: "{dep}"')
    return tasks, warnings


def pick_collapsed(tasks, max_nodes, full):
    """노드가 상한을 넘으면 '큰 상태 그룹부터' 접는다. 상태 이름은 보지 않는다."""
    if full or len(tasks) <= max_nodes:
        return set()

    counts = Counter(t["status"] for t in tasks)
    collapsed = set()
    visible = len(tasks)
    for status, size in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if visible <= max_nodes:
            break
        if size < 2:
            continue
        collapsed.add(status)
        visible -= size - 1
    return collapsed


def render_graph(tasks, colors, collapsed):
    group_node = {status: "GRP_" + sanitize(status) for status in collapsed}
    node_of = {
        t["id"]: (group_node[t["status"]] if t["status"] in collapsed else sanitize(t["id"]))
        for t in tasks
    }

    lines = ["flowchart TD"]
    for phase_name in dict.fromkeys(t["phase"] for t in tasks):
        visible = [t for t in tasks if t["phase"] == phase_name and t["status"] not in collapsed]
        if not visible:
            continue
        lines.append(f'  subgraph {sanitize(phase_name)}["{escape_label(phase_name)}"]')
        for task in visible:
            label = escape_label(f'{task["id"]}<br/>{task["title"]}<br/>{task["status"]}')
            lines.append(f'    {node_of[task["id"]]}["{label}"]')
        lines.append("  end")
        lines.append("")

    counts = Counter(t["status"] for t in tasks)
    for status in sorted(collapsed):
        label = escape_label(f"{status} ×{counts[status]}<br/>(접힘)")
        lines.append(f'  {group_node[status]}["{label}"]')
    if collapsed:
        lines.append("")

    known_ids = {t["id"] for t in tasks}
    edges = []
    seen = set()
    for task in tasks:
        for dep in task["depends_on"]:
            if dep not in known_ids:
                continue
            src, dst = node_of[dep], node_of[task["id"]]
            if src == dst or (src, dst) in seen:
                continue
            seen.add((src, dst))
            edges.append(f"  {src} --> {dst}")
    lines.extend(edges)
    lines.append("")

    lines.extend(class_defs(counts, colors))
    for task in tasks:
        if task["status"] not in collapsed:
            lines.append(f'  class {node_of[task["id"]]} {class_name(task["status"])}')
    for status in sorted(collapsed):
        lines.append(f"  class {group_node[status]} {class_name(status)}")
    return "\n".join(lines)


def class_defs(counts, colors):
    lines = []
    for status in sorted(counts):
        fill, text = colors[status]
        lines.append(f"  classDef {class_name(status)} fill:{fill},color:{text}")
    lines.append("")
    return lines


def render_legend(tasks, colors):
    """색에 관습적 의미가 없으므로 범례가 그래프의 자기 설명을 맡는다."""
    counts = Counter(t["status"] for t in tasks)
    lines = ["flowchart LR"]
    for status in sorted(counts):
        node = "LG_" + sanitize(status)
        lines.append(f'  {node}["{escape_label(f"{status} ({counts[status]})")}"]')
    lines.append("")
    lines.extend(class_defs(counts, colors))
    for status in sorted(counts):
        lines.append(f"  class LG_{sanitize(status)} {class_name(status)}")
    return "\n".join(lines)


def e2e_cell(spec) -> str:
    """태스크의 E2E 상태를 한 칸으로 줄인다.

    렌더는 검증 게이트가 아니라 관측 도구다. 그래서 여기서 판정하지 않고 보이기만 한다 —
    「없음」과 「필요한데 안 덮임」을 눈으로 가르는 것이 목적이고, 세는 것은 query.py 의
    `--coverage` 가 한다.

    필드가 없으면 `—` 다. 「대상 아님」이 아니라 「아직 정하지 않음」이므로 빈 칸으로 두어
    정해진 것과 구별한다.
    """
    if not isinstance(spec, dict):
        return "—"
    covered = spec.get("covered_by")
    # 리스트가 아닌 값을 그대로 이으면 문자열이 한 글자씩 쪼개져 표에 쏟아진다. 판정도 못 하고
    # 표도 망가지므로 형식 오류로 낸다 — query.py 의 `--coverage` 가 같은 술어를 쓴다.
    if covered is not None and not isinstance(covered, list):
        return "**형식오류**"
    if not spec.get("required"):
        return "불필요"
    if covered:
        return escape_cell(", ".join(str(c) for c in covered))
    return "**미충족**"


def render_table(tasks, links=None):
    """태스크 표. `links` 에 있는 id 는 별칭 wikilink 로, 없으면 평문으로 낸다.

    mermaid 그래프(render_graph/render_legend)는 이 함수와 무관하다 — 옵시디언이
    mermaid 노드 라벨 안의 `[[...]]` 를 해석하지 않고 별칭 구분자 `|` 가 mermaid
    문법과 충돌하므로 그래프는 항상 평문 id 로 남긴다.
    """
    links = links or {}
    rows = [
        "| ID | Title | Status | Round | E2E | Depends On | Target Files |",
        "|----|-------|--------|-------|-----|------------|--------------|",
    ]
    for task in tasks:
        id_cell = escape_cell(format_task_ref(task["id"], links))
        deps = (
            ", ".join(escape_cell(format_task_ref(d, links)) for d in task["depends_on"]) or "—"
        )
        files = ", ".join(escape_cell(f) for f in task["target_files"]) or "—"
        rnd = "—" if task.get("round") is None else escape_cell(str(task["round"]))
        rows.append(
            f'| {id_cell} | {escape_cell(task["title"])} '
            f'| {escape_cell(task["status"])} | {rnd} | {e2e_cell(task.get("e2e"))} '
            f'| {deps} | {files} |'
        )
    return "\n".join(rows)


def render_rounds(data, tasks):
    """회차 표. 회차는 PR 하나에 대응하므로 리뷰 상태를 여기서 읽는다."""
    entries = data.get("rounds")
    if not isinstance(entries, list) or not entries:
        return None
    per_round = Counter(t.get("round") for t in tasks)
    rows = [
        "| 회차 | 브랜치 | Base | 상태 | 태스크 | PR |",
        "|------|--------|------|------|--------|-----|",
    ]
    for entry in entries:
        number = entry.get("number")
        url = entry.get("pr_url")
        link = f"[#{str(url).rstrip('/').rsplit('/', 1)[-1]}]({url})" if url else "—"
        rows.append(
            f'| {escape_cell(str(number))} | {escape_cell(str(entry.get("branch") or "—"))} '
            f'| {escape_cell(str(entry.get("base") or "—"))} '
            f'| {escape_cell(str(entry.get("state") or "—"))} '
            f'| {per_round.get(number, 0)} | {link} |'
        )
    return "\n".join(rows)


def render_policy(data):
    """현행 정책만 요약한다 — 폐기된 것은 dag.yaml 에 남아 있고 query.py --policy --all 로 본다."""
    raw_policy = data.get("project_policy")
    if isinstance(raw_policy, list):
        items = [i for i in raw_policy if isinstance(i, dict) and not i.get("legacy")]
        retired = len(raw_policy) - len(items)
    elif isinstance(raw_policy, dict):
        items = [{"key": k, "decision": v} for k, v in raw_policy.items()]
        retired = 0
    else:
        return None
    if not items:
        return None
    rows = ["| 정책 | 결정 | 정한 날 |", "|------|------|---------|"]
    for item in items:
        decision = str(item.get("decision"))
        if len(decision) > 160:
            decision = decision[:160].replace("\n", " ").rstrip() + " …"
        rows.append(
            f'| {escape_cell(str(item.get("key")))} | {escape_cell(decision)} '
            f'| {escape_cell(str(item.get("decided_at") or "—"))} |'
        )
    table = "\n".join(rows)
    if retired:
        table += f"\n\n_폐기 {retired}건은 생략했습니다 — `query.py --policy --all`._"
    return table


def render_dag_md(tasks, warnings, colors, collapsed, data=None, links=None):
    data = data or {}
    parts = [
        "> [!NOTE] 자동 생성 파일 — dag.yaml 을 수정한 뒤 show-dag-stack 스킬로 다시 생성하세요.\n"
    ]

    if warnings:
        parts.append(f"## ⚠️ 경고 {len(warnings)}건\n")
        parts.append("\n".join(f"- {w}" for w in warnings) + "\n")

    rounds_table = render_rounds(data, tasks)
    if rounds_table:
        parts.append("## 회차\n")
        parts.append(rounds_table + "\n")

    policy_table = render_policy(data)
    if policy_table:
        parts.append("## 현행 정책\n")
        parts.append(policy_table + "\n")

    if not tasks:
        parts.append("## Task Graph\n\n_그릴 태스크가 없습니다._\n")
        return "\n".join(parts)

    parts.append("## 상태 범례\n")
    parts.append(f"```mermaid\n{render_legend(tasks, colors)}\n```\n")

    parts.append("## Task Graph\n")
    if collapsed:
        names = ", ".join(f"`{s}`" for s in sorted(collapsed))
        parts.append(
            f"_노드가 많아 {names} 상태를 그룹 노드로 접었습니다. "
            "전체를 보려면 `--full` 로 다시 생성하세요._\n"
        )
    parts.append(f"```mermaid\n{render_graph(tasks, colors, collapsed)}\n```\n")

    parts.append("## Task List\n")
    parts.append(f"<details>\n<summary>전체 {len(tasks)}개 태스크</summary>\n")
    parts.append(render_table(tasks, links) + "\n")
    parts.append("</details>\n")
    return "\n".join(parts)


def parse_args(argv):
    path, full, max_nodes = None, False, DEFAULT_MAX_NODES
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--full":
            full = True
        elif arg == "--max-nodes":
            index += 1
            max_nodes = int(argv[index])
        elif path is None:
            path = arg
        index += 1
    return path, full, max_nodes


def main():
    raw_path, full, max_nodes = parse_args(sys.argv[1:])
    if raw_path is None:
        print("[dag-render] Usage: python render.py <dag_yaml_path> [--full] [--max-nodes N]")
        sys.exit(1)

    dag_path = Path(raw_path)
    if not dag_path.exists():
        print(f"[dag-render] Error: {dag_path} 를 찾을 수 없습니다")
        sys.exit(1)

    with open(dag_path, encoding="utf-8") as handle:
        data = yaml.safe_load(handle)
    if not isinstance(data, dict):
        print("[dag-render] Error: dag.yaml 이 비었거나 매핑이 아닙니다")
        sys.exit(1)

    tasks, warnings = collect(data)
    counts = Counter(t["status"] for t in tasks)
    colors = assign_colors(counts.keys())
    collapsed = pick_collapsed(tasks, max_nodes, full)
    links = resolve_wikilinks(dag_path)

    out_path = dag_path.parent / "dag.md"
    out_path.write_text(
        render_dag_md(tasks, warnings, colors, collapsed, data, links), encoding="utf-8"
    )

    print(f"[dag-render] dag.md 갱신: {out_path}")
    print(f"[dag-render] 태스크 {len(tasks)}개, 상태 {len(counts)}종")
    resolved_ids = {t["id"] for t in tasks} & links.keys()
    print(f"[dag-render] 태스크 표 wikilink: {len(resolved_ids)}/{len(tasks)}개 해소")
    for status, count in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        mark = " (접힘)" if status in collapsed else ""
        print(f"  - {status}: {count}{mark}")
    if warnings:
        print(f"[dag-render] 경고 {len(warnings)}건 — dag.md 상단에 기록했습니다:")
        for warning in warnings[:10]:
            print(f"  ! {warning}")
        if len(warnings) > 10:
            print(f"  ... 외 {len(warnings) - 10}건")


if __name__ == "__main__":
    main()
