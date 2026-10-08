#!/usr/bin/env python3
"""pair_sheet.py — put mockup and app captures side by side and diff their computed styles.

Usage:
  python3 pair_sheet.py <mockup_dir> <app_dir> --out <compare_dir> [--max-width 1600]

For every <state>-<width>.png present on either side it writes <compare_dir>/<state>-<width>.png
("MOCKUP | APP", missing side drawn as a grey placeholder) and <compare_dir>/style-diff.md with one
row per style pair whose values differ. Requires Pillow (pip install pillow).
Only reports; classification (missing implementation / mockup-only / out of scope / ambiguous)
is a human-or-agent judgment made by looking at the images.
"""
import argparse
import json
from pathlib import Path

from PIL import Image, ImageDraw

LABEL_H = 28
GAP = 12


def load(p: Path):
    return Image.open(p).convert("RGB") if p.exists() else None


def placeholder(w, h, text):
    im = Image.new("RGB", (w, h), "#d4d4d4")
    ImageDraw.Draw(im).text((16, 16), text, fill="#333333")
    return im


def side_by_side(left, right, max_width):
    w = max(i.width for i in (left, right) if i) if (left or right) else 800
    h = max(i.height for i in (left, right) if i) if (left or right) else 600
    left = left or placeholder(w, h, "mockup: not captured")
    right = right or placeholder(w, h, "app: not captured")
    sheet = Image.new("RGB", (left.width + right.width + GAP, max(left.height, right.height) + LABEL_H), "#ffffff")
    d = ImageDraw.Draw(sheet)
    d.text((8, 8), "MOCKUP", fill="#000000")
    d.text((left.width + GAP + 8, 8), "APP", fill="#000000")
    sheet.paste(left, (0, LABEL_H))
    sheet.paste(right, (left.width + GAP, LABEL_H))
    d.line([(left.width + GAP // 2, 0), (left.width + GAP // 2, sheet.height)], fill="#ef4444", width=2)
    if sheet.width > max_width:
        ratio = max_width / sheet.width
        sheet = sheet.resize((max_width, int(sheet.height * ratio)))
    return sheet


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("mockup_dir", type=Path)
    ap.add_argument("app_dir", type=Path)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--max-width", type=int, default=1600)
    a = ap.parse_args()
    a.out.mkdir(parents=True, exist_ok=True)

    names = sorted({p.name for d in (a.mockup_dir, a.app_dir) for p in d.glob("*.png")})
    for name in names:
        side_by_side(load(a.mockup_dir / name), load(a.app_dir / name), a.max_width).save(a.out / name)

    def styles(d):
        f = d / "styles.json"
        return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {}

    ms, as_ = styles(a.mockup_dir), styles(a.app_dir)
    rows, missing = [], []
    for key in sorted(set(ms) | set(as_)):
        if key == "_errors":
            continue
        mp, ap_ = ms.get(key, {}), as_.get(key, {})
        for pair in sorted(set(mp) | set(ap_)):
            mv, av = mp.get(pair), ap_.get(pair)
            if mv is None or av is None:
                missing.append(f"| {key} | {pair} | {'목업 요소 없음' if mv is None else ''}{' / ' if mv is None and av is None else ''}{'앱 요소 없음' if av is None else ''} |")
                continue
            for prop in sorted(set(mv) | set(av)):
                if mv.get(prop) != av.get(prop):
                    rows.append(f"| {key} | {pair} | {prop} | {mv.get(prop)} | {av.get(prop)} |")
    errors = {**{f"mockup:{k}": v for k, v in ms.get("_errors", {}).items()},
              **{f"app:{k}": v for k, v in as_.get("_errors", {}).items()}}
    md = ["# style diff", "", f"비교 이미지 {len(names)}장 · 값이 다른 속성 {len(rows)}건 · 선택자 불일치 {len(missing)}건 · 미캡처 {len(errors)}건", ""]
    md += ["| 상태-폭 | 짝 | 속성 | 목업 | 앱 |", "|---|---|---|---|---|", *rows, ""]
    if missing:
        md += ["## 선택자가 요소를 못 찾음", "", "| 상태-폭 | 짝 | 상황 |", "|---|---|---|", *missing, ""]
    if errors:
        md += ["## 미캡처", "", *[f"- {k}: {v}" for k, v in errors.items()], ""]
    (a.out / "style-diff.md").write_text("\n".join(md), encoding="utf-8")
    print(f"[pair-sheet] {len(names)} sheet(s), {len(rows)} differing prop(s), {len(missing)} missing element(s), {len(errors)} not captured → {a.out}")


if __name__ == "__main__":
    main()
