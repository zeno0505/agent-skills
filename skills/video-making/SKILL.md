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
| HyperFrames CLI | `npx --no-install --offline hyperframes@<고정 버전>` | **전역 설치 금지.** 검증한 버전: `0.8.143`. 승인받은 1회 받기(§7) 뒤로는 `--no-install --offline`으로 npx 캐시에서만 부른다. `template/package.json` 스크립트도 같은 버전·같은 방식 |
| FFmpeg · ffprobe | PATH에 있음 | 인코딩·프레임 추출 |
| 헤드리스 Chrome | `chrome-headless-shell` | 1회 받기(§7)에서 `browser ensure`로 `~/.cache/hyperframes/chrome/`에 미리 받는다(약 260MB). 미리 받지 않으면 첫 `check`/`render`가 **자동으로 내려받는다**(네트워크) |
| 글꼴 | 한글이면 Noto Sans CJK KR | `fc-list \| grep -i "Noto Sans CJK"` |
| GSAP | 프로젝트 안 로컬 사본 `gsap.min.js` (`gsap@3.14.2`) | 렌더 중 네트워크를 쓰지 않기 위해. `scripts/vendor_gsap.sh`가 npm 캐시에서 꺼내 sha256을 확인해 넣는다(아래) |

### 사전 점검 — 설치는 사람 승인 후에만

```bash
~/.agents/skills/video-making/scripts/preflight.sh            # 기본 버전 0.8.143
~/.agents/skills/video-making/scripts/preflight.sh --node <node22-dir> --version 0.8.143
```

`--node`에는 풀어 둔 Node 22 폴더(`node-v22.x-linux-x64`)와 그 `bin` 폴더 중 아무거나 줘도 된다. node 실행 파일이 있는 쪽을 찾아 이번 점검의 `PATH` 앞에 붙인다.

`preflight.sh`는 **아무것도 설치하지 않는다.** Node 버전, npx, FFmpeg/ffprobe, Noto Sans CJK, Chrome 캐시 유무를 보고,
CLI가 npx 캐시에 이미 있을 때만 `hyperframes doctor`를 돌린다(`npx --no-install --offline`). 빠진 것이 있으면 목록과 설치 명령 **제안**만 출력하고 멈춘다.
판정은 마지막 `result:` 줄이다. `doctor`는 이 스킬에 필요 없는 선택 항목(Docker 데몬, 음성 인식·TTS·배경음 모델)이 없어도 `Some checks failed`를 출력한다. `preflight.sh`는 이것들을 `note doctor optional only: …`로 따로 적고 `result: ready`를 낸다. Docker 데몬은 `render --docker`를 쓸 때만 필요하다. (`doctor`는 최신 버전 확인에 네트워크를 쓸 수 있다. 사전 점검 단계라 괜찮다.)

- 빠진 의존성은 **사람에게 목록을 보여 주고 승인받은 뒤** 설치한다. CLI·Chrome·GSAP를 처음 받는 것(§7 「1회 받기」)도 같은 취급이다.
- 승인 없이 시스템 패키지·전역 npm 패키지를 설치하지 않는다.

### 환경별 메모

- **여러 에이전트가 함께 쓰는 Linux 머신:** 시스템 Node가 22보다 낮으면 시스템을 올리지 말고, 승인을 받아 Node 22 공식 tarball을 프로젝트 옆 폴더에 풀어 그 `bin`을 해당 셸의 `PATH` 앞에만 붙인다(체크섬 확인). Chrome 캐시는 사용자 홈 아래 하나를 공유한다.
- **macOS (Claude Code·Codex 등 로컬 에이전트):** `brew install node@22 ffmpeg`를 제안하고 승인을 받는다. keg-only인 `node@22`는 `PATH="$(brew --prefix node@22)/bin:$PATH"`로 해당 셸에만 붙인다. 한글 글꼴은 Noto Sans CJK KR을 설치하거나, 시스템 글꼴을 `@font-face local()`로 이름을 정확히 적어 쓴다.

### 환경 변수·네트워크

```bash
export HYPERFRAMES_NO_TELEMETRY=1    # 익명 사용 통계 끄기 (또는 npx --no-install --offline hyperframes@<버전> telemetry disable)
export HYPERFRAMES_SKIP_SKILLS=1     # init 이 GitHub에서 에이전트 스킬을 확인·설치하지 않게
```

