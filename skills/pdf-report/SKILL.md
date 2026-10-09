---
name: pdf-report
description: >-
  Use when building a human-facing PDF report or deck with Slidev (weekly briefings, one-off ops or
  policy shares) — keep it self-contained (glossary, sources, appendix), call the image-making skill
  for any figure, export to PDF, render every page to PNG, and run the page-level visual self-QA
  before attaching or sharing the file.
---

# PDF 보고서 제작 (Slidev → PDF · 자가완결 · 페이지 셀프검수)

사람이 읽을 Slidev→PDF를 만들고, 붙이거나 올리기 **전에** 검수한다. **만들기 → 내보내기 → PNG 렌더 → 검수 → 고치기**를
전 페이지가 통과할 때까지 돌리고, 통과본만 첨부·공유한다. 미통과본은 "초안"이라고 표시하거나 아예 보내지 않는다.

이 스킬이 맡는 것: 문서 구성, 자가완결성(용어·출처·부록), 내보내기, 페이지 단위 검수, 전달.
그림 한 장을 만드는 일(수단·비율·폰트·정렬·그림 단위 QA)은 [`image-making`](../image-making) 스킬이 맡는다.

## 1. 시각자료는 이미지 스킬로
- 차트·다이어그램·플로우가 필요하면 `image-making`을 용도 `pdf-figure`로 호출한다. 슬롯(페이지·의도)과 담을 숫자를 넘기고, Self-QA를 통과한 그림과 alt를 받는다.
- 그 스킬의 `pdf-figure` 설정을 따른다: mermaid 금지, 숫자·플로우는 HTML/CSS, 생성 이미지로 숫자를 그리지 않음, Noto Sans CJK, 본문 영역 ≥70%.
- 단순한 표는 슬라이드에 바로 쓴다. 다이어그램은 **플로우가 머릿속에 안 그려질 때만** 넣는다.
- 그림을 넣은 뒤 페이지 단위 검수(§6)는 이 스킬에서 다시 한다.

## 2. 준비 (한 번)

```bash
cp -r ~/.agents/skills/pdf-report/template my-deck && cd my-deck
npm install                       # @slidev/cli · @slidev/theme-default · playwright-chromium
npx playwright install chromium   # export 가 쓰는 헤드리스 브라우저
```

- 시스템 도구: `pdftoppm`·`pdfinfo`(poppler-utils), Python 3 + Pillow(`pip install pillow`).
- 한글 글꼴: **Noto Sans CJK KR** 가 시스템에 설치돼 있어야 한다(`fc-list | grep -i "Noto Sans CJK"`).
  템플릿은 `fonts.provider: none` 이라 웹 글꼴을 내려받지 않는다 — 없으면 대체 글꼴로 조용히 바뀌어 줄바꿈이 달라진다.
- 검증된 조합: `@slidev/cli` 53 · `playwright-chromium` 1.63 · Node 20+.

## 3. 문서 형식

| 규칙 | 이유 |
|---|---|
| **고정 16:9 캔버스**(`aspectRatio: 16/9`, `canvasWidth: 980`). 장마다 높이가 다른 문서처럼 쓰지 않는다 | PDF 한 장 = 슬라이드 한 장. 넘치면 잘린다 |
| **첫 장에 한 줄 요약** | 독자가 첫 장만 봐도 결론을 안다 |
| 사람이 읽는 문장. 긴 로그·덤프 슬라이드 금지 | 근거가 길면 부록으로 |
| 단계가 3개 이상이면 **좌→우** 또는 2단, 본문 **≥14px** | 세로로 길게 쌓으면 글자가 작아지거나 잘린다 |
| 링크는 **라벨 링크**(`[설계 문서](https://…)`) | 원시 URL 벽은 읽히지 않고 PDF 에서 줄바꿈이 깨진다 |
| 표지·전면 장은 `layout: none` + 절대 위치 컨테이너 | 기본 레이아웃 패딩·제목 스타일을 피한다 |
| **마지막은 부록**(§7) | 용어·출처·긴 근거표를 본문에서 뺀다 |

템플릿(`template/slides.md`, `template/styles/index.css`)에 표지·2열 비교·좌→우 흐름도·표·부록 용어표 예시가 있다.

## 4. 자가완결성 — 용어 (첨부 전 필수)
PDF 만 받은 사람이 **이 문서 밖의 맥락 없이** 읽어도 뜻을 알 수 있어야 한다.
1. 본문·표·그림에서 팀 내부 약어·운영 용어·채널명·역할 이름을 목록으로 뽑는다.
   `preflight.py --jargon` 이 대문자 약어·괄호 밖 영문 토큰 후보를 뽑아 준다(후보일 뿐, 최종 판단은 사람이 읽고 한다).
