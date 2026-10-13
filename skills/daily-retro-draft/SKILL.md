---
name: daily-retro-draft
description: >-
  Use when drafting the user's daily retrospective from what actually happened that day —
  observe their chat messages and local agent/worktree activity, group by project, propose
  lesson candidates, and record a draft page in the retrospective database for the user to
  answer. Finalizes lessons only from the user's replies; hands publishable lessons to
  weekly-lesson-draft. Database and source locations come from the runtime's instructions.
---

# 일일 회고 초안

하루 동안 실제로 있었던 일을 관측해 회고 초안을 만들고, 사용자의 답으로 교훈을 확정한다. 블로그 초안·발행은 `weekly-lesson-draft`·`weekly-lesson-publish`가 맡는다.

## Inputs (런타임 지침에서 받는다)
- 회고 DB 위치(속성: `이름`, `날짜`, `프로젝트`, `공개 여부`, `블로그 연결`, `확정 교훈`, `주간 행`)
- 관측 대상: 사용자의 채팅 활동(사용자가 쓴 메시지와 사용자를 언급한 메시지), 로컬 작업 내역(에이전트 작업 관리 도구의 worktree 목록과 각 저장소의 그날 커밋)
- 사용자 본인 채팅 채널(질문을 보낼 곳)
- 대상 날짜(기본: 오늘, KST)

## Hard rules
1. **활동이 없으면 만들지 않는다.** 관측 결과가 비면 페이지를 만들지 않고 「오늘 관측된 활동 없음」만 보고한다.
2. **같은 날짜 페이지는 하나.** 이미 있으면 새로 만들지 않고 그 페이지에 덧붙인다.
3. **교훈은 사용자가 확정한다.** 에이전트는 「교훈 후보」만 쓴다. `확정 교훈`은 사용자 답을 받은 뒤에만 채운다.
4. **사용자 답은 원문 그대로.** 받은 시각과 함께 `## 원문`에 그대로 옮긴다.
5. **근거 없는 일반론 금지.** 후보마다 근거 링크(메시지, 커밋, 문서)를 붙인다.

## Steps
1. **관측.**
   - 채팅: 대상 날짜에 사용자가 쓴 메시지와 사용자를 언급한 메시지를 찾는다. 스레드면 부모까지 읽는다.
   - 로컬 작업: worktree 목록을 보고, 각 저장소에서 `git log --since="<날짜> 00:00" --until="<날짜> 23:59" --author=<사용자>`로 그날 커밋을 모은다.
2. **프로젝트별로 묶는다.** 회고 DB `프로젝트` 속성의 기존 옵션 이름을 우선 쓰고, 맞는 게 없으면 새 이름을 쓴다.
3. **페이지를 만든다.** 속성: `이름 = YYYY-MM-DD 회고`, `날짜`, `프로젝트`, `공개 여부 = 질문 중`, `블로그 연결 = 미정`, 이번 주 `주간 행` 연결. 본문:
   - `## 원문` — 비워 둔다(사용자 답이 여기에 쌓인다).
   - `## 근거 링크` — 프로젝트별 출처 목록.
   - `## 정리` — 프로젝트별 한두 줄: 무엇이 진행됐고 무엇이 결정됐는지, 결정 대기는 무엇인지.
   - `## 교훈 후보` — `L1`, `L2` … 각 후보는 한 문장 결론 + 왜 그렇게 보는지 + 근거 링크.
4. **사용자에게 묻는다.** 사용자 본인 채팅으로 `🤖`로 시작하는 메시지에 페이지 링크와 질문을 담아 보낸다: 후보별로 맞는지·고칠지·뺄지, 공개해도 되는지.
5. **답을 받으면 확정한다.** 답을 `## 원문`에 시각과 함께 옮기고, 후보를 확정·수정·제외 표시한 뒤 `확정 교훈`에 확정본을 쓴다. `공개 여부`는 사용자 답대로 바꾼다(`예`/`아니오`/`나중에`).
6. **블로그로 넘긴다.** `공개 여부 = 예`이고 사용자가 블로그로 쓰자고 하면 `블로그 연결 = 예`로 바꾸고 `weekly-lesson-draft`로 넘긴다.

## Out of scope
- 블로그 초안 작성·발행(`weekly-lesson-draft`·`weekly-lesson-publish`)
- 주간 갭 선정·판정
