#!/usr/bin/env python3
"""build_timeline.py — storyboard JSON → HyperFrames index.html + timing.json.

Usage:
  python3 build_timeline.py storyboard.json [--out index.html] [--timing timing.json]

Each scene's duration is computed, never hand-tuned:
  duration = max(last_reveal + reveal + hold,  read_base + weighted_chars / cps)
  weighted_chars = Hangul/CJK chars * 1.0 + other non-space chars * 0.5   (tags stripped)
Defaults: reveal 0.5s, hold 4.5s, read_base 1.5s, cps 15. Per-scene "hold" / "cps" override.

storyboard.json (paths relative to the JSON file):
{
  "width": 1920, "height": 1080, "css": "style.css", "gsap": "gsap.min.js", "lang": "ko",
  "hold": 4.5, "cps": 15, "read_base": 1.5, "reveal": 0.5, "progress_bar": true,
  "scenes": [
    {"id": "s1", "style": "", "body": "<h1 id='s1h'>…</h1>"  (or "body_file": "scenes/s1.html"),
     "reveals": [["#s1h", 0.3], ["#s1s", 0.8]],      # [selector, seconds after previous reveal start]
     "tweens": [["tl.to('#ph', {x: 900, duration: 2, ease: 'none'}, {t});", 1.0]],  # {t} = absolute time
     "hold": 6, "cps": 12}
  ]
}
Writes index.html (one paused GSAP timeline registered as window.__timelines["main"]) and
timing.json ([{id, start, duration, full_reveal, qa_time, rule, chars}]) for extract_frames.py.
Prints a timing table; scenes longer than 20s are flagged for splitting.
"""
import argparse
import html
import json
import re
import sys
from pathlib import Path

CJK = re.compile(r"[\u1100-\u11ff\u3130-\u318f\uac00-\ud7a3\u3040-\u30ff\u4e00-\u9fff]")


def visible_text(body: str) -> str:
    body = re.sub(r"<(script|style)\b.*?</\1>", " ", body, flags=re.S | re.I)
    body = re.sub(r"<[^>]+>", " ", body)
    return html.unescape(body)


def weighted_chars(text: str) -> float:
    n = 0.0
    for ch in text:
        if ch.isspace():
            continue
        n += 1.0 if CJK.match(ch) else 0.5
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("storyboard", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--timing", type=Path)
    a = ap.parse_args()
    base = a.storyboard.parent
    sb = json.loads(a.storyboard.read_text(encoding="utf-8"))
    out = a.out or base / "index.html"
    timing_path = a.timing or base / "timing.json"

    W, H = sb.get("width", 1920), sb.get("height", 1080)
    reveal = float(sb.get("reveal", 0.5))
    g_hold, g_cps, read_base = float(sb.get("hold", 4.5)), float(sb.get("cps", 15)), float(sb.get("read_base", 1.5))

    t = 0.0
    js, sections, timing, warn = [], [], [], []
    for sc in sb["scenes"]:
        sid = sc["id"]
        body = sc.get("body") or (base / sc["body_file"]).read_text(encoding="utf-8")
        rel = 0.0
        for sel, gap in sc.get("reveals", []):
            rel += float(gap)
            js.append(f'pop({json.dumps(sel)}, {round(t + rel, 3)});')
            m = re.match(r"#([\w-]+)$", sel)
            if m and f'id="{m.group(1)}"' not in body and f"id='{m.group(1)}'" not in body:
                warn.append(f"{sid}: reveal selector {sel} not found in scene body")
        for tpl, off in sc.get("tweens", []):
            js.append(tpl.replace("{t}", str(round(t + float(off), 3))))
        chars = weighted_chars(visible_text(body))
        by_hold = rel + reveal + float(sc.get("hold", g_hold))
        by_read = read_base + chars / float(sc.get("cps", g_cps))
        dur = round(max(by_hold, by_read) * 10 + 0.4999) / 10  # round up to 0.1s
        rule = "hold" if by_hold >= by_read else "read"
        sections.append(
            f'<section id="{sid}" class="clip scene" style="{sc.get("style", "")}" '
            f'data-start="{round(t, 3)}" data-duration="{dur}" data-track-index="0">{body}</section>'
        )
        timing.append({"id": sid, "start": round(t, 3), "duration": dur,
                       "full_reveal": round(t + rel + reveal, 3),
                       "qa_time": round(t + dur - 0.3, 3), "rule": rule, "chars": round(chars, 1)})
        if dur > 20:
            warn.append(f"{sid}: {dur}s — consider splitting the scene")
        t += dur
    total = round(t, 3)

    css = (base / sb.get("css", "style.css")).read_text(encoding="utf-8")
    progress = ""
    progress_js = ""
    if sb.get("progress_bar", True):
        progress = (f'<div id="progress" class="clip" style="inset:auto; top:0; left:0; width:{W}px; height:10px;" '
                    f'data-start="0" data-duration="{total}" data-track-index="9"></div>')
        progress_js = f'tl.fromTo("#progress", {{ scaleX: 0 }}, {{ scaleX: 1, duration: {total}, ease: "none" }}, 0);'
    doc = f"""<!doctype html>
<html lang="{sb.get('lang', 'ko')}" data-resolution="landscape">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width={W}, height={H}" />
<script src="{sb.get('gsap', 'gsap.min.js')}"></script>
<style>
{css}
</style>
</head>
<body>
<div id="root" data-composition-id="main" data-start="0" data-duration="{total}" data-width="{W}" data-height="{H}">
{progress}
{chr(10).join(sections)}
</div>
<script>
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
const pop = (sel, t) => tl.fromTo(sel, {{ opacity: 0, y: 30 }}, {{ opacity: 1, y: 0, duration: {reveal}, ease: "power2.out" }}, t);
{progress_js}
{chr(10).join(js)}
window.__timelines["main"] = tl;
tl.seek(0);
</script>
</body>
</html>
"""
    out.write_text(doc, encoding="utf-8")
    timing_path.write_text(json.dumps(timing, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"{'scene':<8}{'start':>8}{'dur':>7}{'rule':>6}{'chars':>8}")
    for r in timing:
        print(f"{r['id']:<8}{r['start']:>8}{r['duration']:>7}{r['rule']:>6}{r['chars']:>8}")
    print(f"total {total}s → {out} , {timing_path}")
    if total > 90:
        warn.append(f"total {total}s exceeds 90s — split the video or move content to a document")
    for w in warn:
        print("WARN", w, file=sys.stderr)


if __name__ == "__main__":
    main()
