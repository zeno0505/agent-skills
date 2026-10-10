# PR 리스크 티어 가이드라인

PR 리스크 티어(상/중/하)는 각 라운드 PR의 리스크를 평가하고 머지 권장 사항을 결정하는 체계입니다. 이 문서는 DAG 스택 워크플로에서 리스크 티어가 어떻게 결정되고 사용되는지를 설명합니다.

## 원칙

1. **리스크는 리뷰어가 평가한다** — 코드를 작성한 에이전트나 서브에이전트가 아니라, CodeRabbit 또는 로컬 리뷰 에이전트가 평가합니다.
2. **결정론적 시그널이 먼저다** — 프로젝트별 설정으로 정의된 시그널이 발화하면 리뷰어 판단과 무관하게 `상`으로 강제합니다.
3. **리스크 티어는 권장사항이다** — 자동 머지가 아닙니다. 티어는 머지 권장을 생성하지만, 최종 머지 결정은 사람의 몫입니다.
4. **봇 승인은 입력이지 판정이 아니다** — CodeRabbit의 APPROVED 상태는 리스크 평가의 입력이지, 그 자체로 독립적 판정이 아닙니다.

## 티어 정의

### 상 (High Risk)

다음 중 **하나라도** 해당하면 `상`:

- **결정론적 시그널 발화** — `risk_config`에 정의된 시그널이 하나라도 발화
  - `critical_paths` 글로브 매칭 (예: payments, auth, subscriptions)
  - `critical_files` 글로브 매칭 (예: DB 스키마, API 계약)
  - `max_diff_lines` 초과
  - 기타 프로젝트별 커스텀 시그널
- **리뷰어 판단** — 위 시그널 없이도 리뷰어가 다음을 발견한 경우:
  - 공유 컴포넌트 변경으로 영향 범위가 넓음
  - 컨벤션/설정 변경으로 프로젝트 전반에 영향
  - 데이터 무결성 또는 보안 이슈 가능성

**처리:**
- 사람의 직접 리뷰 **필수**
- 리뷰 라운드 2회 제한과 무관하게 사람 리뷰 대기

### 중 (Medium Risk)

`상` 시그널이 없고, 리뷰어가 중간 수준 리스크로 판단한 경우:
- 주요 로직 변경이지만 격리되어 있음
- 여러 파일에 걸친 변경이지만 한 기능에 국한
- 테스트 커버리지가 있지만 엣지 케이스 우려

**처리:**
- 최대 2회 리뷰 라운드
- 2회 후 크리티컬 이슈가 남지 않으면 → 머지 권장
- 남은 마이너 파인딩은 `보류(defer)`로 처리

### 하 (Low Risk)

`상`/`중` 조건 없이 리뷰어가 낮은 리스크로 판단한 경우:
- 작은 범위의 변경
- 격리된 버그 수정
- 문서/테스트/스타일만 변경
- 리뷰에서 문제 없음

**처리:**
- 1회 리뷰 라운드 후 마이너/노 파인딩 → 머지 권장
- 발견된 마이너 이슈는 빠르게 수정 또는 `보류`

## 결정론적 시그널 설정

프로젝트별 `risk_config`는 `dag.yaml`의 최상위 레벨 또는 별도 설정 파일에 둡니다. 이 필드가 없으면 모든 결정론적 시그널이 비활성화되고, 리뷰어 판단만으로 티어를 결정합니다.

### `dag.yaml`에 직접 포함하는 방식

```yaml
schema: 2
project:
  # ...

risk_config:
  critical_paths:
    - "src/payment/**"
    - "src/auth/**"
    - "src/subscription/**"
  critical_files:
    - "**/schema.sql"
    - "**/migrations/*.sql"
    - "**/api-contract.yaml"
    - "**/*.proto"
  max_diff_lines: 500

project_policy:
  # ...
```

### 글로브 패턴

- `critical_paths`: 저장소 루트 기준 경로 패턴. `**`는 0개 이상의 디렉터리, `*`는 한 레벨 내 매칭
- `critical_files`: 저장소 루트 기준 파일 패턴. 파일명만으로도 매칭 가능

## 리뷰 라운드와의 통합

리뷰 라운드 제한(기본 2회)은 다음과 같이 동작합니다:

1. **첫 리뷰 후 리스크 평가** — `review-dag-stack`이 첫 리뷰를 읽은 뒤 시그널을 확인하고 티어를 결정
2. **티어별 처리**:
   - `상`: 사람 리뷰 대기, 라운드 카운트와 무관
   - `중`: 최대 2라운드, 크리티컬 이슈 없으면 머지 권장
   - `하`: 1라운드 후 클린하면 머지 권장
