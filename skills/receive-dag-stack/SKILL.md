---
name: receive-dag-stack
description: Use when a subagent is dispatched by run-dag-stack to implement, resume, fix, or review one task from a dag.yaml plan; the subagent-side execution contract (append-only implementation.md, commit only, never push)
---

# Receive DAG Stack

서브에이전트가 DAG 태스크 하나를 받을 때 사용하는 실행 계약이다. 오케스트레이터 쪽 짝은 `run-dag-stack` 이다.

**Core principle:** 작업을 시작하기 전에 재개 가능한 기록을 남긴다. 세션 만료, 사용량 제한, 재파견이 발생해도 다음 에이전트가 같은 맥락으로 이어야 한다.

## When to Use

- `run-dag-stack`이 구현, 리뷰, 리뷰 수정, 재개 작업을 맡겼을 때
- 오케스트레이터가 여러 태스크를 한 번에 묶은 통합 구현 또는 fix-mode 재개 작업을 맡겼을 때 (Integration Mode 절 참조)
- `assignment.md`, `implementation.md`, `review-N.md` 중 하나를 입력으로 받았을 때
- 한 태스크의 worktree, branch, PR, review loop를 이어야 할 때

## Files

```text
{note_dir}/inbox/{task_id}/assignment.md      # 오케스트레이터가 만든 작업 패킷
{note_dir}/inbox/{task_id}/implementation.md  # 구현 에이전트 append-only 기록
{note_dir}/inbox/{task_id}/review-1.md        # 리뷰 에이전트 결과
{note_dir}/inbox/{task_id}/review-2.md
{note_dir}/inbox/{task_id}/review-3.md
{note_dir}/inbox/{task_id}/final.md           # 오케스트레이터 전용
```

## Implementation Mode

1. `assignment.md`를 먼저 읽는다.
2. 기존 `implementation.md`가 있으면 새 작업이 아니라 resume으로 본다.
3. 코드 수정 전에 `implementation.md`에 새 attempt를 append한다.
4. 기록할 필수 필드: `started_at`, `branch`, `worktree`, `base_commit`, `status`, `plan`.
5. 현재 태스크 하나만 구현하고 `target_files` 범위를 우선 지킨다.
6. 탐색, 수정, 검증, 커밋 후 `## Checkpoints`에 append한다.
7. 검증 명령과 결과를 `## Verification`에 남긴다.
8. **커밋까지가 끝이다.** 푸시하지 않고, PR을 만들지 않는다 — 커밋 해시를 `## Commits`에
   남기고 오케스트레이터에게 보고한다. 회차 마감은 누적 diff 실측으로 정해지는데, 태스크
   하나만 보는 서브에이전트는 그 정보를 갖고 있지 않다.
9. 브라우저로만 확인 가능한 것이 있으면 `{note_dir}/e2e-checklist.md` 에
   `- [ ] [T-XXX] 확인할 것` 형식으로 줄을 추가한다. 직접 검수하지는 않는다.
10. 중단 가능성이 있거나 막히면 마지막에 `## Resume Point`를 남긴다.

Resume Point에는 다음 액션, 현재 브랜치/worktree, 변경 파일, 미완료 검증, 막힌 이유를 쓴다.

### Integration Mode

오케스트레이터가 태스크를 하나씩이 아니라 묶어서 파견한 통합 구현 작업이면 다음 차이를 적용한다.

1. `assignment.md`의 `role: integration_implementation`을 확인한다.
2. `inbox/integration/implementation.md` 한 파일에 모든 태스크 결과를 append한다 — 태스크별 `## Task T-XXX:` 마커로 구분.
3. DAG topological order로 다수 태스크를 순차 구현한다 (한 태스크가 아니라 전체).
4. 작업 중 신규 태스크가 필요하면 `append-dag-stack`으로 `dag.yaml`에 추가하고(직접 편집 금지 — `set-dag-stack` 경유) `## New Task Discovered: T-XXX` 마커로 implementation.md에 기록.
5. 종료 시 `## Resume Point` 또는 `## Complete` 마커만 남긴다 — terminal 상태와 분할은 메인 오케스트레이터가 담당한다.
6. 분할 단계는 이 mode 범위 밖이다 — 구현만 책임진다.

## Review Mode

1. `assignment.md`, `implementation.md`, 태스크 커밋의 diff(라운드 PR이 열려 있으면 PR diff), downstream task 정보를 읽는다.
2. 코드를 수정하지 않는다.
3. 지정된 `review-N.md`만 작성한다.
4. 현재 태스크 범위 안의 Medium 이상 결함만 `blocking_issues`에 넣는다.
5. 후속 태스크에서 처리될 누락은 `future_task_notes`에 넣는다.
6. 애매한 범위 판단은 `questions`에 넣고 실패로 세지 않는다.

