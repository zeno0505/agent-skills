#!/usr/bin/env bash
# setup_note_link.sh — link this worktree's docs/note to the project's note directory.
#
# The DAG skills keep dag.yaml / dag.md / context.md / e2e-checklist.md outside the code
# repository, in a notes directory you own (for example an Obsidian vault). This script makes
# that directory reachable as `docs/note` inside the worktree and keeps it out of git.
#
# Usage:
#   NOTE_ROOT=~/notes setup_note_link.sh [project_path]
#
#   NOTE_ROOT     root of your notes directory (required; no default on purpose)
#   project_path  optional sub-path under NOTE_ROOT for this project
#                 (project mode: docs/note -> $NOTE_ROOT/<project_path>).
#                 Omit it to link the whole NOTE_ROOT (repo mode).
#
# Idempotent: an existing correct link is left alone; a different existing link is reported
# and left alone (never overwritten).
set -euo pipefail

if [ -z "${NOTE_ROOT:-}" ]; then
  echo "[setup-note-link] NOTE_ROOT is not set. Example: NOTE_ROOT=~/notes $0 acme/web/my-project" >&2
  exit 2
fi

PROJECT_PATH="${1:-}"
TARGET="$NOTE_ROOT"
[ -n "$PROJECT_PATH" ] && TARGET="$NOTE_ROOT/$PROJECT_PATH"
LINK_PATH="docs/note"

if [ ! -e ".git" ]; then
  echo "[setup-note-link] run this from the root of a git worktree" >&2
  exit 2
fi

mkdir -p "$TARGET" docs

if [ -L "$LINK_PATH" ]; then
  current="$(readlink "$LINK_PATH")"
  if [ "$current" = "$TARGET" ]; then
    echo "[setup-note-link] symlink already exists: $LINK_PATH -> $TARGET"
  else
    echo "[setup-note-link] $LINK_PATH already points to $current (wanted $TARGET); leaving it alone" >&2
    exit 1
  fi
elif [ -e "$LINK_PATH" ]; then
  echo "[setup-note-link] $LINK_PATH exists and is not a symlink; leaving it alone" >&2
  exit 1
else
  ln -s "$TARGET" "$LINK_PATH"
  echo "[setup-note-link] created symlink: $LINK_PATH -> $TARGET"
fi

# Exclude from git via info/exclude of the main repository (works for linked worktrees too).
if [ -f ".git" ]; then
  GITDIR="$(sed 's/^gitdir: //' .git)"
  MAIN_GIT="$(cd "$GITDIR/../.." && pwd)"
else
  MAIN_GIT=".git"
fi
EXCLUDE_FILE="$MAIN_GIT/info/exclude"
mkdir -p "$(dirname "$EXCLUDE_FILE")"
if grep -qxF "$LINK_PATH" "$EXCLUDE_FILE" 2>/dev/null; then
  echo "[setup-note-link] already excluded: $LINK_PATH"
else
  echo "$LINK_PATH" >> "$EXCLUDE_FILE"
  echo "[setup-note-link] added to $EXCLUDE_FILE: $LINK_PATH"
fi
