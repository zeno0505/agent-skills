---
name: slidev-pdf
description: >-
  Use when building a human-facing PDF deck with Slidev (reports, one-off shares, briefings) —
  author fixed 16:9 slides with HTML/CSS diagrams, export to PDF, render every page to PNG, and
  run a visual self-QA harness (clipping, overlap, density/margins, type size, direction,
  contrast) plus a jargon scan with a glossary appendix before attaching or sharing the file.
---

# Slidev → PDF (작성 · 내보내기 · 시각 셀프검수)

사람에게 보낼 PDF를 Slidev로 만들 때 쓴다. **만들기 → 내보내기 → PNG 렌더 → 시각 검수 → 고치기**를
전 페이지가 통과할 때까지 돌리고, 통과본만 첨부·공유한다. 미통과본은 "초안"이라고 표시하거나 아예 보내지 않는다.

## 0. 준비 (한 번)

```bash
cp -r ~/.agents/skills/slidev-pdf/template my-deck && cd my-deck
npm install                       # @slidev/cli · @slidev/theme-default · playwright-chromium
npx playwright install chromium   # export 가 쓰는 헤드리스 브라우저
```

- 시스템 도구: `pdftoppm`·`pdfinfo`(poppler-utils), Python 3 + Pillow(`pip install pillow`).
- 한글 글꼴: **Noto Sans CJK KR** 가 시스템에 설치돼 있어야 한다(`fc-list | grep -i "Noto Sans CJK"`).
  템플릿은 `fonts.provider: none` 이라 웹 글꼴을 내려받지 않는다 — 없으면 대체 글꼴로 조용히 바뀌어 줄바꿈이 달라진다.
- 검증된 조합: `@slidev/cli` 53 · `playwright-chromium` 1.63 · Node 20+.

## 1. 작성 규칙

| 규칙 | 이유 |
|---|---|
| **고정 16:9 캔버스**(`aspectRatio: 16/9`, `canvasWidth: 980`). 장마다 높이가 다른 문서처럼 쓰지 않는다 | PDF 한 장 = 슬라이드 한 장. 넘치면 잘린다 |
| 다이어그램은 **HTML/CSS**(flex/grid 박스·화살표) 또는 표 | mermaid 는 export 에서 빈 그림으로 나오는 경우가 있다. 템플릿 preflight 가 막는다 |
| **숫자·차트·흐름도를 이미지 생성 모델로 그리지 않는다** | 생성 이미지는 숫자·글자를 틀리게 그린다. 차트는 표나 CSS 막대로 |
| 단계가 3개 이상이면 **좌→우** 또는 2단 | 세로로 길게 쌓으면 글자가 작아지거나 잘린다 |
| 본문 **≥14px**, 다이어그램 핵심 라벨은 더 크게 | PDF 를 화면 축소로 볼 때도 읽혀야 한다 |
| 다이어그램이 **본문 영역의 대부분(≈70% 이상)** 을 쓰게 | 작은 그림이 가운데 떠 있으면 읽히지 않는다 |
| 링크는 **라벨 링크**(`[설계 문서](https://…)`) | 원시 URL 벽은 읽히지 않고 PDF 에서 줄바꿈이 깨진다 |
| 문장은 쉬운 말, 내부 약어는 첫 등장에 한 줄 풀이 또는 부록 용어표 | PDF 만 받은 사람이 맥락 없이 읽는다(§4 G) |
| 표지·전면 장은 `layout: none` + 절대 위치 컨테이너 | 기본 레이아웃 패딩·제목 스타일을 피한다 |

템플릿(`template/slides.md`, `template/styles/index.css`)에 표지·2열 비교·좌→우 흐름도·표·부록 용어표 예시가 있다.

## 2. 내보내기 + 렌더

```bash
~/.agents/skills/slidev-pdf/scripts/build.sh slides.md out/deck.pdf
```

