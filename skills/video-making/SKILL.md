---
name: video-making
description: >-
  Use when a flow, a change over time, or a PR walkthrough is easier to grasp moving than as one
  figure or a document — render a short (≤90s) silent explainer MP4 from HTML with HyperFrames,
  storyboard first, every on-screen claim tied to a source, reading-time-based scene holds, and a
  per-scene frame self-QA plus a reproducibility check before anyone sees it. A companion to the
  doc or PR, never a replacement; static figures inside scenes come from image-making.
---

# 영상 제작 (HyperFrames → MP4 · 장면 셀프검수)

흐름·변화·PR 설명처럼 **움직여야 이해되는 것**을 90초 이하의 짧은 설명 영상으로 만들고, 보여 주기 **전에** 검수한다.
**스토리보드 → HTML 작성 → check → 렌더 → 장면별 프레임 검수 → 고치기**를 모든 장면이 통과할 때까지 돌린다.

이 스킬이 맡는 것: 영상에 맞는 소재인지 판단, 스토리보드, 컴포지션(HTML) 작성, 장면 길이, 렌더, 장면 단위 검수, 전달.
이 스킬이 맡지 않는 것: 장면 안에 넣을 정적 그림 한 장(→ [`image-making`](../image-making)), 훑어보고 찾아보는 문서(→ [`pdf-report`](../pdf-report)), 발행·커밋.

## 1. 언제 쓰나

| 전하려는 것 | 쓸 스킬 |
|---|---|
| 개념 하나, 구조 한 장 | [`image-making`](../image-making) |
| 훑어보고 다시 찾아볼 참고 자료, 근거표 | [`pdf-report`](../pdf-report) |
| **시간에 따라 바뀌는 것**: 단계가 이어지는 흐름, 상태 변화, 전/후, PR 한 건의 변경 설명 | **이 스킬** |

- 영상은 **동반 자료**다. 원본 문서·PR을 대신하지 않는다. 영상만 보고 결정해야 하는 내용이면 문서를 먼저 고친다.
- 길이는 **90초 이하**. 더 길어지면 영상을 둘로 나누거나 그 내용은 문서로 보낸다.
- 기본은 **무음**(자막·내레이션 없음). 화면 글만으로 읽혀야 한다.

## 2. 의존성과 환경

| 구성 | 요구 | 비고 |
|---|---|---|
| Node.js | **22 이상** | HyperFrames CLI의 `engines` 요구 |
| HyperFrames CLI | `npx hyperframes@<고정 버전>` | **전역 설치 금지.** 검증한 버전: `0.8.143`. 프로젝트 `package.json` 스크립트도 같은 버전으로 고정 |
| FFmpeg · ffprobe | PATH에 있음 | 인코딩·프레임 추출 |
| 헤드리스 Chrome | `chrome-headless-shell` | 첫 `check`/`render` 때 `~/.cache/hyperframes/chrome/`에 **자동으로 내려받는다**(약 260MB). 없으면 느린 스크린샷 방식으로 대체된다 |
| 글꼴 | 한글이면 Noto Sans CJK KR | `fc-list \| grep -i "Noto Sans CJK"` |
| GSAP | 프로젝트 안 로컬 사본 `gsap.min.js` | 렌더 중 네트워크를 쓰지 않기 위해 |

### 사전 점검 — 설치는 사람 승인 후에만

```bash
~/.agents/skills/video-making/scripts/preflight.sh            # 기본 버전 0.8.143
~/.agents/skills/video-making/scripts/preflight.sh --node <node22-bin-dir> --version 0.8.143
```

`preflight.sh`는 **아무것도 설치하지 않는다.** Node 버전, npx, FFmpeg/ffprobe, Noto Sans CJK, Chrome 캐시 유무를 보고,
CLI가 npx 캐시에 이미 있을 때만 `hyperframes doctor`를 돌린다(`npx --no-install`). 빠진 것이 있으면 목록과 설치 명령 **제안**만 출력하고 멈춘다.

- 빠진 의존성은 **사람에게 목록을 보여 주고 승인받은 뒤** 설치한다. CLI를 처음 받는 것(`npx hyperframes@<버전> --version`)과 Chrome 첫 다운로드도 같은 취급이다.
- 승인 없이 시스템 패키지·전역 npm 패키지를 설치하지 않는다.