- `init` 템플릿은 GSAP를 CDN에서 부른다. 이 스킬은 `init` 대신 `template/`을 복사하고, `build_timeline.py`가 만드는 HTML은 로컬 사본(`<script src="gsap.min.js">`)을 부른다.
- **GSAP를 이 저장소에 넣지 않는 이유:** GSAP는 「Standard 'no charge' license」로 무료지만, 이 라이선스는 허용된 용도의 사용·복제를 허락할 뿐 공개 저장소 재배포를 분명히 허락하지 않는다. 그래서 프로젝트마다 npm 패키지에서 꺼내 쓰고, 파일 머리의 라이선스 주석은 지우지 않는다.
- 렌더·검수 중에는 네트워크 자원(웹 글꼴, CDN 스크립트, 원격 이미지)을 쓰지 않는다. 자산은 모두 프로젝트 폴더에 둔다.
- 기계가 달라도 **바이트까지 같은** 결과가 필요하면 `render --docker`(Chromium·글꼴·FFmpeg 고정)를 쓴다. 같은 기계에서는 그냥 렌더해도 매번 같다.

## 3. 입력

- 원본: 설명할 대상의 실제 파일(스킬 문서, PR diff, 설정 파일, 설계 문서). **원격으로 읽고**, 화면에 쓸 주장마다 근거를 아래 표기로 메모한다
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
- 편집 판단(분류·강조·「후보」 표시 등)은 사실과 섞지 말고 「편집 판단」이라고 적는다.
- 작성자가 스토리보드를 승인하기 전에는 **최종 렌더를 하지 않는다**(시안 렌더는 괜찮다).

### 근거 표기

| 근거 종류 | 표기 | 예 |
|---|---|---|
| 저장소 파일 | `<저장소> · <경로>:<줄>` 또는 `<경로>:<시작>–<끝>`. 경로는 저장소 기준 상대 경로(내 기계의 절대 경로 금지), 여러 곳은 `,`로 | `example/repo · docs/flow.md:12–40`, `docs/flow.md:3,8` |
| 커밋·PR | 저장소 + 커밋 앞 7자리 또는 PR 번호 | `example/repo@1a2b3c4`, `example/repo#42` |
| Slack 메시지 | 메시지 퍼머링크 URL(Slack의 「링크 복사」). 채널 이름만 적지 않는다 | `Slack 퍼머링크: <메시지 링크>` |
| Notion 페이지 | 페이지 URL(블록이면 `#<블록>` 붙인 URL) | `https://www.notion.so/<페이지>` |
| 웹 문서 | URL | `https://gsap.com/standard-license` |
| 직접 측정 | `직접 측정 · <무엇> · <날짜>` | `직접 측정 · 재렌더 sha256 일치 · 2026-10-10` |

- 화면 아래 출처 줄은 짧은 표기(저장소 경로·문서 제목)로 쓰고, 전체 표기(퍼머링크·URL 포함)는 `claims-sources.md` 표(장면 | 화면 주장 | 근거)에 적어 영상과 함께 넘긴다.
- 퍼머링크·내부 URL이 공개 범위 제약에 걸리면 화면에는 넣지 않고 `claims-sources.md`에만 둔다.

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

`template/style.css`에 위 규칙(글꼴 선언, keep-all, 최소 글자 크기, 카드·흐름 상자·진행 막대, `.scene.center`, `.draft` 배지)이 들어 있다.

### 세로 정렬 — `.scene.center`

- 기본 `.scene`은 위에서부터 쌓는다(제목 위치가 장면마다 같다). 표·카드가 여러 줄인 장면에 맞다.
- 내용이 화면 높이의 절반 남짓밖에 안 차서 **아래 절반이 비는 장면**(표지, 한 문장 장면, 카드 한 줄)에는 스토리보드 장면에 `"class": "center"`를 준다. 세로 가운데 정렬하고, 아래 출처 줄과 겹치지 않게 아래 여백을 남긴다.
- 같은 구조의 장면이 이어지면 정렬도 같게 둔다. 장면마다 제목이 오르내리면 산만하다.
- 줄바꿈이 어색하면(라벨 아래로 내려간 첫 항목, 줄 끝에 홀로 남은 `·`) 폭을 넓히는 대신 `<br/>`로 끊을 곳을 정한다.

