#!/usr/bin/env bash
# vendor_gsap.sh — put a verified local copy of gsap.min.js into a video project.
#
# Usage: vendor_gsap.sh <project-dir> [--fetch] [--from <existing gsap.min.js>]
#   (default)  offline: take gsap@3.14.2 from the local npm cache (npm pack --offline)
#   --from     copy an existing file (e.g. another project's gsap.min.js) after checking its sha256
#   --fetch    allow ONE network download of the npm tarball (npm checks the registry integrity hash).
#              Ask the human first — this is the one-time fetch; later runs work offline from the cache.
#
# Why a script instead of a copy in this repo: GSAP is free under its "Standard 'no charge'
# license" (https://gsap.com/standard-license), which grants use and reproduction for permitted
# uses but does not clearly grant redistribution in a public repository. So each project takes
# its own copy from npm; the license header in the file is kept as-is.
# The version matches what `hyperframes@0.8.143 init` templates load from a CDN.
set -euo pipefail
GSAP_VER=3.14.2
GSAP_SHA256=c174bfce53a729418d57a8ad8625e7247c793a22fef8e2851e3cfa3de9cd8280   # package/dist/gsap.min.js
DEST="" FETCH=0 FROM=""
while [ $# -gt 0 ]; do
  case "$1" in
    --fetch) FETCH=1; shift ;;
    --from) FROM=$2; shift 2 ;;
    -h|--help) sed -n '2,15p' "$0"; exit 0 ;;
    -*) echo "unknown option: $1" >&2; exit 2 ;;
    *) DEST=$1; shift ;;
  esac
done
[ -n "$DEST" ] || { sed -n '4,4p' "$0" >&2; exit 2; }
mkdir -p "$DEST"
out="$DEST/gsap.min.js"

sha() { if command -v sha256sum >/dev/null 2>&1; then sha256sum "$1" | cut -d' ' -f1; else shasum -a 256 "$1" | cut -d' ' -f1; fi; }
install_verified() {
  local got; got=$(sha "$1")
  if [ "$got" != "$GSAP_SHA256" ]; then
    echo "sha256 mismatch for $1: $got (want gsap@$GSAP_VER $GSAP_SHA256)" >&2; exit 1
  fi
  head -c 300 "$1" | grep -q "gsap.com/standard-license" || { echo "license header missing in $1" >&2; exit 1; }
  cp "$1" "$out"
  echo "ok  $out  gsap@$GSAP_VER  sha256 $GSAP_SHA256"
}

if [ -n "$FROM" ]; then install_verified "$FROM"; exit 0; fi
if [ -f "$out" ] && [ "$(sha "$out")" = "$GSAP_SHA256" ]; then echo "ok  $out already present (gsap@$GSAP_VER)"; exit 0; fi

command -v npm >/dev/null 2>&1 || { echo "npm not found (ships with Node 22)" >&2; exit 1; }
tmp=$(mktemp -d); trap 'rm -rf "$tmp"' EXIT
if (cd "$tmp" && npm pack "gsap@$GSAP_VER" --offline --silent >/dev/null 2>&1); then
  echo "from npm cache: gsap@$GSAP_VER"
elif [ "$FETCH" = 1 ]; then
  echo "downloading gsap@$GSAP_VER tarball from the npm registry (approved one-time fetch)"
  if ! (cd "$tmp" && npm pack "gsap@$GSAP_VER" >"$tmp/npm.log" 2>&1); then
    echo "npm pack failed (network blocked? sandboxed agent?):" >&2; grep -i "error" "$tmp/npm.log" | head -5 >&2
    echo "Fallback: --from <existing gsap.min.js>, or run this fetch outside the sandbox." >&2; exit 1
  fi
else
  echo "gsap@$GSAP_VER is not in the npm cache." >&2
  echo "Ask the human, then rerun with --fetch (one download, ~1.7MB tarball; cached for later runs)," >&2
  echo "or pass --from <path-to-gsap.min.js> if another project already has it." >&2
  exit 1
fi
tar xzf "$tmp/gsap-$GSAP_VER.tgz" -C "$tmp" package/dist/gsap.min.js
install_verified "$tmp/package/dist/gsap.min.js"
