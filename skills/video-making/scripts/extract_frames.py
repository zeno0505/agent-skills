#!/usr/bin/env python3
"""extract_frames.py — pull one fully revealed frame per scene for visual QA.

Usage:
  python3 extract_frames.py <video.mp4> (--timing timing.json | --html index.html) [--out qa] [--tag r1] [--no-stable]

--timing  timing.json from build_timeline.py (uses each scene's qa_time: 0.3s before its cut)
--html    fallback: parse <section ... class="...scene..." data-start data-duration> from the composition
--tag     added to file names; change it on every re-render so image viewers cannot show a cached frame
Writes <out>/<tag>-NN-<scene>-t<sec>.png with ffmpeg (accurate seek) and prints the list.
Also copies each one to a stable name <out>/frame-N.png (N = scene number, 1-based) for hand-off
and docs that link a fixed path; --no-stable skips that. Look at the tagged files during QA —
the stable names are overwritten on every run, which is exactly what image viewers cache.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path


def scenes_from_html(path: Path):
    text = path.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"<section\b[^>]*>", text):
        tag = m.group(0)
        sid = re.search(r'\bid="([^"]+)"', tag)
        st = re.search(r'data-start="([\d.]+)"', tag)
        du = re.search(r'data-duration="([\d.]+)"', tag)
        if sid and st and du:
            s, d = float(st.group(1)), float(du.group(1))
            out.append({"id": sid.group(1), "qa_time": round(s + d - 0.3, 3)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video", type=Path)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--timing", type=Path)
    src.add_argument("--html", type=Path)
    ap.add_argument("--out", type=Path, default=Path("qa"))
    ap.add_argument("--tag", default="r1")
    ap.add_argument("--no-stable", action="store_true", help="do not write frame-N.png copies")
    a = ap.parse_args()
    scenes = json.loads(a.timing.read_text(encoding="utf-8")) if a.timing else scenes_from_html(a.html)
    if not scenes:
        sys.exit("no scenes found")
    if not a.video.is_file():
        sys.exit(f"video not found: {a.video} — render first")
    a.out.mkdir(parents=True, exist_ok=True)
    for i, sc in enumerate(scenes, 1):
        t = sc["qa_time"]
        dst = a.out / f"{a.tag}-{i:02d}-{sc['id']}-t{t:.1f}.png"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", str(a.video), "-ss", str(t),
                        "-frames:v", "1", str(dst)], check=True)
        print(dst)
        if not a.no_stable:
            stable = a.out / f"frame-{i}.png"
            shutil.copyfile(dst, stable)
            print(f"  = {stable}")


if __name__ == "__main__":
    main()
