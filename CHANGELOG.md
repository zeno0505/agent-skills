# Changelog

이 파일은 [Keep a Changelog](https://keepachangelog.com/ko/1.1.0/) 형식을 따르고, 버전은 [SemVer](https://semver.org/lang/ko/)를 따릅니다.

## [Unreleased]

## [0.4.0] - 2026-10-10

DAG 스택에 PR 리스크 티어 시스템(상/중/하)을 추가했습니다. 리뷰어(CodeRabbit 또는 로컬 리뷰 에이전트)가 각 라운드 PR의 리스크를 평가하고 머지 권장 사항을 제공합니다.

### Added

- `references/pr-risk-tiers.md` — PR 리스크 티어 가이드라인 문서. 티어 정의(상/중/하), 결정론적 시그널 설정(`risk_config`), 리뷰 라운드 제한과의 통합, 머지 권장 로직, 후속 피드백 루프를 설명.
- `plan-dag-stack` — 스키마에 `risk_config` 최상위 필드 추가 (선택): `critical_paths`, `critical_files`, `max_diff_lines`로 결정론적 시그널을 정의하여 `상` 티어를 강제할 수 있음. 없으면 리뷰어 판단만 사용.
- `plan-dag-stack` — 스키마의 `rounds[]` 엔트리에 4개 필드 추가: `risk_tier` (상/중/하), `risk_reason` (한 줄 사유), `risk_signals` (발화한 시그널 목록), `risk_assessed_by` (평가자 이름). 첫 리뷰 후 기록, 없으면 `null`.
- `review-dag-stack` — 첫 리뷰 후 리스크 티어 평가 단계 추가. 결정론적 시그널 확인 → 리뷰어 판단 → 기록. 승인 시 티어와 리뷰 라운드 카운트에 따라 머지 권장 생성 (하/1라운드 클린 → 권장, 중/2라운드 크리티컬 없음 → 권장, 상 → 사람 리뷰 필수).
- `read-dag-stack/scripts/query.py` — `--pr` 출력에 리스크 필드 4개 포함 (`null`이면 명시).
- `show-dag-stack/scripts/render.py` — 회차 표에 리스크 열 추가. 티어와 사유(40자 이내)를 함께 표시, 없으면 `—`.
- `run-dag-stack` — 라운드 종료 제안 시 `--pr` 출력(리스크 티어 포함)을 같이 보고하도록 명시.

### Changed

- `review-dag-stack` — frontmatter `description`에 리스크 평가 언급 추가. Process 단계 재번호: 리스크 평가가 step 3, 승인 처리가 step 4, 머지 권장이 승인 안에 통합. Constraints에 리스크 평가 제약 추가 (첫 리뷰만, 리뷰어가 평가, 시그널 강제, 권장이지 자동 머지 아님).
- `plan-dag-stack` — Schema 절에 `risk_config`와 `rounds[]` 신규 필드 문서화. 역호환성: 선택 필드이므로 기존 파일은 그대로 동작.
- README — 아직 업데이트 안 함 (스킬 목록 버전은 개별 스킬 변경이 아니라 전체 배포 시점에 올림).

### Backward Compatibility

- `risk_config` 없는 기존 `dag.yaml` → 결정론적 시그널 비활성, 리뷰어 판단만 사용.
- `risk_tier` 등 4개 필드가 `null`인 라운드 → "평가 안 됨"으로 처리, 기존 2라운드 제한은 여전히 동작.
- 기존 스킬(`read-dag-stack`, `show-dag-stack`, `track-dag-stack`)은 신규 필드 무시하고 정상 동작.

## [0.3.2] - 2026-10-10

macOS에서 외부 에이전트(Claude Code 헤드리스)로 `video-making`을 처음부터 끝까지 돌려 본 결과와 반복 영상·PDF 운영 피드백을 반영했습니다(`video-making` 0.1.2, `pdf-report` 0.1.1).

### Added

- `video-making` — 반복 영상(같은 형식을 매주) 절(§11): 장면 템플릿 + 데이터 파일 + 슬롯, 바뀐 장면만 다시 렌더·검수하는 패턴과 비용(분할 렌더는 처음 한 번이 단일 렌더보다 몇 배 느림). 엔진 코드는 넣지 않음.
- `video-making` — 초안 전용 실행 규칙: 초안 배지·`-draft` 파일명을 지키면 스토리보드 승인 대신 초안 영상 + `claims-sources.md`를 작성자가 승인, 승인 전엔 공식 채널로 보내지 않음.
- `video-making` — `build_timeline.py`가 장면 길이를 넘기는 트윈(반복 포함)을 경고, 스토리보드 `no_read_classes`로 읽기 시간에서 뺄 클래스를 추가.
- `video-making` — `preflight.sh`가 `VIDEO_NODE_BIN` 환경 변수로 Node 위치를 받음. 결과를 `ready`(0) / `needs one-time fetch`(3) / `missing`(1)로 나눠, CLI·Chrome이 아직 없는데 `ready`라고 하던 문제를 고침.
- `pdf-report` — `qa_pages.py`가 페이지 전체 잉크 비율(`ink%`)을 재고 거의 빈 페이지를 `BLANK`로 표시, `--fail-blank`면 종료 코드 1. `build.sh`가 이 옵션으로 호출.
- `pdf-report` — 같은 보고서를 다시 만들 때 고정 폴더(`$PDF_DECK_ROOT/<보고서-이름>/`)를 재사용하는 규칙.

### Changed

- `video-making` — 문서의 설치 경로를 `$SKILL_DIR`로 바꿈(스킬을 `~/.claude/skills` 등 다른 곳에 둔 에이전트가 경로를 못 찾던 문제).
- `video-making` — macOS 대응: GNU `timeout`이 없으면 `gtimeout`이나 perl로 대신(없으면 CLI 점검이 조용히 「not in cache」로 빠지던 문제), Noto Sans CJK KR이 없으면 Apple SD Gothic Neo로 대체(템플릿 CSS `local()` 목록과 사전 점검), `shasum -a 256`, OS별 캡처 방식 차이를 문서화.
- `video-making` — 샌드박스 에이전트(Codex `workspace-write`)에서는 npm 캐시·로컬 서버·프로세스 우선순위가 막혀 `check`·`render`가 돌지 않음을 문서화. `vendor_gsap.sh --fetch`가 npm 오류를 숨기지 않고 대안을 안내. `extract_frames.py`가 영상이 없으면 짧은 오류로 끝남.
- `video-making` — 새 고정 요소에는 `data-no-read`가 필수임을 강조, 템플릿·분할 영상은 전체 진행 막대 대신 장면 표시를 쓰도록 안내, QA 프레임은 컷 0.3초 전이라 반복 애니메이션은 깔끔한 자세로 끝나게, 결과 파일명(`<slug>.mp4` / `<slug>-draft.mp4`)과 스토리보드 표 위치(`storyboard.md`)를 명시.
- README — `video-making` 0.1.2(Linux·macOS), `pdf-report` 0.1.1.

## [0.3.1] - 2026-10-10

`video-making` 첫 실사용 피드백을 반영했습니다(스킬 0.1.1).

### Added

- `video-making` — 템플릿에 `hyperframes.json`·`package.json`을 넣어 `init` 없이 프로젝트를 만듦. `scripts/vendor_gsap.sh` 추가: `gsap@3.14.2`를 npm 캐시에서 꺼내 sha256·라이선스 주석을 확인해 프로젝트에 복사(캐시에 없으면 승인 후 `--fetch` 1회). GSAP 라이선스가 공개 저장소 재배포를 분명히 허락하지 않아 사본은 커밋하지 않음.
- `video-making` — 스토리보드 최상위 `overlay`(초안 배지처럼 모든 장면에 보이는 요소, 시간 속성 없는 위층으로 렌더), 장면 `class` 필드와 `.scene.center`(아래 절반이 비는 짧은 장면용 세로 가운데 정렬), `.draft` 배지 스타일.
- `video-making` — 근거 표기 형식(저장소 경로:줄, 커밋·PR, Slack 퍼머링크, Notion URL, 웹 URL, 직접 측정)과 `claims-sources.md` 전달.

### Changed

- `video-making` — 1회 받기(CLI·Chrome `browser ensure`·GSAP, 승인 후) 뒤로는 모든 명령을 `npx --no-install --offline hyperframes@0.8.143`로 바꿔 검사·렌더에 네트워크를 쓰지 않음. `--no-install`만으로는 npx가 버전 확인차 레지스트리에 접속하고, 네트워크가 없으면 멈춤.
- `video-making` — `build_timeline.py`가 `.source`·`.draft`·`data-no-read` 요소와 overlay를 읽기 시간 글자량에서 뺌.
- `video-making` — `extract_frames.py`가 태그 붙은 파일과 함께 고정 이름 `frame-N.png`도 씀(`--no-stable`로 끔).
- `video-making` — `preflight.sh --node`가 Node 폴더와 그 `bin` 폴더를 모두 받음. `doctor`가 선택 항목(Docker 데몬 등)만 실패해 「Some checks failed」를 내면 note로 따로 적고 `result: ready` 유지.
- `video-making` — QA 게이트에 늘 나오는 무시 가능 경고(`nested_structure_needs_subcomposition`, `timeline_track_too_dense`)를 명시. HyperFrames 0.8.143에는 특정 lint 규칙을 끄는 공식 방법이 없음.
- README — `video-making` 행을 0.1.1로, 외부 도구 HyperFrames 항목에 `--no-install --offline`·GSAP 처리 반영.

## [0.3.0] - 2026-10-10

흐름·변화·PR 설명용 설명 영상 스킬 `video-making`을 추가했습니다.

### Added

- `video-making` — 신규 작성. 흐름·변화·PR 설명용 90초 이하 무음 설명 영상을 HyperFrames로 만드는 절차: 언제 쓰나(`image-making`·`pdf-report`와 구분), 의존성·환경(Node 22, 고정 버전 npx, 사전 점검 후 승인받고 설치, 텔레메트리·스킬 자동 설치 끄기, 로컬 GSAP), 스토리보드 게이트, 화면 규칙(진행 막대, 카드당 4–5줄, 최소 글자 크기, CJK `@font-face local()`, `keep-all`), 글자량 기반 장면 길이, QA 게이트(`check` + 장면별 프레임 + 재렌더 체크섬). `preflight.sh`, `build_timeline.py`, `extract_frames.py`, 기본 스타일·스토리보드 예시 포함.
- README — 스킬 목록에 `video-making` 행, 외부 도구에 HyperFrames 항목.

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
