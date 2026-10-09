#!/usr/bin/env python3
"""preflight.py — checks a Slidev slides.md before export.

Usage:
  python3 preflight.py <slides.md> [--forbidden FILE] [--jargon]

Fails (exit 1) on:
  * mermaid blocks (they can export as blank figures — use HTML/CSS or tables)
  * raw URLs outside markdown/HTML links (use labelled links)
  * any regex listed in the forbidden-terms file (default: forbidden-terms.txt next to slides.md,
    one Python regex per line, '#' comments). Keep that file out of public repositories.
--jargon prints candidate jargon tokens (acronyms, Latin words in Korean text) to cross-check
against the glossary appendix. Candidates only; a human reads and decides.
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

MERMAID = [re.compile(p, re.I) for p in (r"```\s*mermaid\b", r"~~~+\s*mermaid\b", r"<mermaid\b")]
URL = re.compile(r"https?://[^\s)<>\"']+")
LINK_BEFORE = re.compile(r"(\]\(\s*|href=\s*[\"'])$")
COMMON = {"pdf", "png", "url", "html", "css", "ok", "a", "b", "i"}
TOKEN = re.compile(r"\b[A-Za-z][A-Za-z0-9_.+-]{1,}\b")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("slides", type=Path)
    ap.add_argument("--forbidden", type=Path)
    ap.add_argument("--jargon", action="store_true")
    a = ap.parse_args()
    text = a.slides.read_text(encoding="utf-8")
    lines = text.splitlines()
    fails = []

    for i, line in enumerate(lines, 1):
        for rx in MERMAID:
            if rx.search(line):
                fails.append(f"{i}: mermaid is banned — use HTML/CSS boxes or a table")
        for m in URL.finditer(line):
            if not LINK_BEFORE.search(line[: m.start()]):
                fails.append(f"{i}: raw URL — use a labelled link: {m.group(0)[:60]}")

    forbidden = a.forbidden or a.slides.parent / "forbidden-terms.txt"
    if forbidden.exists():
        pats = [l.strip() for l in forbidden.read_text(encoding="utf-8").splitlines() if l.strip() and not l.lstrip().startswith("#")]
        for pat in pats:
            rx = re.compile(pat)
            for i, line in enumerate(lines, 1):
                if rx.search(line):
                    fails.append(f"{i}: forbidden term /{pat}/")

    if a.jargon:
        body = re.sub(r"```.*?```", " ", text, flags=re.S)
        body = re.sub(r"^---.*?^---", " ", body, count=1, flags=re.S | re.M)  # headmatter
        body = re.sub(r"<[^>]+>|\(https?://[^)]*\)", " ", body)               # tags, link targets
        counts = Counter(t for t in TOKEN.findall(body)
                         if any(ch.isupper() for ch in t) and t.lower() not in COMMON)
        print("[preflight] jargon candidates (check first-use definition or glossary row):")
        for tok, n in counts.most_common(40):
            print(f"  {tok} x{n}")

    if fails:
        print("[preflight] FAIL")
        for f in fails:
            print("  " + f)
        sys.exit(1)
    print(f"[preflight] OK ({len(lines)} lines; forbidden list: {'yes' if forbidden.exists() else 'none'})")


if __name__ == "__main__":
    main()
