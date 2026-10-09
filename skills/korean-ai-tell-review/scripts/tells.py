#!/usr/bin/env python3
"""korean-ai-tell-review 정량 계측기.

마크다운을 걷어낸 뒤 결정적으로 셀 수 있는 신호만 센다. 판정은 하지 않는다 —
카탈로그(tells.md)를 읽는 서브에이전트가 이 수치를 앵커로 삼아 판정한다.

베이스라인·z-score·위험등급을 내지 않는다. 참고한 저장소의 베이스라인은
쉼표 계열 6개 지표에만 실측값이 있고 그나마 칼럼·에세이 코퍼스에서 나온 값이라,
설계 문서에 그대로 대면 틀린 답을 낸다.

어휘 사전과 정규식은 epoko77-ai/im-not-ai (MIT, (c) 2026 epoko77-ai) 에서
가져왔다. have/make 사전에서 "만들다" 계열은 뺐다 — 설계 문서 94편 실측에서
5건 전부 자연스러운 한국어였다("주소를 만들었다").

사용법:
    python3 -B tells.py <경로>
    cat foo.md | python3 -B tells.py -
    python3 -B tells.py <경로> --out-dir <전처리본 저장 위치>
"""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import tempfile

# 분포형 지표를 산출할 최소 분량. 이보다 짧으면 문장 길이 표준편차 같은 값이
# 표본 부족으로 튄다(350자 샘플에서 어휘 다양도가 사람 평균의 6배로 나왔다).
MIN_CHARS_FOR_DISTRIBUTION = 800
MIN_SENTENCES_FOR_DISTRIBUTION = 10

# 패턴당 증거로 남길 최대 건수. 보고에 다 싣지 않으므로 상한을 둔다.
MAX_EVIDENCE_PER_PATTERN = 5


# ---------------------------------------------------------------------------
# 전처리
# ---------------------------------------------------------------------------
# 줄을 지우지 않고 빈 줄로 바꾼다. 줄 번호가 원본과 어긋나면 보고의 위치
# 표기(`foo.md:88`)로 원문을 찾을 수 없다.

_FENCE_RE = re.compile(r"^\s*(?:```|~~~)")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|?[\s:|-]+\|[\s:|-]*$")
_HEADING_RE = re.compile(r"^\s*#{1,6}\s+")
_INLINE_CODE_RE = re.compile(r"`[^`\n]+`")
_LIST_MARKER_RE = re.compile(r"^(\s*)(?:[-*+]|\d{1,3}[.)])\s+")
_QUOTE_MARKER_RE = re.compile(r"^(\s*)>\s?")
_LINK_RE = re.compile(r"\[([^\]\n]*)\]\([^)\n]*\)")
_EMPHASIS_RE = re.compile(r"\*\*([^*\n]+)\*\*|__([^_\n]+)__")


def strip_markup(text: str) -> str:
    """마크다운 서식을 제거하되 줄 수는 보존한다."""
    lines = text.split("\n")
    out: list[str] = []
    in_fence = False
    in_frontmatter = False

    for i, line in enumerate(lines):
        # frontmatter — 첫 줄이 --- 이면 다음 --- 까지
        if i == 0 and line.strip() == "---":
            in_frontmatter = True
            out.append("")
            continue
        if in_frontmatter:
            if line.strip() == "---":
                in_frontmatter = False
            out.append("")
            continue

        if _FENCE_RE.match(line):
            in_fence = not in_fence
            out.append("")
            continue
        if in_fence:
            out.append("")
            continue

        if _TABLE_ROW_RE.match(line) or _TABLE_SEP_RE.match(line):
            out.append("")
            continue
        if _HEADING_RE.match(line):
            out.append("")
            continue

        s = _INLINE_CODE_RE.sub(" ", line)
        s = _LINK_RE.sub(r"\1", s)
        s = _EMPHASIS_RE.sub(lambda m: m.group(1) or m.group(2), s)
        s = _QUOTE_MARKER_RE.sub(r"\1", s)
        s = _LIST_MARKER_RE.sub(r"\1", s)
        out.append(s)

    return "\n".join(out)


