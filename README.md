# agent-skills

개인적으로 쓰는 에이전트 스킬 모음입니다. 각 스킬은 [Agent Skills](https://agentskills.io) 형식(`SKILL.md` + 선택적 `scripts/`, `references/`, `agents/`)을 따르고, Claude Code·Codex 등 `SKILL.md`를 읽는 런타임이면 어디서든 씁니다.

## 설치

설치 경로는 하나로 고정합니다: `~/.agents/skills/<slug>`. 스킬 본문의 스크립트 경로도 모두 이 위치를 기준으로 적혀 있습니다.

```bash
git clone https://github.com/zeno0505/agent-skills.git ~/src/agent-skills
mkdir -p ~/.agents/skills
for d in ~/src/agent-skills/skills/*/; do ln -sfn "$d" ~/.agents/skills/"$(basename "$d")"; done

# 런타임이 다른 디렉터리를 읽는다면 같은 곳을 다시 가리키게 한다 (예)
ln -sfn ~/.agents/skills ~/.claude/skills   # Claude Code — 기존 디렉터리가 있으면 개별 링크로
```

필요한 스킬만 골라 링크해도 됩니다. 단, DAG 스택 스킬은 서로의 스크립트를 부르므로 **11개를 함께** 설치하세요.

## 스킬 목록

| 스킬 | 한 줄 설명 | 의존성 | 버전 |
|---|---|---|---|
| [`mockup-screenshot-diff`](skills/mockup-screenshot-diff) | 목업과 실제 앱을 상태×폭 스크린샷·계산 스타일로 짝지어 대조하고 남은 차이를 분류 | Node + Playwright, Python + Pillow | 0.1.0 |
| [`korean-ai-tell-review`](skills/korean-ai-tell-review) | 한국어 글의 AI 티(번역투·과잉 구조·상투어) 점검 — 도메인 용어는 직접 채우는 템플릿 | Python 3 | 0.1.0 |
| [`uiux-design-review`](skills/uiux-design-review) | 정보 구조·흐름·상태·접근성 중심의 UI/UX 리뷰 | (선택) Playwright | 0.1.0 |
| [`minimal-design-review`](skills/minimal-design-review) | 현재 설계에 군더더기가 없는지 서브에이전트에게 반박시켜 확인하는 최소 설계 검토 | — | 0.1.0 |
| [`figma-mapping-interview`](skills/figma-mapping-interview) | Figma 노드↔실제 DOM 요소 매핑을 인터뷰로 확정 | Figma 접근(MCP 등) | 0.1.0 |
| [`cross-agent-review`](skills/cross-agent-review) | 한 에이전트의 결론을 다른 에이전트 세션이 독립 검증 | [Orca](#외부-도구) `orca` CLI (없으면 수동 전달) | 0.1.0 |
| [`slack-reply-draft`](skills/slack-reply-draft) | 스레드 맥락을 읽고 사용자가 직접 붙여 넣을 슬랙 답글 초안 작성 (보내지 않음) | 슬랙 읽기 도구 | 0.1.0 |
| [`weekly-lesson-draft`](skills/weekly-lesson-draft) | 회고 교훈으로 주간 블로그 초안 작성, 작성자 승인 게이트 | — | 0.1.0 |
| [`weekly-lesson-publish`](skills/weekly-lesson-publish) | 승인본을 GitHub Pages 블로그 저장소에 발행 | git, gh | 0.1.0 |
| [`notion-qa-triage`](skills/notion-qa-triage) | 노션 프로젝트의 열린 QA를 기획·디자인 확인 / 설계 고민 / 수정 방향 명확 / 사용자 직접 확인(첨부 미열람) 넷으로 나누고 다음 처리 제안 | 노션 읽기 도구(MCP 등) | 0.1.0 |
| [`x-post-analysis`](skills/x-post-analysis) | X 게시글 원문·맥락을 먼저 확보하고 작성자 의도를 분리해 정리 | X 읽기 도구 | 0.1.0 |
| [`image-making`](skills/image-making) | 글·리포트·PDF에 들어갈 그림 한 장 제작 + 그림 단위 Self-QA (용도: blog / report-card / pdf-figure별 비율·mermaid·공개 필터) | (선택) `pdf-report` 템플릿, Python + Pillow | 0.1.0 |
| [`pdf-report`](skills/pdf-report) | Slidev로 사람용 PDF 보고서 작성 — 자가완결(용어·출처 부록) + 페이지별 시각 QA, 그림은 `image-making` 호출 | Node, Slidev 53, playwright-chromium, poppler-utils, Python + Pillow | 0.1.0 |
| [`plan-dag-stack`](skills/plan-dag-stack) | 프로젝트를 DAG(dag.yaml)로 계획, 라운드 단위 브랜치·PR | DAG 공통¹ | 0.1.0 |
| [`run-dag-stack`](skills/run-dag-stack) | pending 태스크를 라운드 브랜치에 커밋하고 PR 올리기 | DAG 공통¹, gh-stack, CodeRabbit | 0.1.0 |
| [`review-dag-stack`](skills/review-dag-stack) | 라운드 PR의 CodeRabbit 리뷰를 읽고 반영 태스크로 정리 | DAG 공통¹, CodeRabbit | 0.1.0 |
| [`append-dag-stack`](skills/append-dag-stack) | 후속·QA 수정·리뷰 반영·요구 변경을 기존 DAG에 추가 | DAG 공통¹ | 0.1.0 |
| [`track-dag-stack`](skills/track-dag-stack) | 구현·푸시·머지 뒤 dag.yaml을 실제 git/PR 상태와 맞춤 | DAG 공통¹ | 0.1.0 |
| [`setup-dag-stack`](skills/setup-dag-stack) | 새 워크트리에 라운드 브랜치·노트 링크 복원 | DAG 공통¹, gh-stack, (선택) Conductor | 0.1.0 |
| [`read-dag-stack`](skills/read-dag-stack) | dag.yaml 읽기 전용 질의 (상태·의존·대상 파일) | Python 3 + PyYAML | 0.1.0 |
| [`set-dag-stack`](skills/set-dag-stack) | dag.yaml 쓰기 (검증 포함, 직접 편집 금지) | Python 3 + PyYAML | 0.1.0 |
| [`show-dag-stack`](skills/show-dag-stack) | dag.yaml → dag.md 렌더 | Python 3 + PyYAML, (선택) Obsidian 볼트 | 0.1.0 |
| [`summary-dag-stack`](skills/summary-dag-stack) | 남은 일·진행 상황을 사람이 읽는 요약으로 | Python 3 + PyYAML | 0.1.0 |
| [`migrate-dag-stack`](skills/migrate-dag-stack) | 태스크별 PR 스키마(v1)를 라운드 모델(v2)로 승격 | Python 3 + PyYAML, gh | 0.1.0 |

¹ DAG 공통: git, [GitHub CLI](https://cli.github.com) `gh`, Python 3 + PyYAML.

## DAG 스택: 노트 디렉터리

DAG 스킬은 계획 문서(`dag.yaml`, `dag.md`, 태스크별 메모)를 저장소 밖 **노트 디렉터리**에 두고, 저장소에는 `docs/note` 심볼릭 링크로만 연결합니다. 노트는 커밋되지 않습니다 (`.git/info/exclude`에 추가).

```bash
export NOTE_ROOT=~/notes/projects            # 노트 루트 (필수)
~/.agents/skills/setup-dag-stack/scripts/setup_note_link.sh acme/web/profile-avatar
# → <repo>/docs/note -> $NOTE_ROOT/acme/web/profile-avatar
```

- 인자를 생략하면 저장소 이름을 프로젝트 경로로 씁니다. 다른 곳을 가리키는 링크가 이미 있으면 덮어쓰지 않고 멈춥니다.
- **Obsidian 연동(선택):** `show-dag-stack`의 `render.py`는 노트 디렉터리 위쪽에서 `.obsidian`을 찾고, 그 볼트에 `scripts/wikilink_resolve.py`가 있으면 태스크 id를 `[[위키링크]]`로 바꿉니다. 없으면 평문 id로 렌더합니다 — 이 저장소는 그 스크립트를 포함하지 않으며, 없어도 모든 기능이 동작합니다.

## 외부 도구

- **CodeRabbit** — `run-dag-stack`/`review-dag-stack`/`append-dag-stack`는 라운드 PR을 CodeRabbit 봇이 리뷰한다고 가정합니다 (draft PR은 리뷰되지 않음). 다른 리뷰 봇을 쓰면 해당 단계만 바꾸세요.
- **gh-stack** — 라운드 브랜치를 쌓는 `gh stack` 확장. 설치는 해당 확장의 안내를 따르세요.
- **Conductor / Orca** — 워크트리별 에이전트 작업 공간. DAG 스킬은 워크트리 이름 규칙을 예시로만 언급하며 필수는 아닙니다. `cross-agent-review`는 Orca의 `orca terminal list|read|send`를 쓰고, 없으면 요청문을 다른 세션에 직접 붙여 넣는 방식으로 대체합니다.
- **Slidev / Playwright / poppler** — `pdf-report`, `image-making`, `mockup-screenshot-diff`가 사용합니다. 버전은 각 스킬 문서를 보세요.

## 공개 저장소 점검

이 저장소는 공개입니다. 조직·사람·제품 이름, 내부 ID, 토큰, 개인 경로가 들어가지 않도록 커밋 전에 점검합니다.

```bash
scripts/check-blocklist.sh   # scripts/blocklist.txt + (있으면) .blocklist.local
scripts/check-skills.py      # frontmatter name == 디렉터리, description 존재
```

`scripts/blocklist.txt`에는 일반 패턴(토큰 접두어, 슬랙/노션 ID 형식, 개인 경로)만 둡니다. 특정 이름 목록은 그 자체가 노출이므로 저장소에 넣지 않고, 로컬 `.blocklist.local`(gitignore)과 CI 시크릿 `BLOCKLIST_EXTRA`에 둡니다.

## 버전·기여

- 변경 이력은 [CHANGELOG.md](CHANGELOG.md) (Keep a Changelog, SemVer). 릴리스는 `vX.Y.Z` 태그.
- 서드파티에서 가져온 내용의 출처는 [NOTICE.md](NOTICE.md)에 있습니다.

## 라이선스

[MIT](LICENSE)
