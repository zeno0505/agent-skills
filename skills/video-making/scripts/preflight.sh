#!/usr/bin/env bash
# preflight.sh — check video-making dependencies WITHOUT installing anything.
#
# Usage: preflight.sh [--version X.Y.Z] [--node <dir-containing-node-binary>]
#   --version  pinned HyperFrames CLI version (default 0.8.143)
#   --node     prepend this directory to PATH for this check only (project-local Node 22)
#
# Checks Node >= 22, npx, ffmpeg/ffprobe, Noto Sans CJK fonts, the chrome-headless-shell cache,
# and — only if the pinned CLI is already in the npx cache — runs `hyperframes doctor` via
# `npx --no-install`. Missing pieces are listed with suggested install commands; nothing is run.
# Exit 0 when every required check passes, 1 otherwise.
set -uo pipefail
VER=0.8.143
NODE_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --version) VER=$2; shift 2 ;;
    --node) NODE_DIR=$2; shift 2 ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[ -n "$NODE_DIR" ] && export PATH="$NODE_DIR:$PATH"
export HYPERFRAMES_NO_TELEMETRY=1 HYPERFRAMES_SKIP_SKILLS=1

missing=()
ok()   { printf '  ok    %-16s %s\n' "$1" "$2"; }
bad()  { printf '  MISS  %-16s %s\n' "$1" "$2"; missing+=("$1"); }
note() { printf '  note  %-16s %s\n' "$1" "$2"; }

echo "video-making preflight (hyperframes@$VER)"

if command -v node >/dev/null 2>&1; then
  v=$(node -v); major=${v#v}; major=${major%%.*}
  if [ "$major" -ge 22 ] 2>/dev/null; then ok node "$v ($(command -v node))"; else bad node "$v — need >= 22"; fi
else
  bad node "not found — need >= 22"
fi
command -v npx >/dev/null 2>&1 && ok npx "$(npx --version 2>/dev/null)" || bad npx "not found (ships with Node)"

for b in ffmpeg ffprobe; do
  if command -v "$b" >/dev/null 2>&1; then ok "$b" "$("$b" -version 2>/dev/null | head -1 | cut -d' ' -f1-3)"
  else bad "$b" "not found"; fi
done

if command -v fc-list >/dev/null 2>&1; then
  if fc-list : family | grep -i "Noto Sans CJK KR" >/dev/null; then ok font "Noto Sans CJK KR"
  else bad font "Noto Sans CJK KR not found (only needed for Korean on-screen text)"; fi
else
  note font "fc-list unavailable — check the CJK font manually"
fi

if ls -d "$HOME"/.cache/hyperframes/chrome/chrome-headless-shell/*/ >/dev/null 2>&1; then
  ok chrome "$(ls -d "$HOME"/.cache/hyperframes/chrome/chrome-headless-shell/*/ | head -1 | xargs basename)"
else
  note chrome "not cached — first check/render downloads chrome-headless-shell (~260MB) to ~/.cache/hyperframes (ask first)"
fi

if command -v npx >/dev/null 2>&1 && timeout 60 npx --no-install "hyperframes@$VER" --version </dev/null >/dev/null 2>&1; then
  ok cli "hyperframes@$VER in npx cache — running doctor"
  timeout 120 npx --no-install "hyperframes@$VER" doctor </dev/null 2>&1 | sed 's/^/        /'
else
  note cli "hyperframes@$VER not in npx cache — first 'npx hyperframes@$VER --version' downloads it (ask first)"
fi

if [ ${#missing[@]} -eq 0 ]; then
  echo "result: ready"
  exit 0
fi
echo "result: missing ${missing[*]}"
echo "suggested installs — show these to the human and run only after approval:"
has() { case " ${missing[*]} " in *" $1 "*) return 0 ;; esac; return 1; }
if [ "$(uname -s)" = Darwin ]; then
  { has node || has npx; } && echo "  brew install node@22 && export PATH=\"\$(brew --prefix node@22)/bin:\$PATH\""
  { has ffmpeg || has ffprobe; } && echo "  brew install ffmpeg"
  has font && echo "  install Noto Sans CJK KR (e.g. brew install --cask font-noto-sans-cjk-kr)"
else
  { has node || has npx; } && echo "  node 22 without touching the system: download node-v22.x-linux-x64.tar.gz from" \
    "nodejs.org/dist/latest-v22.x, verify with SHASUMS256.txt, extract next to the project, rerun with --node <dir>/bin"
  { has ffmpeg || has ffprobe; } && echo "  sudo apt-get install -y ffmpeg"
  has font && echo "  sudo apt-get install -y fonts-noto-cjk"
fi
exit 1