### 환경별 메모

- **여러 에이전트가 함께 쓰는 Linux 머신:** 시스템 Node가 22보다 낮으면 시스템을 올리지 말고, 승인을 받아 Node 22 공식 tarball을 프로젝트 옆 폴더에 풀어 그 `bin`을 해당 셸의 `PATH` 앞에만 붙인다(체크섬 확인). Chrome 캐시는 사용자 홈 아래 하나를 공유한다.
- **macOS (Claude Code·Codex 등 로컬 에이전트):** `brew install node@22 ffmpeg`를 제안하고 승인을 받는다. keg-only인 `node@22`는 `PATH="$(brew --prefix node@22)/bin:$PATH"`로 해당 셸에만 붙인다. 한글 글꼴은 Noto Sans CJK KR을 설치하거나, 시스템 글꼴을 `@font-face local()`로 이름을 정확히 적어 쓴다.

### 환경 변수·네트워크

```bash
export HYPERFRAMES_NO_TELEMETRY=1    # 익명 사용 통계 끄기 (또는 npx hyperframes@<버전> telemetry disable)
export HYPERFRAMES_SKIP_SKILLS=1     # init 이 GitHub에서 에이전트 스킬을 확인·설치하지 않게
```

- `init` 템플릿은 GSAP를 CDN에서 부른다. 받아 둔 로컬 사본(`<script src="gsap.min.js">`)으로 바꾼다.
- 렌더·검수 중에는 네트워크 자원(웹 글꼴, CDN 스크립트, 원격 이미지)을 쓰지 않는다. 자산은 모두 프로젝트 폴더에 둔다.
- 기계가 달라도 **바이트까지 같은** 결과가 필요하면 `render --docker`(Chromium·글꼴·FFmpeg 고정)를 쓴다. 같은 기계에서는 그냥 렌더해도 매번 같다.

## 3. 입력

- 원본: 설명할 대상의 실제 파일(스킬 문서, PR diff, 설정 파일, 설계 문서). **원격으로 읽고**, 화면에 쓸 주장마다 파일·줄을 메모한다
- 보는 사람: 개발자 / 비개발 동료 / 작성자 본인. 용어 수준이 달라진다
- 목표 길이(≤90초), 해상도(기본 1920×1080, 30fps)
- 공개 범위 제약: 호출하는 쪽이 정한 금지 항목(실명, 내부 ID, 미공개 수치 등)

## 4. 스토리보드 먼저 (작성자 검토 게이트)

HTML을 쓰기 전에 장면 표를 만든다.

| 장면 | 한 줄 메시지 | 화면 구성(도식 우선) | 화면 글(카드당 4–5줄 이하) | 근거(파일:줄 / URL) |
|---|---|---|---|---|

- **장면 하나에 생각 하나.** 두 가지를 말하려면 장면을 나눈다.
- **도식이 먼저, 글은 그다음.** 흐름은 박스·화살표, 비교는 표, 시간은 타임라인 막대로.
- **근거 칸이 빈 주장은 화면에 넣지 않는다.** 직접 잰 값(렌더 시간, 체크섬 일치 등)은 「직접 측정」이라고 근거 칸에 적는다.
- 작성자가 스토리보드를 승인하기 전에는 **최종 렌더를 하지 않는다**(시안 렌더는 괜찮다).

## 5. 컴포지션 작성 규칙

### HyperFrames 계약

- 컴포지션은 HTML 파일 하나다. 루트 요소에 `data-composition-id`, `data-width`, `data-height`, `data-duration`.
- 장면은 `class="clip"` + `data-start`(초) + `data-duration`(초). 시간 정보는 속성에 두고 JS로 계산해 넣지 않는다(lint가 읽는다).
- 움직임은 **paused** GSAP 타임라인 하나에 절대 시각으로 적고 등록한다:
  `const tl = gsap.timeline({ paused: true }); … window.__timelines["main"] = tl;`
  렌더러는 이 타임라인을 재생하지 않고 프레임마다 시각 t로 seek해서 찍는다.
- **결정성:** `Date.now()`, 시드 없는 `Math.random()`, `requestAnimationFrame` 기반 애니메이션, 렌더 중 `fetch` 금지.

