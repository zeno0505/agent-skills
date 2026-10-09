---
name: image-making
description: >-
  Use when any deliverable needs a figure or summary card — blog post figures, a summary card at the
  top of a report, a diagram or chart inside a PDF/slide deck. Pick the medium and aspect ratio for
  the destination, render with code, and pass a per-image self-QA before anyone sees it. Called by
  other skills (weekly-lesson-draft, pdf-report, report publishers); never for ad-hoc decoration.
---
# 이미지 제작

글·리포트·PDF에 들어갈 **그림 한 장 한 장**을 만들고 검수한다.

이 스킬이 맡는 것: 그림의 수단·비율·폰트·레이아웃, 그림 단위 Self-QA.
이 스킬이 맡지 않는 것: 글 본문·말투, 문서 전체의 구성·자가완결성·출처 표기·부록(→ [`pdf-report`](../pdf-report) 스킬이나 각 글 스킬), 발행·커밋.

호출하는 쪽: [`weekly-lesson-draft`](../weekly-lesson-draft), [`pdf-report`](../pdf-report), 주간 리포트를 올리는 스킬 등. 호출하는 스킬이 **용도**와 **슬롯**을 넘긴다.

## Inputs
- 용도: `blog` / `report-card` / `pdf-figure` 중 하나 (아래 용도별 설정 표)
- 슬롯: 한 줄 의도 + 넣을 위치(섹션 위/아래, 페이지 번호)
- 담을 내용: 숫자·단계·비교 항목. 숫자는 출처에서 받은 값만 쓴다
- 공개 범위 제약: 호출 스킬이 정한 금지 항목(실명, 내부 ID, 미공개 수치 등)

## 용도별 설정

| 항목 | blog (블로그 그림) | report-card (리포트 맨 위 요약 카드) | pdf-figure (PDF·슬라이드 안 그림) |
|---|---|---|---|
| 비율 | 직사각형 1:1~4:3, 최대 ~3:2. 배너형 금지 | 16:9 한 장 | 슬라이드 본문 영역(16:9 캔버스 안)에 맞춤 |
| 캔버스 너비 | 고정 금지. 콘텐츠 최소 폭 + 마진 | 16:9 고정 | 슬라이드 폭 기준, 본문 영역 ≥70% 채움 |
| mermaid | 허용(1순위) | 쓰지 않음. HTML/CSS 표·칩·막대 | **금지**. HTML/CSS로 |
| 공개 필터 | 엄격: 제품 UI·회사명·실명·내부 ID·미공개 수치 금지, 추상 목업으로 대체 | 내부 열람용. 개인정보·비밀값만 금지 | 문서 독자 범위를 따름(호출 스킬이 지정) |
| 분량 | 글당 1~3장, 슬롯 없으면 「이미지 없음」 | 리포트당 1장 | 플로우가 머릿속에 안 그려질 때만 |

새 용도가 생기면 이 표에 열을 추가한다. 용도를 모르면 호출 스킬에 묻지 말고 가장 가까운 열을 쓰고 보고에 적는다.

## Hard rules
1. **장식용 금지.** 내용을 설명하지 않는 분위기 이미지는 만들지 않는다.
2. **수단 우선순위** (앞에서 되면 뒤는 쓰지 않는다. 용도 표의 mermaid 칸이 우선):
   1. 코드로 그리는 도식: mermaid / SVG / HTML·CSS
   2. Slidev 한 장 → PNG ([`pdf-report`](../pdf-report)의 템플릿·`build.sh` 재사용)
   3. 이미지 생성 모델: 개념도·아이콘 수준만
