# Changelog

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르고, 버전은 [SemVer](https://semver.org/lang/ko/)를 따릅니다.

## [Unreleased]

## [0.2.0] - 2026-10-10

0.1.0 이관 때 빠진 DAG 스택 짝 스킬 `collect-dag-stack`과 `receive-dag-stack`을 추가하고, DAG 스택에서 `gh-stack`을 필수에서 선택으로 내렸습니다.

### Added

- `collect-dag-stack` — 개인 노트 볼트에서 이관, DAG 스택 이름 규칙에 맞춰 이름을 바꿈. 계획 전 요구사항 수집(Notion·Jira·Figma·Slack → `context.md`, 원문별 출처·지문, 변경 이력은 덮어쓰지 않고 쌓기).
  - 핸드오프 대상을 `plan-dag-stack`으로 바꾸고, 출력 경로를 `plan-dag-stack`의 `context_file`(`docs/note/context.md`)에 맞춤. `note_dir`는 `setup-dag-stack`의 `docs/note` 링크 규칙을 따르고, 입력 `project_name`을 `project_path`로 바꿈.
  - 예시 Figma 파일 키·노드·프로젝트명을 일반 예시로 교체.
- `receive-dag-stack` — 개인 노트 볼트에서 이관, DAG 스택 이름 규칙에 맞춰 이름을 바꿈. `run-dag-stack`이 파견한 서브에이전트의 실행 계약(구현 / 통합 구현 / 리뷰 / 리뷰 수정 모드, append-only `implementation.md`, 커밋까지만 하고 푸시·PR은 오케스트레이터 몫).
  - 오케스트레이터 참조를 `run-dag-stack`으로 바꾸고, 이 저장소에 없는 통합 구현 오케스트레이터 이름은 일반 서술로 대체. 신규 태스크 추가는 `append-dag-stack`/`set-dag-stack` 경유로 명시.
  - 리뷰 모드 입력을 라운드 모델에 맞춤(태스크 커밋 diff, 라운드 PR이 열려 있으면 PR diff). 위키링크 예시 경로를 일반화하고 Obsidian 볼트가 없으면 평문 id를 쓰도록 명시.

### Changed

- `plan-dag-stack` — `context.md`를 `collect-dag-stack`이 만든다는 점을 3단계에 명시.
- `track-dag-stack` — 지문 재수집 주체를 `collect-dag-stack`으로 명시.
- `run-dag-stack` — 서브에이전트 파견 시 `receive-dag-stack`을 따르도록 4단계에 명시. 쌓인 라운드의 기본 흐름을 일반 git으로: 라운드 *n+1*을 라운드 *n* 브랜치에서 따고 `gh pr create --base <라운드 n 브랜치>`(draft 금지)로 PR을 엶. 아래 라운드가 바뀌면 위 브랜치에 merge로 전파(force-push 금지 명시), 아래 라운드가 머지되면 `gh pr edit --base`로 다음 PR의 base를 바꿈. `gh-stack`은 설치돼 있을 때의 선택지로만 남기고 기존 안전 규칙(`submit --auto --open`, `view --json`, `unstack` 자동 실행 금지)을 유지.
- `setup-dag-stack` — `gh-stack` 등록 단계를 선택 사항으로. force-push 금지는 유지.
- `append-dag-stack`, `set-dag-stack`, `show-dag-stack` — 금지 문구를 도구 중립적으로(브랜치·스택 변경 전반: `git branch`/`rebase`/`push`, `gh pr`, `gh-stack`).
- README — `gh-stack`을 의존성에서 선택 도구로 표기.

## [0.1.0] - 2026-10-08

첫 공개 릴리스. 개인 작업 환경에서 쓰던 스킬을 옮기면서 조직·사람·제품 이름, 내부 ID, 개인 경로를 일반화했습니다.

### Added

- `mockup-screenshot-diff` — 신규 작성. 목업↔앱 상태×폭 스크린샷 대조 절차, `capture.mjs`(Playwright), `pair_sheet.py`(대조 시트·스타일 차이표).
- `korean-ai-tell-review` — 개인 노트 볼트의 스킬에서 이관. 도메인 용어 목록을 사용자 템플릿 `references/domain-terms.md`로 분리.
- `uiux-design-review` — 개인 노트 볼트에서 이관 (내용 변경 없음).
- `minimal-design-review` — 개인 노트 볼트에서 이관 (내용 변경 없음).
- `figma-mapping-interview` — 개인 노트 볼트에서 이관. 예시의 제품 용어·경로를 일반 예시로 교체.
- `cross-agent-review` — 개인 노트 볼트에서 이관. Orca CLI 의존성 명시, 요청 템플릿을 `references/`로 분리.
- `slack-reply-draft` — 에이전트 작업 공간 워크플로에서 이관. 런타임 전용 도구 이름과 내부 판단 사례를 빼고 일반화.
- `weekly-lesson-draft`, `weekly-lesson-publish` — 에이전트 작업 공간 워크플로에서 이관. 발행 지표 기록 단계를 선택 사항으로 일반화. 그림은 `image-making`(용도 `blog`)을 호출.
- `notion-qa-triage` — 개인 노트 볼트에서 이관. 열린 QA를 네 갈래(기획·디자인 확인 / 설계 고민 / 수정 방향 명확 / 사용자 직접 확인)로 분류. 노션 MCP가 첨부 이미지·영상 내용을 돌려주지 않는다는 주의를 추가하고, 프로젝트 고유 예시를 일반 예시로 바꿈. Codex용 `agents/openai.yaml` 포함.
- `x-post-analysis` — 에이전트 작업 공간 워크플로에서 이관 (frontmatter 추가).
- `image-making` — 에이전트 작업 공간 워크플로에서 이관. 블로그 전용이던 이미지 스킬과 PDF 스킬의 그림 관련 기준을 합쳐 "그림 한 장" 스킬로 정리: 용도 `blog` / `report-card` / `pdf-figure`별 비율·mermaid 허용·공개 필터 표, 그림 단위 Self-QA A–I.
- `pdf-report` — 신규 작성 + 이관. 실제로 쓰던 Slidev 53 내보내기 절차(`build.sh`, `preflight.py`, `qa_pages.py`, 최소 템플릿)에 PDF 보고서 규칙을 합침: 문서 구성, 자가완결성(용어 부록 + 새 출처 규칙·「부록 — 출처」표), 페이지 단위 시각 QA. 그림은 `image-making`(용도 `pdf-figure`)을 호출하고, 조직 고유의 보고서별 규칙은 빼고 일반화.
- DAG 스택 11종 — `plan-`, `run-`, `review-`, `append-`, `track-`, `setup-`, `read-`, `set-`, `show-`, `summary-`, `migrate-dag-stack`. 개인 노트 볼트의 최신본에서 이관.
  - 스크립트 경로를 `~/.agents/skills/<slug>/scripts/` 로 통일, 스킬 간 참조는 상대 경로로.
  - 노트 볼트 전용 스크립트 의존을 제거: `setup_note_link.sh`를 `NOTE_ROOT` 기반 범용 스크립트로 새로 작성해 `setup-dag-stack`에 포함, Obsidian 위키링크 변환은 선택 기능으로 문서화.
  - 예시 브랜치·프로젝트 경로를 일반 예시로 교체.
- 저장소 점검: `scripts/check-blocklist.sh`, `scripts/check-skills.py`, GitHub Actions CI.
