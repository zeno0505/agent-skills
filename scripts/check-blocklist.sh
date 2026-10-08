#!/usr/bin/env bash
# Grep the tree for terms that must never land in this public repo.
#   scripts/blocklist.txt   public patterns (committed)
#   .blocklist.local        private patterns (gitignored, local only)
#   $BLOCKLIST_EXTRA        private patterns, newline-separated (CI secret)
# Exit 1 on any hit. Usage: scripts/check-blocklist.sh [extra-file-or-text-to-scan...]
set -euo pipefail
cd "$(dirname "$0")/.."

pats=$(mktemp); trap 'rm -f "$pats"' EXIT
{ grep -vE '^\s*(#|$)' scripts/blocklist.txt
  [ -f .blocklist.local ] && grep -vE '^\s*(#|$)' .blocklist.local
  [ -n "${BLOCKLIST_EXTRA:-}" ] && printf '%s\n' "$BLOCKLIST_EXTRA" | grep -vE '^\s*(#|$)'
} > "$pats" || true

private=0
[ -f .blocklist.local ] && private=1
[ -n "${BLOCKLIST_EXTRA:-}" ] && private=1

files=$(git ls-files --cached --others --exclude-standard | grep -vE '^(scripts/blocklist\.txt|\.blocklist\.local)$' || true)
hits=0; idx=0
while IFS= read -r p; do
  [ -z "$p" ] && continue
  idx=$((idx + 1))
  case "$p" in "(?-i)"*) flags=(-P); p=${p#"(?-i)"} ;; *) flags=(-P -i) ;; esac
  out=$(printf '%s\n' $files | xargs -r -d '\n' grep -nH "${flags[@]}" -e "$p" -- 2>/dev/null || true)
  for extra in "$@"; do
    if [ -f "$extra" ]; then o=$(grep -nH "${flags[@]}" -e "$p" -- "$extra" 2>/dev/null || true)
    else o=$(printf '%s\n' "$extra" | grep -n "${flags[@]}" -e "$p" 2>/dev/null | sed 's/^/<arg>:/' || true); fi
    [ -n "$o" ] && out=$(printf '%s\n%s' "$out" "$o")
  done
  out=$(printf '%s\n' "$out" | sed '/^$/d')
  if [ -n "$out" ]; then
    n=$(printf '%s\n' "$out" | wc -l); hits=$((hits + n))
    echo "pattern #$idx: $n hit(s)"   # index only, so private patterns never print in public CI logs
    printf '%s\n' "$out" | sed 's/^/  /'
  fi
done < "$pats"

echo "[blocklist] $(wc -l < "$pats") pattern(s), private list: $([ $private = 1 ] && echo loaded || echo 'not loaded'), hits: $hits"
[ "$hits" -eq 0 ]