리뷰 결과 형식:

```yaml
blocking_issues:
  - severity: critical | high | medium | low
    file: string
    line: number
    description: string
    why_in_scope: string
future_task_notes:
  - deferred_to: string
    description: string
questions:
  - description: string
low_priority_notes:
  - description: string
```

## Review Fix Mode

리뷰에서 `blocking_issues`가 있으면 같은 branch/worktree에서 수정한다.

- 최신 `review-N.md`를 읽고 Medium 이상 blocking issue만 고친다.
- 새 기능, 후속 태스크 범위, Low note는 구현하지 않는다.
- 수정 전후 checkpoint를 `implementation.md`에 append한다.
- 추가 커밋을 만들고 검증 결과를 기록한다.

## Append Format

`implementation.md`에는 append만 한다. 이전 attempt를 삭제하거나 요약으로 덮어쓰지 않는다.

```markdown
## Attempt 2

started_at: 2026-05-19T10:30:00+09:00
branch: feat/example
worktree: /path/to/worktree
base_commit: abc123
status: in_progress

## Plan

- ...

## Checkpoints

- explored: ...
- edited: ...
- committed: ...

## Verification

- pnpm typecheck: pass

## Commits

- def456 feat(badge): …

## Resume Point

next_action: ...
blocked_by: ...
```

## 다른 태스크 언급 표기

`implementation.md`, `review-N.md` 의 자유 서술(Plan, Checkpoints, Decisions, Resume
Point, 리뷰 description 등)에서 다른 태스크의 노트를 언급할 때는 별칭 붙은
path-qualified wikilink 로 쓴다. (노트 디렉터리가 Obsidian 볼트 안에 있을 때의 규칙이다. 볼트가 없으면 평문 `T-001` 로 쓴다.)

```text
[[<project_path>/inbox/T-001/assignment|T-001]]
```

- **path-qualified 인 이유**: 볼트에는 `implementation.md`·`assignment.md` 같은 basename
  중복이 프로젝트 수만큼 생긴다. `[[T-001]]` 같은 bare 링크는 다른 프로젝트의 동명 파일로 조용히
  연결된다.
- **별칭을 붙이는 이유**: 경로를 그대로 노출하면 본문 표기가 무너진다. 별칭 없이 적으면
  `T-001` 한 단어였던 자리가 수십 자의 경로 문자열로 부풀어 문장이 읽기 어려워진다.
- 표 안에서 쓸 때는 별칭 구분자 `|`를 `\|`로 이스케이프한다. 표에서 `|`는 열 구분자라,
  이스케이프하지 않으면 그 행의 열 수가 늘어나 표가 어긋난다.

  ```text
  | 커밋 | 태스크 |
  |---|---|
  | `abc123` | [[acme/web/example/inbox/T-004/implementation\|T-004]] |
  ```

이 규칙은 `T-XXX` 형태의 태스크 ID 를 언급할 때만 적용한다. Integration Mode가 쓰는
`inbox/integration/` 처럼 태스크가 아닌 폴더는 대상이 아니다 — 태스크가 아닌 언급까지
wikilink 로 만들면 어휘 가드가 걸러야 할 대상을 걸러내지 못한다.

## Do Not

- `dag.yaml`, `run-log.md`, or `final.md`를 직접 terminal 상태로 갱신하지 않는다.
- 푸시하지 않는다. PR을 만들거나 고치지 않는다. 브랜치를 새로 파지 않는다.
- 오케스트레이터 대신 다른 태스크를 고르지 않는다.
- 다른 병렬 에이전트의 변경을 되돌리지 않는다.
- 리뷰 모드에서 코드를 수정하지 않는다.
- 사용량 제한으로 중단될 때 기록 없이 종료하지 않는다.

## Common Mistakes

| Mistake | Correction |
|---|---|
| "작업이 작으니 바로 수정한다" | 먼저 `implementation.md`에 attempt를 남긴다 |
| "기존 implementation이 있지만 새로 시작한다" | resume으로 보고 이전 branch/worktree/checkpoint를 확인한다 |
| "run-log가 in_progress라서 실패로 본다" | `final.md`와 `implementation.md`를 먼저 본다 |
| "리뷰가 지적한 Low note도 고친다" | Medium 이상 blocking issue만 고친다 |
| "커밋했으니 푸시까지 해 둔다" | 푸시·PR은 오케스트레이터 몫이다. 커밋 해시만 보고한다 |
| "E2E를 직접 돌려 확인한다" | 확인이 필요하다는 줄만 e2e-checklist.md 에 남긴다 |
