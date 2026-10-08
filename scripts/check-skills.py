#!/usr/bin/env python3
"""Validate every skills/<slug>/SKILL.md: frontmatter parses, name == slug, description present."""
import sys
from pathlib import Path

import yaml

root = Path(__file__).resolve().parents[1] / "skills"
bad = 0
for skill in sorted(p for p in root.iterdir() if p.is_dir()):
    f = skill / "SKILL.md"
    if not f.exists():
        print(f"FAIL {skill.name}: no SKILL.md"); bad += 1; continue
    text = f.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        print(f"FAIL {skill.name}: no frontmatter"); bad += 1; continue
    meta = yaml.safe_load(text.split("---\n", 2)[1]) or {}
    if meta.get("name") != skill.name:
        print(f"FAIL {skill.name}: name is {meta.get('name')!r}"); bad += 1
    if not str(meta.get("description", "")).strip():
        print(f"FAIL {skill.name}: empty description"); bad += 1
print(f"[check-skills] {len(list(root.iterdir()))} skill dir(s), {bad} problem(s)")
sys.exit(1 if bad else 0)