`build.sh` 가 하는 일:
1. `preflight.py` — mermaid 금지, (있으면) `forbidden-terms.txt` 금지어, 원시 URL 검사. 실패하면 export 하지 않는다.
2. `npx slidev export <slides> --output <pdf> --timeout 120000`
3. `pdftoppm -png -r 144 <pdf> <out>/png/p` — 전 페이지 PNG
4. `pdfinfo` 로 페이지 수·크기 출력
5. `qa_pages.py` — 페이지별 가장자리 잉크(잘림 의심)·콘텐츠 채움 비율(과여백 의심) 수치와 4장씩 묶은 대조 시트(`out/qa/sheet-N.png`)

## 3. 시각 셀프검수 (첨부 전 필수)

`qa_pages.py` 수치는 **의심 목록**일 뿐이다. 판정은 PNG 를 직접 열어 본다(시트 → 의심 페이지 원본 순서).
페이지마다 `통과 / 수정필요` 로 적는다.

### F. 시각
- [ ] **잘림** 없음 — 글자·박스가 캔버스 밖으로 나가거나 아래가 잘리지 않는다(가장자리 잉크 경고 페이지 우선 확인)
- [ ] **겹침** 없음 — 박스·글자·화살표가 서로 덮지 않는다
- [ ] **여백·밀도** — 다이어그램 장에서 상하좌우가 텅 비고 그래픽이 작게 가운데 있으면 수정필요. 채움 비율 경고 페이지 우선 확인
- [ ] **글자 크기** — 다이어그램 안 한글이 작아 흐리면 수정필요(글자·패딩을 키우거나 단계를 줄인다)
- [ ] **방향** — 단계 ≥3 이면 좌→우 또는 2단
- [ ] **대비** — 옅은 회색 글자·배경 위 글자가 충분히 읽힌다
- [ ] **생성 이미지에 숫자·지표 없음**

### G. 용어·자가완결
PDF 만 받은 사람이 **이 문서 밖의 맥락 없이** 읽어도 뜻을 알 수 있어야 한다.
1. 본문·다이어그램·표에서 팀 내부 약어·운영 용어·채널명·역할 이름을 목록으로 뽑는다.
   `preflight.py --jargon` 이 대문자 약어·괄호 밖 영문 토큰 후보를 뽑아 준다(후보일 뿐, 최종 판단은 사람이 읽고 한다).
2. 각 용어가 **첫 등장 근처에 한 줄 정의**가 있거나 **부록 「용어」 표**에 행이 있는지 확인한다.
- [ ] 미정의 내부어 0건
- [ ] 용어가 1개라도 있으면 마지막에 「부록 — 용어」(용어 | 뜻)
- [ ] 본문에 새 용어를 넣었으면 부록도 같이 갱신
- [ ] 부록 설명이 길어지면 본문을 쉬운 말로 바꿔 용어 자체를 줄인다

### 공개 범위
- [ ] 받는 사람이 보면 안 되는 내부 정보(사람 이름·일정 사유·내부 ID·경로·비공개 결정)가 없다.
  프로젝트별 금지어는 덱 폴더의 `forbidden-terms.txt`(한 줄에 정규식 하나)에 두면 preflight 가 막는다. 그 파일은 공개 저장소에 올리지 않는다.

## 4. 고치기 루프

1. `slides.md` HTML/CSS 수정 — `width:100%`, `gap`, `font-size↑`, `padding`, 불필요한 마진↓, 단계 줄이기, 장 나누기
2. `build.sh` 재실행 → PNG 재판정
3. **전 페이지 통과 후에만** 첨부·공유
4. QA 노트를 남긴다(예: `out/qa/QA-NOTE.md`): 페이지 수, 수정필요였던 페이지와 고친 내용, 용어 스캔 결과·부록 행 수, 금지어 검사 결과

## Do not
- 미통과본을 최종본처럼 첨부하기
- 스크린샷 한두 장만 보고 "전 페이지 통과"라고 하기
- mermaid·생성 이미지로 숫자·흐름 그리기
- 다이어그램을 작게 줄여 가운데만 두기
- `forbidden-terms.txt` 같은 내부 금지어 목록을 공개 저장소에 커밋하기
