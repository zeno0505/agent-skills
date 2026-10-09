#!/usr/bin/env python3
"""qa_pages.py — numeric suspects for the visual self-QA of rendered PDF pages.

Usage:
  python3 qa_pages.py <png_dir> [--sheets <dir>] [--edge 8] [--min-fill 0.45]

Per page (p-*.png from pdftoppm):
  edge ink  — share of non-background pixels in an <edge>px band on each side. Ink touching the
              border suggests clipping or content running off the canvas.
  fill      — area of the content bounding box (inside the page, ignoring the edge band) divided
              by the page area. Low fill on a diagram page suggests a small figure floating in
              empty space.
Background = the most common colour of the four corners (tolerance 24 per channel); full-bleed
gradient covers will show edge ink by design — judge them by eye.
Writes 2×2 contact sheets (sheet-N.png) when --sheets is given. Exit code is always 0: these are
suspects to open and look at, not a verdict.
Requires Pillow.
"""
import argparse
import re
from collections import Counter
from pathlib import Path

from PIL import Image


def bg_color(im):
    w, h = im.size
    px = im.load()
    samples = [px[x, y] for (x0, y0) in ((0, 0), (w - 10, 0), (0, h - 10), (w - 10, h - 10))
               for x in range(x0, x0 + 10) for y in range(y0, y0 + 10)]
    return Counter(samples).most_common(1)[0][0]


def is_ink(c, bg, tol=24):
    return any(abs(a - b) > tol for a, b in zip(c, bg))


def analyse(path, edge):
    im = Image.open(path).convert("RGB")
    small = im.resize((im.width // 2, im.height // 2))
    w, h = small.size
    e = max(1, edge // 2)
    px = small.load()
    bg = bg_color(small)
    bands = {"top": (0, 0, w, e), "bottom": (0, h - e, w, h), "left": (0, 0, e, h), "right": (w - e, 0, w, h)}
    edge_ink = {}
    for name, (x0, y0, x1, y1) in bands.items():
        tot = ink = 0
        for x in range(x0, x1):
            for y in range(y0, y1):
                tot += 1
                ink += is_ink(px[x, y], bg)
        edge_ink[name] = ink / tot
    xs, ys = [], []
    for y in range(e, h - e, 2):
        for x in range(e, w - e, 2):
            if is_ink(px[x, y], bg):
                xs.append(x); ys.append(y)
    fill = ((max(xs) - min(xs)) * (max(ys) - min(ys)) / (w * h)) if xs else 0.0
    return edge_ink, fill


def page_no(p):
    m = re.search(r"(\d+)", p.stem)
    return int(m.group(1)) if m else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("png_dir", type=Path)
    ap.add_argument("--sheets", type=Path)
    ap.add_argument("--edge", type=int, default=8)
    ap.add_argument("--min-fill", type=float, default=0.45)
    ap.add_argument("--edge-threshold", type=float, default=0.005)
    a = ap.parse_args()
    pages = sorted(a.png_dir.glob("*.png"), key=page_no)
    if not pages:
        raise SystemExit(f"no PNG pages in {a.png_dir}")
    print(f"{'page':>4}  {'fill':>5}  edge-ink(top/bottom/left/right)  suspects")
    flagged = 0
    for p in pages:
        edge_ink, fill = analyse(p, a.edge)
        sus = [f"edge:{k}" for k, v in edge_ink.items() if v > a.edge_threshold]
        if fill < a.min_fill:
            sus.append("low-fill")
        flagged += bool(sus)
        e = "/".join(f"{edge_ink[k]*100:.1f}" for k in ("top", "bottom", "left", "right"))
        print(f"{page_no(p):>4}  {fill:5.2f}  {e:<32} {' '.join(sus) or '-'}")
    print(f"[qa-pages] {len(pages)} page(s), {flagged} with suspects — open those PNGs and judge by eye")
    if a.sheets:
        a.sheets.mkdir(parents=True, exist_ok=True)
        first = Image.open(pages[0])
        W, H = first.width // 2, first.height // 2
        for k in range(0, len(pages), 4):
            sheet = Image.new("RGB", (W * 2 + 30, H * 2 + 30), "#888888")
            for j, f in enumerate(pages[k:k + 4]):
                sheet.paste(Image.open(f).convert("RGB").resize((W, H)), (10 + (j % 2) * (W + 10), 10 + (j // 2) * (H + 10)))
            sheet.save(a.sheets / f"sheet-{k // 4 + 1}.png")
        print(f"[qa-pages] contact sheets → {a.sheets}")


if __name__ == "__main__":
    main()
