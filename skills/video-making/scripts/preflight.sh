#!/usr/bin/env bash
# preflight.sh — check video-making dependencies WITHOUT installing anything.
#
# Usage: preflight.sh [--version X.Y.Z] [--node <node-dir>]
#   --version  pinned HyperFrames CLI version (default 0.8.143)
#   --node     project-local Node 22 for this check only: either the extracted folder
#              (node-v22.x-linux-x64) or its bin/ — whichever holds the node binary is put on PATH
#
# Checks Node >= 22, npx, ffmpeg/ffprobe, Noto Sans CJK fonts, the chrome-headless-shell cache,
# and — only if the pinned CLI is already in the npx cache — runs `hyperframes doctor` via
# `npx --no-install --offline` (cache only, never the registry). Missing pieces are listed with suggested install commands; nothing is run.
# doctor also lists optional extras (Docker daemon, transcription/TTS/music models); when only
# those fail it prints "Some checks failed" — preflight reports them as notes, not misses.
# Exit 0 when every required check passes, 1 otherwise. The final "result:" line is the verdict.
set -uo pipefail
VER=0.8.143
NODE_DIR=""
while [ $# -gt 0 ]; do
  case "$1" in
    --version) VER=$2; shift 2 ;;
    --node) NODE_DIR=$2; shift 2 ;;
    -h|--help) sed -n '2,16p' "$0"; exit 0 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
if [ -n "$NODE_DIR" ]; then
  NODE_DIR=${NODE_DIR%/}
  if [ -x "$NODE_DIR/node" ]; then export PATH="$NODE_DIR:$PATH"
  elif [ -x "$NODE_DIR/bin/node" ]; then export PATH="$NODE_DIR/bin:$PATH"
  else echo "--node $NODE_DIR: no node binary in it or in its bin/" >&2; exit 2; fi
fi
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
  note chrome "not cached — 'npx --no-install --offline hyperframes@$VER browser ensure' downloads chrome-headless-shell (~260MB) to ~/.cache/hyperframes (ask first)"
fi

if command -v npx >/dev/null 2>&1 && timeout 60 npx --no-install --offline "hyperframes@$VER" --version </dev/null >/dev/null 2>&1; then
  ok cli "hyperframes@$VER in npx cache — running doctor"
  doc=$(timeout 120 npx --no-install --offline "hyperframes@$VER" doctor </dev/null 2>&1 | sed $'s/\x1b\\[[0-9;]*m//g')
  printf '%s\n' "$doc" | sed 's/^/        /'
  # doctor marks failures with ✗; Docker daemon and AI model extras are optional for this skill.
  failed=$(printf '%s\n' "$doc" | grep '✗' | sed 's/^[[:space:]]*✗[[:space:]]*//' || true)
  optional='^(Docker running|Docker|whisper-cpp|TTS|BGM|onnxruntime|@google/genai)'
  hard=$(printf '%s\n' "$failed" | grep -Ev "$optional" | grep -v '^$' || true)
  soft=$(printf '%s\n' "$failed" | grep -E "$optional" | sed 's/  .*//' | paste -sd, - || true)
  [ -n "$soft" ] && note doctor "optional only: $soft — 'Some checks failed' above is about these; ignore unless you use render --docker"
  if [ -n "$hard" ]; then bad doctor "$(printf '%s' "$hard" | paste -sd';' -)"; fi
else
  note cli "hyperframes@$VER not in npx cache — one-time 'npx --yes hyperframes@$VER --version' downloads it (ask first); then everything runs with --no-install --offline"
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
    "nodejs.org/dist/latest-v22.x, verify with SHASUMS256.txt, extract next to the project, rerun with --node <extracted-dir> (or its bin/)"
  { has ffmpeg || has ffprobe; } && echo "  sudo apt-get install -y ffmpeg"
  has font && echo "  sudo apt-get install -y fonts-noto-cjk"
fi
exit 1