3. **숫자·차트·표·플로우는 반드시 코드로.** 생성 이미지로 숫자를 그리지 않는다.
4. **폰트:** 기본 **Noto Sans CJK** (`NotoSansCJK-Regular.ttc` / `NotoSansCJK-Bold.ttc`, index 0). 요청자가 바꾸기 전까지 다른 글꼴로 바꾸지 않는다.
5. **카드·박스 세로 정렬.** 카드·패널 안 텍스트·배지·아이콘 묶음은 세로 중앙. 상·하 패딩 대칭. PIL에서는 콘텐츠 높이로 센터 오프셋을 계산한다.
6. **과여백 금지.** 카드는 콘텐츠에 맞춘다(패딩 16–28px, 바깥 마진 24–40px). 고정 큰 박스에 글만 넣는 방식 금지.
7. **가독성.** 그림 안 글자 ≥14px 상당, 핵심 라벨은 더 크게. 단계 ≥3이면 좌→우 또는 2단. 한글 단어가 한 줄에 한 단어만 남거나 단어 중간에서 끊기지 않게 한다.
8. **그림 안 용어.** 그림만 봐도 뜻이 통해야 한다. 내부 약어가 그림에 남으면 그림 안 각주로 한 줄 풀거나 쉬운 말로 바꾼다.
9. **초안만.** 커밋·배포·발행은 하지 않는다. 결과는 파일 경로로 호출 스킬에 넘긴다.

## Self-QA (보여주기 전에 매 장 필수)
렌더한 PNG를 직접 열어 확인한다. 하나라도 실패하면 고치고 다시 렌더한다. 요청자에게 여백·정렬·비율을 물으며 반복하지 않는다.

| # | 검사 | 실패 시 |
|---|------|--------|
| A | 폰트 = Noto Sans CJK (지정 변경 없을 때) | 재렌더 |
| B | 잘림·겹침 없음 | 폭·줄바꿈 조정 후 재렌더 |
| C | 카드 안 세로 중앙 · 상단≈하단 패딩 | 센터 재계산 |
| D | 과여백 없음 · 밀도 적정 (`pdf-figure`는 본문 영역 ≥70%) | 크기·패딩 조정 |
| E | 비율·mermaid 사용이 용도별 설정과 일치 | 레이아웃 변경 |
| F | 글자 ≥14px · 대비 충분 · 단어 고립/중간 끊김 없음 | 폰트·폭 조정 |
| G | 숫자는 출처 값과 일치 · 생성 이미지로 그린 숫자 없음 | 코드로 다시 그림 |
| H | 공개 필터 통과 · 그림 안 미정의 내부어 0건 | 추상화·각주 |
| I | alt + 삽입 위치 준비됨 | 보완 |

렌더 회차와 실패 사유는 QA 메모로 남긴다(호출 스킬이 정한 위치, 없으면 그림 옆 `qa.md`).

## Steps
1. 용도와 슬롯을 확인한다. 슬롯이 없으면 슬롯 후보만 제안하고 멈춘다.
2. 용도별 설정과 우선순위로 수단을 고른다.
3. 콘텐츠 폭·높이를 먼저 잰 뒤 캔버스·카드를 잡고 렌더한다. 파일명 `YYYY-MM-DD-<slug>-NN.png`.
4. Self-QA A–I를 장마다 통과시킨다.
5. 통과분에 alt·삽입 위치·마크다운을 붙여 호출 스킬로 돌려보낸다.

## Output shape
```
- slot: <섹션 제목 또는 페이지>
  purpose: blog | report-card | pdf-figure
  path: <local file>
  alt: "…"
  insert_after: <heading 또는 페이지>
  markdown: "![…](…)"
  self_qa: pass  # A–I, 렌더 N회
```

## 용도별 참고
- **blog:** `weekly-lesson-draft`가 슬롯을 정한 뒤 호출한다. 작성자 리뷰는 내용·넣을지 여부에만 집중하게 하고, 레이아웃은 Self-QA에서 끝낸다. 작성자 탈락분은 버린다.
- **pdf-figure:** `pdf-report`가 호출한다. 그림을 받은 뒤 페이지 단위 검수(잘림·밀도·용어 부록)는 PDF 스킬이 다시 한다.
- **report-card:** 리포트(슬랙·노션 등) 맨 위에 두는 요약 한 장. 상태 칩·숫자 표·한 줄 요약 정도로 제한한다.

## Out of scope
- 글·문서 본문 재작성, 문서 전체 구성, 출처·부록
- 테마/CSS 대공사, OG 이미지 SEO 최적화
- 승인 없는 커밋·푸시·발행