### 화면 규칙

| 규칙 | 이유 |
|---|---|
| 상단에 **진행 막대**(전체 길이에 걸친 `scaleX` 트윈) 또는 단계 표시줄을 계속 둔다 | 지금 어디쯤인지 알면 인지 부담이 준다 |
| 카드 하나에 **4–5줄 이하**, 본문 글자 **≥34px**, 라벨·출처·푸터도 **≥28px**(1080p 기준) | 26px 출처 줄은 작아서 못 읽는다는 지적을 받았다 |
| 한글 글꼴은 `@font-face { font-family: X; src: local("Noto Sans CJK KR"); }`로 선언(굵게는 `local("Noto Sans CJK KR Bold")`) | 선언이 없으면 lint 오류, 렌더는 대체 글꼴로 바뀐다 |
| 루트에 `word-break: keep-all` | 한글 단어가 중간에서 끊기는 것을 막는다 |
| 겹쳐서 바꿔 끼우는 요소(활성 단계 강조 등)는 `data-layout-allow-overlap`, 가려지는 아래 글자는 함께 투명하게 | `check`의 겹침·대비 경고가 거짓 양성으로 남지 않게 |
| 화면 아래에 출처 한 줄(저장소·파일 경로·문서 URL) | 화면 주장의 근거를 영상 안에서 보여 준다 |

`template/style.css`에 위 규칙(글꼴 선언, keep-all, 최소 글자 크기, 카드·흐름 상자·진행 막대)이 들어 있다.

## 6. 장면 길이 — 다 보인 뒤에도 읽을 시간

장면 길이는 손으로 정하지 않고 `build_timeline.py`가 계산한다.

```
장면 길이 = max( 마지막 등장 시각 + 등장 애니메이션(0.5s) + 최소 유지(4.5s),
                 기본 1.5s + 글자량 / 읽기 속도 )
글자량    = 한글·한자 글자 수 × 1.0 + 그 밖의 공백 아닌 글자 수 × 0.5
읽기 속도 = 초당 15 (스토리보드에서 장면별 cps·hold로 조정 가능)
```

- 모든 장면은 **다 나타난 뒤 최소 4.5초** 머문다. 지난 시안에서 마지막 줄이 나타나고 1–2초 만에 넘어간 장면이 지적을 받았다.
- 글이 많은 장면은 4.5초로도 부족하다는 리뷰를 받았다 → 글자량 항이 길이를 늘린다. 계산 결과가 20초를 넘으면 장면을 나눈다.
- 빌더는 장면마다 어느 규칙이 길이를 정했는지(`hold` / `read`)와 글자량을 표로 출력한다. 리뷰에서 "짧다"는 말이 나오면 cps를 낮춘다.

```bash
python3 ~/.agents/skills/video-making/scripts/build_timeline.py storyboard.json   # → index.html, timing.json
```

스토리보드 JSON 형식은 `template/storyboard.example.json`에 있다(장면별 `body`, `reveals: [[선택자, 앞 등장과의 간격]]`, 선택 `tweens`, `cps`, `hold`).

## 7. 렌더

프로젝트 준비(한 번, 네트워크는 이 단계에서만):

```bash
HYPERFRAMES_SKIP_SKILLS=1 npx --yes hyperframes@0.8.143 init <name> --example blank --non-interactive --resolution landscape
cp ~/.agents/skills/video-making/template/{style.css,storyboard.example.json} <name>/
# GSAP 로컬 사본: init 템플릿이 가리키는 버전(0.8.143 기준 gsap@3.14.2)의 dist/gsap.min.js 를 프로젝트에 받아 둔다
```

```bash
npx --yes hyperframes@0.8.143 check                                   # 아래 QA 게이트
npx --yes hyperframes@0.8.143 render --quality high --fps 30 --output out/video.mp4
```

- 참고 수치(8코어 Linux, 소프트웨어 GPU): 1080p 30fps 59초 영상 렌더 약 28초, 85초 영상 약 39초.
- 렌더는 `HeadlessExperimental.beginFrame`으로 프레임마다 한 번에 그린 화면을 받아 FFmpeg(image2pipe → libx264)로 넣는다. 첫 렌더에서 Chrome 다운로드가 일어날 수 있다(§2).

