---
name: weekly-lesson-publish
description: >-
  Use when publishing an author-approved weekly lesson draft to a personal GitHub Pages (Jekyll-style) blog repository, after the weekly-lesson-draft review gate — never before explicit human approval.
---
# 주간 교훈 블로그 발행

작성자가 **승인한** 주간 교훈 초안만 GitHub Pages 블로그 저장소에 올린다. 초안·말투·교훈 타당성 심사는 `weekly-lesson-draft` 스킬이, 그림은 `image-making` 스킬(용도 `blog`)이 담당한다.

## Preconditions (하나라도 없으면 여기서 멈춘다)
1. 초안 스킬의 **작성자 1:1 리뷰 게이트**를 통과했다(승인 문구가 있음). 이미지가 있으면 채택된 장만.
2. 대상 저장소·브랜치·Pages 소스가 확인됐다(기본: 개인 `dev-articles`류 공개 저장소, `main` 루트 또는 합의된 경로).
3. 공개 필터가 최종본에도 유지됐다(회사·제품·내부 ID·실명·미공개 수치 없음).

## Hard rules
1. **승인 없는 커밋·푸시·Pages 배포 금지.** 초안만 있는 상태에서는 발행하지 않는다.
2. **초안 재작성 금지.** 발행 단계에서 문장·교훈·그림을 고치지 않는다. 고칠 게 보이면 초안·이미지 스킬로 되돌린다.
3. **저장소 좌표는 루틴·대화 컨텍스트에서 받는다.** 스킬 본문에 특정 owner/repo를 하드코딩하지 않는다.
4. **디자인·테마 대공사 금지.** 기존 `_config.yml`·테마·레이아웃을 유지하고, 글·assets만 추가한다. 테마 변경은 별도 요청일 때만.
5. **소셜 공유·외부 알림은 기본 off.** 작성자가 명시할 때만.

## Publish steps
1. 승인된 초안 전문·제목·날짜(또는 slug)·채택 이미지 목록을 확인한다.
2. 저장소의 글·assets 경로 규칙을 읽는다(예: `_posts/…`, `assets/` 또는 `assets/YYYY-MM-DD/`).
3. front matter는 저장소 관례를 따른다. 보통 `title`, `date`.
4. 본문은 승인본을 그대로 넣는다. 이미지 마크다운 경로는 저장소 상대 경로로 맞춘다. 비서 말투·세 패스 표는 넣지 않는다.
5. 채택된 이미지 파일을 같은 커밋/PR에 포함한다.
6. 저장소 쓰기는 런타임이 허용하는 방식(로컬 clone·원격 에이전트·API)으로 한다. 기본은 짧은 PR → 작성자 머지, 작성자가 「바로 main」이라고 하면 그에 맞춘다.
7. Pages URL이 200이거나 빌드 성공한 뒤에만 「발행 완료」라고 한다.
8. **(선택) 발행 지표 기록.** 작성자가 발행 기록용 로그(예: 주간 달성 로그 DB·스프레드시트)를 쓴다면, 발행 성공 직후 해당 주(`YYYY-Www`) 행에 아래 값을 채운다. 로그 위치·필드 이름은 루틴·대화 컨텍스트에서 받고, 스킬 본문에 하드코딩하지 않는다. 로그가 없으면 이 단계는 건너뛴다.
   - `published` = yes · `post_url` = Pages 글 URL
   - `publish_streak_days` = 연속 발행일(당일 기준; 끊기면 1부터)
   - `candidate_publish_rate` = 그 주 공개 후보 대비 실제 발행 비율(0–100)
   - `days_to_publish` = 회고일→발행일 지연 일수(당일이면 0)
   - 그 주 행이 없으면 로그의 필수 필드만 채워 새로 만들고, 주간 판정 루틴이 나중에 덮어쓸 수 있게 둔다

## Out of scope
- 초안·이미지 작성·작성자 리뷰
- 저장소 최초 생성·테마 선정
- SEO 대공사, 커스텀 도메인, 뉴스레터
- SEO 조회·숏폼 영상 등 발행 이후 지표
