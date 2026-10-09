---
name: context-collector
description: Use when starting a feature or fix workflow and needing to collect requirements from external sources (Notion, Jira, Figma, Slack) before any planning begins
---

# Context Collector

외부 소스에서 요구사항을 1회 수집하여 구조화된 `context.md`를 생성하고, `plan-dag-stack`으로 넘긴다.

**Core principle:** 외부 문서 읽기는 정확히 한 번만 — 코드베이스 탐색도, 플래닝도 없다. 요구사항 수집에만 집중한다.

## When to Use

- 새 피처 또는 수정 작업을 시작할 때 티켓 URL, Figma 링크, Slack 스레드가 있는 경우
- `plan-dag-stack` 실행 전 `context.md`가 필요한 경우 (`plan-dag-stack`의 `context_file` 입력)
- **사용하지 않는 경우:** `context.md`가 이미 존재하는 경우 (파일을 읽으면 된다)

## Note Directory

모든 파일은 `note_dir` 하위에 위치한다. DAG 스택 스킬은 프로젝트 노트 디렉터리를 저장소의
`docs/note` 링크로 연결하므로(저장소 README → *DAG 스택: 노트 디렉터리*), 기본값은 `docs/note` 다.

**note_dir 결정 우선순위:**
1. `note_dir` 파라미터 명시 → 그대로 사용
2. `docs/note` 가 이미 프로젝트 노트 디렉터리로 연결돼 있음 → `docs/note`
3. 연결돼 있지 않음 → 사용자에게 `project_path` 를 확인하고
   `~/.agents/skills/setup-dag-stack/scripts/setup_note_link.sh <project_path>` 로 연결한 뒤 `docs/note` 사용 —
   저장소 안에 노트 파일을 직접 만들지 않는다

## Input / Output

**INPUT:**
```yaml
ticket_url: string          # Notion / Jira 티켓 URL
figma_url: string           # (optional) Figma 디자인 링크
slack_thread: string        # (optional) Slack 스레드 URL
project_path: string        # 프로젝트 노트 경로 — 예: "acme/web/profile-avatar" (docs/note 미연결 시 필수)
note_dir: string            # (optional) 직접 지정 — 기본 docs/note
```

**OUTPUT — `{note_dir}/context.md`:**
```yaml
summary: string             # 작업 목적 한 줄 요약
requirements: string[]      # 기능 요구사항 목록
constraints: string[]       # 기술적 제약 (브라우저, API 버전 등)
figma_specs: object         # 디자인 스펙 (figma_url 제공 시)
sources: object[]           # 각 원문의 출처와 지문 — 아래 "원문에 지문을 박는다" 참고
```

그리고 파일 맨 아래에 **변경 이력** 절을 빈 상태로 만들어 둔다. 이후 기획 변경은 그 절에
날짜와 출처를 달아 아래로 쌓는다.

## The Process

1. `note_dir` 결정 (Note Directory 섹션 규칙 적용)
2. `{note_dir}/context.md`가 이미 존재하면 → **중단**, 기존 파일을 읽을 것. 재생성이 필요하면 사용자에게 확인.
   기획이 바뀐 경우에는 재생성이 아니라 **변경 이력에 덧붙이는 것**이 맞다 (아래 "덮어쓰지 않고 쌓는다")
3. `ticket_url`에서 티켓 내용 수집 (Notion / Jira MCP)
4. `figma_url`이 있으면 → Figma MCP로 **어느 노드를 어느 뷰포트에서 볼지**까지 정한다
   (아래 "`figma_specs` 의 모양"). 지문 파일도 매핑도 여기서 만들지 않는다
5. `slack_thread`가 있으면 → Slack MCP로 스레드 내용 수집
6. 수집 내용을 위 스키마에 맞게 `{note_dir}/context.md`로 정리
7. 시안 대조를 할 프로젝트면 `figma-mapping-interview` 로 넘긴다 (아래 "매핑은 이 스킬이 하지 않는다")
8. `plan-dag-stack` 으로 핸드오프 — `project_path` 와 `context_file: "{note_dir}/context.md"` 를 함께 넘긴다
   (`base_branch` 는 `plan-dag-stack` 이 사용자에게 묻는다. 이 스킬이 추측하지 않는다)

## `figma_specs` 의 모양

`figma_specs` 는 **지문이 아니라 참조**다. 어느 노드를 어느 뷰포트에서 볼 것인가만 적는다.

```yaml
figma_specs:
  file_key: "<FIGMA_FILE_KEY>"
  nodes:
    - id: "1234:5678"
      name: "화면_댓글"
      viewport: mobile        # 시안이 폭마다 다른 노드로 갈리므로 노드와 뷰포트가 한 쌍이다
```