## 8. QA 게이트 (보여 주기 전 필수)

1. **`hyperframes check` 오류 0건.** 경고는 읽고 판단한다(장면을 하위 컴포지션으로 나누라는 권고는 무시해도 된다).
   `check`는 **몇 시점만 표본으로 찍는다.** 잘못 놓인 요소, 상자 안에서 줄이 바뀐 제목, 단어 중간 끊김을 놓쳤다 → 2번이 반드시 필요하다.
2. **장면마다 다 나타난 프레임 한 장씩 직접 본다.**
   ```bash
   python3 ~/.agents/skills/video-making/scripts/extract_frames.py out/video.mp4 --timing timing.json --out out/qa --tag r1
   ```
   이미지 뷰어가 같은 경로를 캐시할 수 있으니 재렌더마다 `--tag`를 바꾼다. 장면마다 `통과 / 수정필요`:
   - [ ] 잘림·겹침 없음, 상자 밖으로 나간 글자 없음
   - [ ] 한글 단어 중간 끊김·한 단어만 남은 줄 없음
   - [ ] 글자 크기(본문 ≥34px, 출처 ≥28px)·대비
   - [ ] 화면 주장이 스토리보드 근거 칸과 일치(과장·부정확 표현 없음)
   - [ ] 공개 범위 필터 통과
3. **재현성:** 같은 소스로 한 번 더 렌더해 `sha256sum` 두 값이 같은지 본다. 다르면 결정성 규칙(§5) 위반을 찾는다.
4. (선택) **영상으로 한 번 보기:** 실제 속도로 처음부터 끝까지 보고, 읽기 전에 넘어가는 장면이 있으면 그 장면의 `cps`/`hold`를 고친다.

고치기 루프: HTML(또는 스토리보드 JSON) 수정 → `build_timeline.py` → `check` → 렌더 → 2번. 지난 시안들은 이 루프를 2–3번 돌았다.

## 9. 출력·전달

```
- video: out/<slug>.mp4          # 1920×1080, 30fps, 길이 N초, 무음
  source: <컴포지션 폴더>          # index.html, storyboard.json, style.css, gsap.min.js, package.json(버전 고정)
  frames: [out/frame-1.png, out/frame-2.png, out/frame-3.png]   # 대표 장면 3장
  sources: [<근거 링크 목록>]
  qa: check 0 errors · 장면 N/N 통과 · 재렌더 체크섬 일치
  gif: (선택) PR·문서 첨부용 — render --format gif --fps 15
```

- 대표 프레임 3장은 흐름의 처음·가운데·핵심 장면에서 고른다.
- 커밋·업로드·발행은 이 스킬이 하지 않는다. 파일 경로로 넘긴다.

## 10. 다른 스킬·도구와의 관계

- 장면 안에 정적 도식 한 장이 필요하면 [`image-making`](../image-making)을 용도 `pdf-figure`에 가까운 설정으로 호출하고, 받은 PNG를 장면에 `<img>`로 넣는다. 움직임이 필요한 도식은 HTML/CSS로 직접 만든다.
- 같은 내용을 문서로도 남겨야 하면 [`pdf-report`](../pdf-report)가 맡는다. 영상은 그 문서의 요약 동반물이다.
- HyperFrames에는 PR을 30–90초 설명 영상으로 만드는 자체 워크플로(`/pr-to-video`, `npx hyperframes@<버전> skills update pr-to-video`로 설치 — 설치이므로 승인 후)가 있다. PR 설명 영상은 그 워크플로를 먼저 시험해 보고, 이 스킬의 스토리보드 게이트·타이밍 규칙·QA 게이트를 그 위에 얹을지 판단한다(아직 평가 전).

## Do not

- 전역 설치(`npm i -g hyperframes`)나 승인 없는 시스템 패키지 설치
- 스토리보드 승인 전에 최종 렌더
- 근거 없는 주장, 생성 이미지로 그린 숫자·흐름
- `check` 통과만 보고 "검수 완료"라고 하기 — 장면별 프레임을 직접 본다
- 렌더 중 네트워크 자원, `Date.now()`·시드 없는 난수
- 90초를 넘기는 한 편짜리 영상, 영상만으로 문서를 대신하기