3. **기록**: `rounds[]` 엔트리에 `risk_tier`, `risk_reason`, `risk_signals`, `risk_assessed_by` 기록

## Rounds 스키마 추가 필드

```yaml
rounds:
  - number: 1
    branch: "feature/profile/avatar-upload"
    base: "feature/profile/main"
    pr_url: "https://github.com/owner/repo/pull/42"
    state: approved
    approved_sha: "abc123..."
    last_pushed_sha: "abc123..."
    risk_tier: "중"                           # NEW: 상/중/하
    risk_reason: "주요 로직 변경, 단일 모듈에 격리"  # NEW: 한 줄 사유
    risk_signals: []                          # NEW: 발화한 시그널 목록 (예: ["critical_paths", "max_diff_lines"])
    risk_assessed_by: "CodeRabbit"           # NEW: 평가자 (봇 이름 또는 에이전트)
```

## 후속 피드백 루프

머지된 PR이 문제를 일으킨 경우:
1. 해당 라운드의 `risk_tier`와 `risk_signals`를 검토
2. 반복되는 패턴이 있으면 → `risk_config` 시그널 추가 또는 린트 규칙/스킬 개선
3. 기록은 `rounds[]`에 보존되므로 사후 분석 가능 (예: "하로 머지했는데 문제가 생긴 케이스 10건 → 패턴 학습")

## 자동 머지 고려 사항

**현재 버전에서는 자동 머지를 지원하지 않습니다.** 모든 머지는 사람의 승인이 필요합니다.

향후 검토 사항:
- 수 주간의 기록 축적 후 `중`/`하` 티어에 대해 자동 머지를 고려할 수 있음
- 도입 전 최소 20–30개 라운드의 기록을 검토하여 오판 비율 확인
- 자동 머지 도입 시에도 사람이 언제든지 중단하거나 되돌릴 수 있어야 함

## 제약사항

- 리스크 티어 평가는 **첫 리뷰 이후**에만 수행 (PR이 draft이거나 리뷰 전에는 `null`)
- `risk_config`가 없으면 결정론적 시그널 없이 리뷰어 판단만 사용
- 봇이 `APPROVED`를 주지 않은 PR은 티어와 무관하게 머지 권장하지 않음
- 리스크 티어는 권장이지 강제가 아님 — 최종 결정은 항상 사람

## 워크플로 예시

### 예시 1: 하 티어, 1라운드 클린 머지

1. `run-dag-stack`이 라운드 1 생성, PR 오픈
2. CodeRabbit 리뷰 → `APPROVED`, 마이너 제안 2건
3. `review-dag-stack` 실행:
   - 시그널 확인: 없음
   - 파일: `docs/README.md`, `tests/unit/parser.test.js` (문서+테스트)
   - 판단: `하`
   - 기록: `risk_tier: "하"`, `risk_reason: "문서 및 테스트만 변경, 리뷰 클린"`
4. 머지 권장: "하 티어, 1라운드 승인, 머지 권장"

### 예시 2: 상 티어, 사람 리뷰 필수

1. `run-dag-stack`이 라운드 2 생성, PR 오픈
2. CodeRabbit 리뷰 → `APPROVED`
3. `review-dag-stack` 실행:
   - 시그널 확인: `src/payment/checkout.ts` 변경 → `critical_paths` 발화
   - 판단: `상` (시그널 강제)
   - 기록: `risk_tier: "상"`, `risk_reason: "결제 경로 변경 (critical_paths 시그널 발화)"`, `risk_signals: ["critical_paths"]`
4. 머지 권장 **안 함**, 보고: "상 티어 — 사람 리뷰 필수"

### 예시 3: 중 티어, 2라운드 후 머지

1. `run-dag-stack`이 라운드 3 생성, PR 오픈
2. CodeRabbit 리뷰 → `CHANGES_REQUESTED`, 5건 파인딩
3. `review-dag-stack`:
   - 시그널 확인: 없음
   - 파일 다수, 주요 로직 변경
   - 판단: `중`
   - 기록: `risk_tier: "중"`, `risk_reason: "여러 파일 변경, 주요 비즈니스 로직"`
   - 5건 파인딩 중 3건 반영, 2건 무효 처리
4. 리뷰 반영 커밋 → 다시 푸시
5. CodeRabbit 재리뷰 → `APPROVED`, 마이너 제안 1건
6. `review-dag-stack`:
   - 라운드 카운트: 2회
   - 중 티어 제한: 2회
   - 크리티컬 이슈: 없음
   - 머지 권장: "중 티어, 2라운드 승인, 크리티컬 이슈 없음 → 머지 권장, 마이너 제안 1건은 보류 처리"

## 버전 이력

- **0.4.0** (2026-10-10) — PR 리스크 티어 시스템 추가
