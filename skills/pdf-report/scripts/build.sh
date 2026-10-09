#!/usr/bin/env bash
# build.sh — preflight → slidev export → PNG render → page info → visual QA numbers.
# Usage: build.sh <slides.md> <out.pdf>     (run from the deck directory that has node_modules)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SLIDES="${1:?usage: build.sh <slides.md> <out.pdf>}"
PDF="${2:?usage: build.sh <slides.md> <out.pdf>}"
OUT="$(dirname "$PDF")"
mkdir -p "$OUT"

echo "==> preflight"
python3 "$HERE/preflight.py" "$SLIDES"

echo "==> slidev export → $PDF"
LOG="$OUT/slidev-export.log"
if ! timeout 600 npx slidev export "$SLIDES" --output "$PDF" --timeout 120000 >"$LOG" 2>&1; then
  tail -20 "$LOG"; echo "export failed (full log: $LOG)" >&2; exit 1
fi

echo "==> render PNG (144 dpi)"
rm -rf "$OUT/png" && mkdir -p "$OUT/png"
pdftoppm -png -r 144 "$PDF" "$OUT/png/p" 2>/dev/null

echo "==> pdfinfo"
pdfinfo "$PDF" | grep -E '^(Pages|Page size):' || true

echo "==> page QA numbers (suspects only — open the PNGs to judge)"
python3 "$HERE/qa_pages.py" "$OUT/png" --sheets "$OUT/qa"
