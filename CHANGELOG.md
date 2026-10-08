# Changelog

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르고, 버전은 [SemVer](https://semver.org/lang/ko/)를 따릅니다.

## [Unreleased]

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
- `weekly-lesson-draft`, `weekly-lesson-images`, `weekly-lesson-publish` — 에이전트 작업 공간 워크플로에서 이관. 발행 지표 기록 단계를 선택 사항으로 일반화.
- `notion-qa-triage` — 개인 노트 볼트에서 이관. 열린 QA를 네 갈래(기획·디자인 확인 / 설계 고민 / 수정 방향 명확 / 사용자 직접 확인)로 분류. 노션 MCP가 첨부 이미지·영상 내용을 돌려주지 않는다는 주의를 추가하고, 프로젝트 고유 예시를 일반 예시로 바꿈. Codex용 `agents/openai.yaml` 포함.
- `x-post-analysis` — 에이전트 작업 공간 워크플로에서 이관 (frontmatter 추가).
- `slidev-pdf` — 신규 작성. 실제로 쓰던 Slidev 53 내보내기 절차(작성 규칙, `build.sh`, `preflight.py`, `qa_pages.py`, 최소 템플릿)와 페이지 시각 QA 체크리스트.
- DAG 스택 11종 — `plan-`, `run-`, `review-`, `append-`, `track-`, `setup-`, `read-`, `set-`, `show-`, `summary-`, `migrate-dag-stack`. 개인 노트 볼트의 최신본에서 이관.
  - 스크립트 경로를 `~/.agents/skills/<slug>/scripts/` 로 통일, 스킬 간 참조는 상대 경로로.
  - 노트 볼트 전용 스크립트 의존을 제거: `setup_note_link.sh`를 `NOTE_ROOT` 기반 범용 스크립트로 새로 작성해 `setup-dag-stack`에 포함, Obsidian 위키링크 변환은 선택 기능으로 문서화.
  - 예시 브랜치·프로젝트 경로를 일반 예시로 교체.
- 저장소 점검: `scripts/check-blocklist.sh`, `scripts/check-skills.py`, GitHub Actions CI.
