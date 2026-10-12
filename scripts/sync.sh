#!/usr/bin/env bash
# Fast-forward this clone to origin/main and keep the per-skill symlinks in step.
#   ~/.agents/skills/<slug>  -> <clone>/skills/<slug>
#   ~/.claude/skills/<slug>  -> ../../.agents/skills/<slug>   (only if ~/.claude/skills exists)
# New skills get linked, links whose skill left the repo get removed. Real directories
# and links pointing elsewhere are never touched. Skips the pull (but still relinks)
# when the clone is not on main or has local changes, so in-progress edits are safe.
# Usage: scripts/sync.sh            (meant for a daily launchd/cron job)
set -euo pipefail
cd "$(dirname "$0")/.."
repo=$(pwd -P)
agents="$HOME/.agents/skills"
claude="$HOME/.claude/skills"

log() { printf '%s [sync] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*"; }

branch=$(git symbolic-ref --short -q HEAD || echo "(detached)")
if [ "$branch" != main ]; then
  log "on $branch, not main — pull skipped"
elif [ -n "$(git status --porcelain)" ]; then
  log "working tree has changes — pull skipped"
else
  before=$(git rev-parse HEAD)
  git fetch -q origin main
  git merge -q --ff-only origin/main
  after=$(git rev-parse HEAD)
  if [ "$before" = "$after" ]; then log "up to date ($(git rev-parse --short HEAD))"
  else log "updated $(git rev-parse --short "$before")..$(git rev-parse --short "$after")"; fi
fi

mkdir -p "$agents"
for dir in "$repo"/skills/*/; do
  slug=$(basename "$dir")
  if [ ! -e "$agents/$slug" ] && [ ! -L "$agents/$slug" ]; then
    ln -s "$repo/skills/$slug" "$agents/$slug"; log "linked $slug"
  fi
  if [ -d "$claude" ] && [ ! -e "$claude/$slug" ] && [ ! -L "$claude/$slug" ]; then
    ln -s "../../.agents/skills/$slug" "$claude/$slug"
  fi
done

for link in "$agents"/* "$claude"/*; do
  [ -L "$link" ] && [ ! -e "$link" ] || continue
  case "$(readlink "$link")" in
    "$repo/skills/"*|../../.agents/skills/*) rm "$link"; log "pruned ${link#"$HOME"/}" ;;
  esac
done