### 모든 장면에 보이는 요소 — `overlay`

초안 배지, 워터마크처럼 **영상 내내 같은 자리에 있어야 하는 것**은 장면 `body`마다 복사하지 말고 스토리보드 최상위 `overlay`에 한 번 쓴다.

```json
"overlay": "<div class='draft'>초안 · 정식 브리핑 아님</div>"
```

빌더는 이것을 장면 클립 밖, 위층(`#overlay`)에 시간 속성 없이 한 번 넣는다. 그래서 처음부터 끝까지 보이고, 움직이지 않고, 읽기 시간에 들어가지 않고, `check` 경고도 늘리지 않는다.

## 6. 장면 길이 — 다 보인 뒤에도 읽을 시간

장면 길이는 손으로 정하지 않고 `build_timeline.py`가 계산한다.

```
장면 길이 = max( 마지막 등장 시각 + 등장 애니메이션(0.5s) + 최소 유지(4.5s),
                 기본 1.5s + 글자량 / 읽기 속도 )
글자량    = 한글·한자 글자 수 × 1.0 + 그 밖의 공백 아닌 글자 수 × 0.5
읽기 속도 = 초당 15 (스토리보드에서 장면별 cps·hold로 조정 가능)
```

글자량에서 빼는 것: `class="source"`(출처 줄), `class="draft"`(배지), `data-no-read` 속성이 있는 요소와 그 안의 모든 글자, `overlay`. 보는 사람이 장면마다 다시 읽지 않는 글이라 길이를 늘리면 안 된다. 장식용 큰 숫자·반복 라벨처럼 읽을 필요가 없는 글에는 `data-no-read`를 붙인다.

- 모든 장면은 **다 나타난 뒤 최소 4.5초** 머문다. 지난 시안에서 마지막 줄이 나타나고 1–2초 만에 넘어간 장면이 지적을 받았다.
- 글이 많은 장면은 4.5초로도 부족하다는 리뷰를 받았다 → 글자량 항이 길이를 늘린다. 계산 결과가 20초를 넘으면 장면을 나눈다.
- 빌더는 장면마다 어느 규칙이 길이를 정했는지(`hold` / `read`)와 글자량을 표로 출력한다. 리뷰에서 "짧다"는 말이 나오면 cps를 낮춘다.

```bash
python3 ~/.agents/skills/video-making/scripts/build_timeline.py storyboard.json   # → index.html, timing.json
```

스토리보드 JSON 형식은 `template/storyboard.example.json`에 있다(최상위 선택 `overlay`, 장면별 `body`, `reveals: [[선택자, 앞 등장과의 간격]]`, 선택 `class`(`"center"`), `tweens`, `cps`, `hold`).

## 7. 렌더

**1회 받기 — 사람 승인 후, 네트워크는 여기서만.** 기계마다 한 번이면 되고, 이미 캐시에 있으면 건너뛴다(`preflight.sh`가 알려 준다).

```bash
npx --yes hyperframes@0.8.143 --version                  # CLI → npx 캐시
npx --no-install --offline hyperframes@0.8.143 browser ensure       # chrome-headless-shell → ~/.cache/hyperframes (약 260MB)
~/.agents/skills/video-making/scripts/vendor_gsap.sh <name> --fetch   # gsap@3.14.2 tarball → npm 캐시 → <name>/gsap.min.js
```

**프로젝트 준비 — 네트워크 없음.** `init`을 쓰지 않고 템플릿을 복사한다.

```bash
mkdir -p <name> && cp ~/.agents/skills/video-making/template/{style.css,hyperframes.json,package.json} <name>/
cp ~/.agents/skills/video-making/template/storyboard.example.json <name>/storyboard.json
~/.agents/skills/video-making/scripts/vendor_gsap.sh <name>   # npm 캐시에서 꺼내 sha256 확인 (캐시에 없으면 멈추고 --fetch 승인을 요청)
```

`vendor_gsap.sh`는 다른 프로젝트에 이미 있는 사본을 `--from <경로>`로 받을 수도 있다(sha256이 같을 때만).