2. 각 용어가 **첫 등장 근처에 한 줄 정의**가 있거나 **부록 「용어」 표**에 행이 있는지 확인한다.
- [ ] 미정의 내부어 0건
- [ ] 용어가 1개라도 있으면 「부록 — 용어」(용어 | 뜻)
- [ ] 본문에 새 용어를 넣었으면 부록도 같이 갱신
- [ ] 부록 설명이 길어지면 본문을 쉬운 말로 바꿔 용어 자체를 줄인다

## 5. 자가완결성 — 출처
- [ ] 숫자·인용·사실 주장마다 출처가 있다. 본문에는 **라벨 링크**(예: Issue #123, 문서 이름)로 달고 raw URL 벽을 만들지 않는다
- [ ] PDF로 인쇄하면 링크가 안 보일 수 있으므로, 출처가 3개 이상이면 「부록 — 출처」표(항목 | 출처 이름 | URL)를 둔다
- [ ] GitHub Issue·PR은 하이퍼링크
- [ ] 출처 없는 수치는 넣지 않거나 「출처 없음」을 밝힌다

## 6. 내보내기 + 페이지 단위 시각 검수 (첨부 전 필수)

```bash
~/.agents/skills/pdf-report/scripts/build.sh slides.md out/deck.pdf
```

`build.sh` 가 하는 일:
1. `preflight.py` — mermaid 금지, (있으면) `forbidden-terms.txt` 금지어, 원시 URL 검사. 실패하면 export 하지 않는다.
2. `npx slidev export <slides> --output <pdf> --timeout 120000`
3. `pdftoppm -png -r 144 <pdf> <out>/png/p` — 전 페이지 PNG
4. `pdfinfo` 로 페이지 수·크기 출력
5. `qa_pages.py` — 페이지별 가장자리 잉크(잘림 의심)·콘텐츠 채움 비율(과여백 의심) 수치와 4장씩 묶은 대조 시트(`out/qa/sheet-N.png`)

`qa_pages.py` 수치는 **의심 목록**일 뿐이다. 판정은 PNG 를 직접 열어 본다(시트 → 의심 페이지 원본 순서).
페이지마다 `통과 / 수정필요` 로 적는다.
- [ ] **잘림·겹침** 없음 — 글자·박스가 캔버스 밖으로 나가거나 서로 덮지 않는다(가장자리 잉크 경고 페이지 우선)
- [ ] **밀도** — 다이어그램 장은 본문 영역의 ≥70%를 쓴다. 그래픽이 가운데에만 작게 있으면 수정필요(채움 비율 경고 페이지 우선)
- [ ] **글자 크기·대비** — ≥14px 상당, 옅은 회색 글자도 읽힌다
- [ ] **그림** — 들어간 그림이 `image-making` Self-QA를 통과한 파일인지
- [ ] **생성 이미지에 숫자·지표 없음**

## 7. 부록
- 「부록 — 용어」(§4), 「부록 — 출처」(§5) 필요 시
- 본문에 넣기엔 길지만 근거로 필요한 표

## 8. 고치기 루프 · 전달
1. `slides.md` HTML/CSS 수정 — `width:100%`, `gap`, `font-size↑`, `padding`, 불필요한 마진↓, 단계 줄이기, 장 나누기. 그림 자체 문제면 `image-making`으로 되돌린다
2. `build.sh` 재실행 → PNG 재판정
3. **전 페이지 통과 후에만** 첨부·공유
4. QA 노트를 남긴다(예: `out/qa/QA-NOTE.md`): 페이지 수, 수정필요였던 페이지와 고친 내용, 용어 스캔 결과·부록 행 수, 출처 수, 금지어 검사 결과
5. 전달 전 `pdfinfo`로 페이지 수·크기를 한 번 더 확인하고, 파일 자체를 첨부한다

### 공개 범위
- [ ] 받는 사람이 보면 안 되는 내부 정보(사람 이름·일정 사유·내부 ID·경로·비공개 결정)가 없다.
  프로젝트별 금지어는 덱 폴더의 `forbidden-terms.txt`(한 줄에 정규식 하나)에 두면 preflight 가 막는다. 그 파일은 공개 저장소에 올리지 않는다.
- 정기 보고서(주간 브리핑 등)처럼 형식이 정해진 문서는 골격·금지어 목록을 덱 폴더에 따로 두고 이 스킬의 절차를 그대로 쓴다.

## Do not
- 미통과본을 최종본처럼 첨부하기
- 스크린샷 한두 장만 보고 "전 페이지 통과"라고 하기
- 그림을 이 스킬 안에서 즉석으로 그리기 — `image-making`을 거친다
- mermaid·생성 이미지로 숫자·흐름 그리기
- 출처 없는 숫자를 본문에 넣기
- `forbidden-terms.txt` 같은 내부 금지어 목록을 공개 저장소에 커밋하기