# ---------------------------------------------------------------------------
# 문장 분해
# ---------------------------------------------------------------------------

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text) if s.strip()]


# ---------------------------------------------------------------------------
# 어휘 사전 · 정규식
# ---------------------------------------------------------------------------

# A-8 이중 피동. 단순 "되다" 는 정상 표현이라 제외한다.
DOUBLE_PASSIVE_TOKENS = (
    "되어진다", "되어졌다", "되어진", "되어지는",
    "여지다", "여진다", "여졌다", "여진",
    "잊혀진", "잊혀졌", "잊혀진다",
    "보여진다", "보여졌다", "보여진",
    "쓰여진다", "쓰여졌다", "쓰여진",
    "닫혀진", "열려진", "불려진", "놓여진",
)

# A-7 have/possess 직역. 원 저장소 사전에서 "만들다" 계열을 뺀 것이다.
HAVE_LITERAL_TOKENS = (
    "가지고 있다", "가지고있다", "가지고 있는", "가지고있는",
    "가지고 있었", "가지고있었", "가지고 있으", "가지고있으",
    "갖고 있다", "갖고있다", "갖고 있는", "갖고있는",
    "을 가지다", "를 가지다", "을 가졌", "를 가졌",
    "을 가진다", "를 가진다",
    "회의를 가지", "회의를 가졌",
)

# A-9 "~에 의해" + 피동. 단순 "에 의해" 는 자연스러운 한국어라
# 피동 동사가 뒤 12자 안에 와야 매칭한다.
BY_PASSIVE_RE = re.compile(
    r"에\s*의(?:해|하여)\s+\S{0,12}?(?:되|받|당하|지)(?:다|었|어|ㄴ다|는다|는|ㄹ|을)"
)

# A-19 이중 조사. 단일 "~의" 는 절대 매칭하지 않는다.
DOUBLE_PARTICLE_RE = re.compile(r"(?:에서의|에로의|으로의|에의|으로부터의|로부터의)")

# C-8 부정 대구. 설계문서 프로파일에서는 면제 — 계측만 한다.
ANTITHESIS_RE = re.compile(
    r"(?:가|이)\s*아니라|것이\s*아니라|것은\s*아니다|이기\s*이전에|되기\s*이전에|이기보다"
)

# D-1 결산 상투구.
CONCLUSION_PIVOT_TOKENS = ("결론적으로", "따라서", "이를 통해", "그러므로", "요약하면", "정리하자면")

# G-2 이중·삼중 완곡.
HEDGE_STACK_RE = re.compile(
    r"가능성이\s*있을\s*수\s*있|보여질\s*수\s*있|수\s*있을\s*것으로\s*보|"
    r"것으로\s*판단될\s*수\s*있|수도\s*있을\s*것"
)

# C-11 연결어미 뒤 쉼표. 설계문서 프로파일에서는 면제 — 계측만 한다.
ENDING_COMMA_RE = re.compile(r"[가-힣](?:고|며|지만|면서|아서|어서)\s*,")
ENDING_BOUNDARY_RE = re.compile(r"(?:고|며|지만|면서|아서|어서)(?=[\s,.!?]|$)")