**검사·렌더 — 네트워크 없음.** 모든 명령에 `--no-install --offline`을 붙인다. `--no-install`만으로는 부족하다: 패키지를 새로 받지는 않아도 npx가 버전을 확인하려고 레지스트리에 접속하고, 네트워크가 없으면 응답 없이 멈춘다(0.8.143, npm 10에서 확인). `--offline`이면 캐시만 보고, 캐시에 없으면 바로 실패한다.

```bash
npx --no-install --offline hyperframes@0.8.143 check                                   # 아래 QA 게이트 (= npm run check)
npx --no-install --offline hyperframes@0.8.143 render --quality high --fps 30 --output out/video.mp4   # (= npm run render)
```

- 참고 수치(8코어 Linux, 소프트웨어 GPU): 1080p 30fps 20초 예시 렌더 약 10초, 59초 영상 약 28초, 85초 영상 약 39초.
- 렌더는 `HeadlessExperimental.beginFrame`으로 프레임마다 한 번에 그린 화면을 받아 FFmpeg(image2pipe → libx264)로 넣는다. Chrome은 1회 받기의 `browser ensure`로 미리 받아 둔다.

## 8. QA 게이트 (보여 주기 전 필수)

1. **`hyperframes check` 오류 0건.** 경고는 읽고 판단한다. 아래 두 경고는 이 스킬의 한 파일 구조에서 늘 나오며 **무시해도 된다**:

   | 경고 코드 | 개수 | 왜 나오나 · 왜 무시하나 |
   |---|---|---|
   | `nested_structure_needs_subcomposition` | 장면 수만큼 | 장면 `<section>` 안에 요소가 들어 있으면 하위 컴포지션 파일로 나누라고 권한다. Studio 타임라인 편집용 권고이고 렌더 결과와는 무관하다 |
   | `timeline_track_too_dense` | 장면이 4개 이상이면 1건 | 한 트랙(`data-track-index="0"`)에 시간 요소가 3개를 넘으면 나온다. 장면은 겹치지 않고 차례로 나오므로 문제없다 |

   HyperFrames 0.8.143에는 특정 lint 규칙을 끄는 공식 방법(설정 파일 항목, CLI 플래그, 주석)이 없다. `check`·`lint`에 규칙 무시 옵션이 없고, `hyperframes.json`에도 lint 설정이 없다. 소스에도 일부 규칙은 의도적으로 끄는 방법을 두지 않는다고 적혀 있다. 그래서 위 두 코드 말고 다른 경고가 나오면 고친다. 같은 코드라도 Studio(`preview`)에서는 오류로 보일 수 있다.

   `check`는 **몇 시점만 표본으로 찍는다.** 잘못 놓인 요소, 상자 안에서 줄이 바뀐 제목, 단어 중간 끊김을 놓쳤다 → 2번이 반드시 필요하다.
2. **장면마다 다 나타난 프레임 한 장씩 직접 본다.**
   ```bash
   python3 ~/.agents/skills/video-making/scripts/extract_frames.py out/video.mp4 --timing timing.json --out out/qa --tag r1
   ```
   `<태그>-NN-<장면>-t<초>.png`와 함께 고정 이름 `frame-N.png`(N = 장면 번호)도 쓴다(`--no-stable`로 끔). 이미지 뷰어가 같은 경로를 캐시할 수 있으니 **검수는 태그 붙은 파일로** 하고 재렌더마다 `--tag`를 바꾼다. `frame-N.png`는 매번 덮어쓰므로 전달·문서 링크용이다. 장면마다 `통과 / 수정필요`:
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
  source: <컴포지션 폴더>          # index.html, storyboard.json, style.css, hyperframes.json, package.json(버전 고정), gsap.min.js
  frames: [out/qa/frame-1.png, out/qa/frame-4.png, out/qa/frame-7.png]   # 대표 장면 3장 (frame-N = 장면 N)
  claims: claims-sources.md      # 장면 | 화면 주장 | 근거 (§4 근거 표기)
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
- 렌더 중 네트워크 자원, `Date.now()`·시드 없는 난수, 1회 받기 뒤의 `npx --yes`(검사·렌더는 `--no-install --offline`)
- `gsap.min.js`를 이 저장소에 커밋하거나 머리의 라이선스 주석을 지우기
- 90초를 넘기는 한 편짜리 영상, 영상만으로 문서를 대신하기