지문 파일 자체는 여기서 만들지 않는다. E2E 자산 저장소의 도구가 만들고 그 저장소에 둔다 —
노트 디렉터리는 그 저장소에서 제외돼 있어, 여기에 지문을 두면 노트가 없는 QA 와 CI 가 디자인 TC 를
돌리지 못한다. 같은 것을 두 곳에 두면 정본이 갈린다.

**피그마는 파일이 아니라 읽은 노드가 단위다.** 트리가 깊이에서 끊겨 어떤 노드는 따로 불러야
나오므로, 무엇을 실제로 읽었는지는 노드 단위로만 정확히 적을 수 있다.

## 매핑은 이 스킬이 하지 않는다

시안 노드를 화면 요소에 잇는 일은 `figma-mapping-interview` 가 한다. 이유가 둘이다.

**산출물이 공통 저장소로 간다.** 이 스킬은 개인 작업 흐름용이고 팀원마다 개발 방식이 다른데, 매핑은
E2E 자산 저장소에 들어가 여럿이 읽는다. 만드는 절차가 개인 작업 흐름에만 있으면 남들은 그 매핑을
읽을 수만 있고 만들 수 없다.

**매핑은 수집이 아니라 묻고 답하는 절차다.** 피그마 트리와 DOM 트리가 1대1 이 아니라서
기계적으로 정할 수 없다 — 오토레이아웃이 만든 묶음은 HTML 로 옮기면 사라진다.

## 덮어쓰지 않고 쌓는다

`context.md` 는 외부 원문의 스냅샷이고, 기획은 구현 도중에 바뀐다. 그때 파일을 다시 만들면
처음 기획과 바뀐 기획 중 어느 쪽이 맞는지 파일만 봐서는 알 수 없다.

그래서 **위쪽 본문은 최초 수집 결과로 남기고, 이후 변경은 맨 아래 변경 이력에 쌓는다.**
날짜와 출처를 달고, 늘 맨 아래가 최신이다. `dag.yaml` 의 `project_policy` 가 `decided_at`
으로 이미 쓰는 모양이고, 덮어쓰기가 없으니 두 독자가 서로 다른 버전을 읽는 일이 생기지 않는다.

기획 변경으로 태스크가 늘어날 때 그 이력을 쓰는 것은 `append-dag-stack` 이다 — 태스크와
맥락을 한 동작으로 쓴다. 이 스킬은 최초 1회와 사용자가 명시적으로 요청한 재수집만 한다.

## 원문에 지문을 박는다

수집한 원문마다 출처와 그 시점의 지문을 `sources` 에 남긴다. 원문이 바뀌면 지문이 어긋나고,
어긋남은 사람의 기억이 아니라 검사에 걸린다. TC 파일의 `source.fingerprint` 가 같은 장치다.

```yaml
sources:
  - kind: notion            # notion | figma | slack | jira
    ref: "<URL>"
    collected_at: "2026-09-10"
    fingerprint: "<sha256>"
```

**Notion 은 원문 전체를 해시하지 않는다.** 기획 페이지는 사소한 편집에도 바이트가 바뀌어
헛경보가 끊이지 않는다. 실제로 옮겨 쓴 블록의 텍스트만 이어 붙여 해시한다 — 어긋났다는 것이
「우리가 읽은 내용이 바뀌었다」를 뜻해야 한다.

**Figma 는 노드별로 남긴다.** 파일 하나가 아니라 실제로 읽은 노드가 단위다.

어긋남을 검사하는 것은 `track-dag-stack` 이고, 시점은 라운드 경계다.

## Constraints

- **코드베이스 탐색 금지** — 파일 검색, grep, git log는 모두 범위 밖. 코드베이스 분석은 `plan-dag-stack` 담당
- **1회 실행** — `{note_dir}/context.md`가 존재하면 덮어쓰지 않는다. 변경은 맨 아래 이력에 쌓는다
- **지문 없이 쓰지 않는다** — 원문을 옮겼으면 그 출처와 지문을 `sources` 에 남긴다
- **지문 파일을 만들지 않는다** — `figma_specs` 는 참조까지다. 지문은 자산 저장소의 몫
- **매핑을 정하지 않는다** — `figma-mapping-interview` 로 넘긴다
- **플래닝 금지** — 태스크 도출, DAG 설계, 구현 범위 추정은 하지 않는다

## Integration

**Auto-chains to:**
- **`plan-dag-stack`** — `context.md` 생성 직후 `context_file` 입력으로 전달

**Related skills:**
- **`plan-dag-stack`** — 컨텍스트를 바탕으로 `dag.yaml` 구현 계획을 수립
- **`figma-mapping-interview`** — 시안 노드↔화면 요소 매핑
- **`append-dag-stack`** — 기획 변경을 태스크와 함께 `context.md` 변경 이력에 기록
- **`track-dag-stack`** — 라운드 경계에서 `sources` 지문 어긋남 검사