# K 계열 — 전달력. 설계 문서 94편 실측에서 뽑았다.
# 한국어는 단어 경계가 없어 앞뒤 음절을 막지 않으면 부분 매칭이 난다.
# 실측 오탐: "관측 단위에서" 의 `위에서`, "아까운" 의 `아까`, "앞서가는" 의 `앞서`.
SESSION_DEIXIS_RE = re.compile(
    r"(?<![가-힣])(?:위에서|방금|지금까지)"
    r"|(?<![가-힣])앞서(?![가-힣])"
    r"|(?<![가-힣])아까(?![가-힣])"
    r"|이번 세션|위 논의|앞의 논의|바로 위"
)
BARE_TASK_ID_RE = re.compile(r"(?<![A-Za-z0-9-])[A-Z]-\d{3}(?![0-9])")
# 위키링크 안의 태스크 ID 는 경로가 곧 설명이라 무설명이 아니다.
# 계수 전에 링크 전체를 지워 K-2 수치가 부풀지 않게 한다.
WIKILINK_RE = re.compile(r"\[\[[^\]]*\]\]")
SUBJECTLESS_REPORT_TOKENS = ("확인했습니다", "확인했다", "해결했습니다", "반영했습니다", "처리했습니다")
# `같습니다` 단독은 설계 문서에서 압도적으로 비교("표와 같습니다")라 추측이 아니다.
# 추측 어감은 `것 같-` 에만 실린다. `그대로 보입니다` 의 `로 보-` 도 막는다.
SPECULATIVE_ENDING_RE = re.compile(
    r"것 같다|것 같습니다|것 같은|것 같아"
    r"|(?<!대)로 보인다|(?<!대)로 보입니다|(?<!대)로 보이는"
    r"|인 듯|로 추정"
)


# ---------------------------------------------------------------------------
# 계수
# ---------------------------------------------------------------------------


def _line_index(text: str) -> list[int]:
    """각 줄의 시작 오프셋."""
    offsets = [0]
    for line in text.split("\n")[:-1]:
        offsets.append(offsets[-1] + len(line) + 1)
    return offsets


def _line_of(offsets: list[int], pos: int) -> int:
    lo, hi = 0, len(offsets) - 1
    while lo < hi:
        mid = (lo + hi + 1) // 2
        if offsets[mid] <= pos:
            lo = mid
        else:
            hi = mid - 1
    return lo + 1


def _excerpt(text: str, start: int, end: int, width: int = 28) -> str:
    a = max(0, start - width)
    b = min(len(text), end + width)
    # 인라인 코드를 걷어낸 자리에 공백이 길게 남으므로 눌러 준다.
    return re.sub(r"\s+", " ", text[a:b]).strip()


def _collect(text: str, offsets: list[int], spans: list[tuple[int, int]]) -> list[dict]:
    ev = []
    for start, end in spans[:MAX_EVIDENCE_PER_PATTERN]:
        ev.append({"line": _line_of(offsets, start), "text": _excerpt(text, start, end)})
    return ev


def count_tokens(text: str, tokens: tuple[str, ...]) -> list[tuple[int, int]]:
    spans = []
    for tok in tokens:
        start = text.find(tok)
        while start != -1:
            spans.append((start, start + len(tok)))
            start = text.find(tok, start + 1)
    return sorted(spans)


def count_regex(text: str, rx: re.Pattern) -> list[tuple[int, int]]:
    return [(m.start(), m.end()) for m in rx.finditer(text)]


# ---------------------------------------------------------------------------
# 분포형
# ---------------------------------------------------------------------------

_FINAL_ENDING_RE = re.compile(r"([가-힣]{2})[.!?]?\s*$")


def distribution(sentences: list[str]) -> dict:
    lengths = [len(s) for s in sentences]
    with_comma = sum(1 for s in sentences if "," in s)

    endings = []
    for s in sentences:
        m = _FINAL_ENDING_RE.search(s)
        endings.append(m.group(1) if m else None)

    streak = best = 0
    prev = None
    for e in endings:
        if e is not None and e == prev:
            streak += 1
        else:
            streak = 1
        prev = e
        best = max(best, streak)

    return {
        "applicable": True,
        "comma_inclusion_rate": round(with_comma / len(sentences), 3),
        "long_sentence_100": sum(1 for n in lengths if n >= 100),
        "same_ending_max_streak": best,
        "sentence_len_stdev": round(statistics.pstdev(lengths), 1) if len(lengths) > 1 else 0.0,
    }


# ---------------------------------------------------------------------------
# 본체
# ---------------------------------------------------------------------------


def analyse(raw: str, source_name: str, out_dir: str) -> dict:
    body = strip_markup(raw)
    offsets = _line_index(body)
    sentences = split_sentences(body)

    patterns = {
        "double_passive": count_tokens(body, DOUBLE_PASSIVE_TOKENS),
        "have_literal": count_tokens(body, HAVE_LITERAL_TOKENS),
        "by_passive": count_regex(body, BY_PASSIVE_RE),
        "double_particle": count_regex(body, DOUBLE_PARTICLE_RE),
        "antithesis": count_regex(body, ANTITHESIS_RE),
        "conclusion_pivot": count_tokens(body, CONCLUSION_PIVOT_TOKENS),
        "hedge_stack": count_regex(body, HEDGE_STACK_RE),
        "session_deixis": count_regex(body, SESSION_DEIXIS_RE),
        # 위키링크를 같은 길이의 공백으로 덮어 오프셋을 보존한 뒤 센다.
        "bare_task_id": count_regex(
            WIKILINK_RE.sub(lambda m: " " * len(m.group(0)), body), BARE_TASK_ID_RE
        ),
        "subjectless_report": count_tokens(body, SUBJECTLESS_REPORT_TOKENS),
        "speculative_ending": count_regex(body, SPECULATIVE_ENDING_RE),
    }

    counts = {k: len(v) for k, v in patterns.items()}
    evidence = {k: _collect(body, offsets, v) for k, v in patterns.items() if v}

    # C-11 은 비율이라 따로 낸다.
    boundary = len(ENDING_BOUNDARY_RE.findall(body))
    ending_comma_hits = count_regex(body, ENDING_COMMA_RE)
    counts["ending_comma"] = len(ending_comma_hits)
    ending_comma_rate = round(len(ending_comma_hits) / boundary, 3) if boundary else 0.0

    body_chars = len(body.strip())
    if body_chars >= MIN_CHARS_FOR_DISTRIBUTION and len(sentences) >= MIN_SENTENCES_FOR_DISTRIBUTION:
        dist = distribution(sentences)
    else:
        dist = {
            "applicable": False,
            "reason": f"{body_chars}자 / {len(sentences)}문장 — "
                      f"기준 {MIN_CHARS_FOR_DISTRIBUTION}자 · "
                      f"{MIN_SENTENCES_FOR_DISTRIBUTION}문장 미만",
        }

    stripped_path = os.path.join(out_dir, f"{source_name}.stripped.md")
    with open(stripped_path, "w", encoding="utf-8") as f:
        f.write(body)

    return {
        "source": source_name,
        "char_count": body_chars,
        "raw_char_count": len(raw),
        "sentence_count": len(sentences),
        "stripped_path": stripped_path,
        "counts": counts,
        "ending_comma_rate": ending_comma_rate,
        "evidence": evidence,
        "distribution": dist,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="한국어 AI 티 정량 계측기")
    ap.add_argument("path", help="검수할 파일 경로. '-' 이면 stdin")
    ap.add_argument("--out-dir", default=None, help="전처리본을 쓸 디렉터리 (기본: 임시 디렉터리)")
    args = ap.parse_args(argv)

    if args.path == "-":
        raw = sys.stdin.read()
        name = "stdin"
    else:
        if not os.path.isfile(args.path):
            print(f"파일을 찾을 수 없습니다: {args.path}", file=sys.stderr)
            return 2
        with open(args.path, "r", encoding="utf-8") as f:
            raw = f.read()
        name = os.path.basename(args.path)

    out_dir = args.out_dir or tempfile.mkdtemp(prefix="tells-")
    os.makedirs(out_dir, exist_ok=True)

    result = analyse(raw, name, out_dir)
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
